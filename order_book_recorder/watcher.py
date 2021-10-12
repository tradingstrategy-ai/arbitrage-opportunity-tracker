import logging
import time
from asyncio import Task, create_task
from typing import Optional, Dict, List, Union, Callable
from concurrent.futures import ThreadPoolExecutor
from ccxtpro.base.exchange import Exchange as ProExchange
from ccxt.base.exchange import Exchange as SyncExchange
from ccxt.base.errors import RateLimitExceeded
from order_book_recorder.utils import to_async

# Create a thread pool where sync exchange APIs will be executed
sync_exchange_thread_pool = ThreadPoolExecutor()


logger = logging.getLogger(__name__)


class Watcher:

    exchange_name: str
    pair: str
    exchange: Union[ProExchange, SyncExchange]
    orderbook: dict
    task: Optional[Task]
    done: bool

    def __init__(self, exchange_name: str, pair: str, exchange):
        self.exchange_name = exchange_name
        self.pair = pair
        self.exchange = exchange
        self.task = None
        self.done = False
        self.task_count = 0

        self.ask_price = None
        self.bid_price = None

        self.order_book_limit = 100

        # Sync API throttling
        self.min_fetch_delay = 2.0
        self.last_fetch = 0

    async def start_watching(self) -> "WatchedExchange":
        """Options

        - Sync API
        - ASync API
        """

        if hasattr(self.exchange, "watch_order_book"):
            # CCXT PRO
            self.orderbook = await self.watch_async()
        else:
            # CCXT
            # Sync (Exmo) or async API (Gemini)
            self.orderbook = await self.watch_sync()
        self.done = True
        return self

    async def watch_async(self):
        return await self.exchange.watch_order_book(self.pair, limit=self.order_book_limit)

    @to_async(executor=sync_exchange_thread_pool)
    def watch_sync(self):
        """Wrap a sync API in a thread pool execution."""
        tries = 10
        delay = 1.0

        needs_sleeping = self.min_fetch_delay - (time.time() - self.last_fetch)
        if needs_sleeping > 0:
            logger.info("Adding some sleep for %s: %f", self.exchange_name, needs_sleeping)
            time.sleep(needs_sleeping)

        while tries:
            try:
                order_book = self.exchange.fetch_order_book(self.pair, limit=self.order_book_limit)
                self.last_fetch = time.time()
                return order_book
            except RateLimitExceeded:
                logger.warning("Rate limit exceeded on %s, tries %d, delay %s", self.exchange_name, tries, delay)
                time.sleep(delay)
                tries -= 1
                delay *= 1.25

    def create_task(self):
        self.done = False
        self.task_count += 1
        self.task = create_task(self.start_watching(), name=f"{self.exchange_name}: {self.pair} task #{self.task_count}")
        return self.task

    def is_task_pending(self):
        if self.task is None:
            return False

        if self.done:
            return False

        return True

    def is_done(self):
        if self.task is None:
            return False

        if self.done:
            return True

        return False

    def has_data(self):
        return self.ask_price is not None

    def refresh_depths(self):
        """Update exchange market depths"""
        #  BTC/GBP [42038.45, 0.083876] [42017.45, 0.03815124]
        self.ask_price = self.orderbook["asks"][0][0]
        self.bid_price = self.orderbook["bids"][0][0]

    def get_spread(self):
        assert self.has_data()
        return (self.ask_price - self.bid_price) / self.bid_price