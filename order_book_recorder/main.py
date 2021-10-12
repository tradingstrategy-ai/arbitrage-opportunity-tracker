import logging
from asyncio import Task, create_task
from typing import Optional

import ccxtpro
from ccxtpro.base.exchange import Exchange
import asyncio

from order_book_recorder.logger import setup_logging

DEPTHS = [100, 500, 1000, 3000, 5000]


MARKETS = ["BTC/GBP", "ETH/GBP", "BTC/EUR", "ETH/EUR"]


logger = logging.getLogger()


class Watcher:

    exchange_name: str
    pair: str
    exchange: Exchange
    orderbook: dict
    task: Optional[Task]
    done: bool

    def __init__(self, exchange_name: str, pair: str, exchange: Exchange):
        self.exchange_name = exchange_name
        self.pair = pair
        self.exchange = exchange
        self.task = None
        self.done = False
        self.task_count = 0

    async def start_watching(self) -> "WatchedExchange":
        self.orderbook = await self.exchange.watch_order_book(self.pair)
        self.done = True
        return self

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


async def setup_exchanges():
    exchanges = {
        "huobi": ccxtpro.huobi({'enableRateLimit': True}),
        "kraken": ccxtpro.kraken({'enableRateLimit': True}),
        "gemini": ccxtpro.gemini({'enableRateLimit': True}),
        "coinbase": ccxtpro.coinbase({'enableRateLimit': True}),
        # "exmo": ccxt.exmo({'enableRateLimit': True}),
    }

    for name, x in exchanges.items():
        logger.info("Loading markets for %s", name)
        await x.load_markets()

    return exchanges


async def main():

    global logger
    logger = setup_logging()

    exchanges = await setup_exchanges()

    watchers = []

    # Create first batch of the tasks
    for exchange_name, exchange in exchanges.items():
        for market in MARKETS:
            if market in exchange.symbols:
                logger.info("Starting to watch market %s: %s", exchange_name, market)
                watcher = Watcher(exchange_name, market, exchange)
                watchers.append(watcher)

    # Run the main loop
    while True:

        # Retrigger watch on any exchange
        for w in watchers:
            if not w.is_task_pending():
                w.create_task()

        # Collect tasks to watch
        tasks = [w.task for w in watchers]

        # Get triggered by websocket updates
        done, pending = await asyncio.wait(tasks)

        for d in done:
            logger.info("Finished task: %s", d)

        # Go through finished tasks
        for w in watchers:
            if w.is_done():
                logger.info("Pair comparison needed: %s", w.pair)


asyncio.get_event_loop().run_until_complete(main())