import logging
import time
import asyncio
from asyncio import Task, create_task
from collections import defaultdict
from typing import Optional, Dict, List

import ccxtpro
from ccxtpro.base.exchange import Exchange


from rich.live import Live
from rich.table import Table
from rich.console import Console

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

        self.ask_price = None
        self.bid_price = None

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


async def setup_exchanges():
    exchanges = {
        "huobi": ccxtpro.huobi({'enableRateLimit': True}),
        "kraken": ccxtpro.kraken({'enableRateLimit': True}),
        # "gemini": ccxtpro.gemini({'enableRateLimit': True}),
        "coinbase": ccxtpro.coinbasepro({'enableRateLimit': True}),
        # "exmo": ccxt.exmo({'enableRateLimit': True}),
    }

    for name, x in exchanges.items():
        logger.info("Loading markets for %s", name)
        await x.load_markets()

    return exchanges


def refresh_live(exchanges: dict, markets: List[str], watchers_by_market: Dict[str, Dict[str, Watcher]]) -> Table:
    """Make a Rich table that keeps displaying the exchange live prices"""
    table = Table()
    table.add_column("Exchange")
    for market in markets:
        table.add_column(market + " ask")
        table.add_column("bid")
        table.add_column("Spread BPS")

    for exchange_name in exchanges.keys():
        values = [exchange_name]
        for market in markets:
            watcher = watchers_by_market.get(market, {}).get(exchange_name, None)

            if watcher is None:
                values.append("N/A")
                values.append("N/A")
                values.append("N/A")
                continue

            if not watcher.has_data():
                values.append("--")
                values.append("--")
                values.append("--")
                continue

            values.append(f"{watcher.ask_price}")
            values.append(f"{watcher.bid_price}")
            values.append(f"{watcher.get_spread() * 10000:,.2f}")

        table.add_row(*values)

    print(table)
    return table


async def run_duty_cycle(watchers: List[Watcher]):
    """Get some exchange updates."""

    # Retrigger watch on any exchange
    for w in watchers:
        if not w.is_task_pending():
            w.create_task()

    # Collect tasks to watch
    tasks = [w.task for w in watchers]

    # Get triggered by websocket updates
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

    for d in done:
        result = await d
        # logger.info("Done %s", d)

    # Go through finished tasks
    for w in watchers:
        if w.is_done():
            # Refresh the price
            # logger.info("Refreshing %s: %s", w.exchange_name, w.pair)
            w.refresh_depths()


async def main(live=True):

    global logger
    logger = setup_logging()

    exchanges = await setup_exchanges()

    watchers = []

    # market -> exchange -> Watcher lookup
    watchers_by_market: Dict[str, Dict[str, Watcher]] = defaultdict(dict)

    def generate_table():
        table = refresh_live(exchanges, MARKETS, watchers_by_market)
        return table

    # Create first batch of the tasks
    for exchange_name, exchange in exchanges.items():
        for market in MARKETS:
            if market in exchange.symbols:
                logger.info("Starting to watch market %s: %s", exchange_name, market)
                watcher = Watcher(exchange_name, market, exchange)
                watchers.append(watcher)
                watchers_by_market[market][exchange_name] = watcher

    if live:
        console = Console()
        #live = Live(generate_table(), console=console, screen=True, auto_refresh=False)
        #live.update(generate_table(), refresh=True)
        with Live(console=console, screen=True, auto_refresh=False) as live:

            last_update = time.time()
            live.update(generate_table(), refresh=True)

            # Run the main loop
            while True:
                await run_duty_cycle(watchers)
                if time.time() - last_update > 4.0:
                    live.update(generate_table(), refresh=True)
                    last_update = time.time()

    else:
        # Raw console logging
        while True:
            await run_duty_cycle(watchers)


asyncio.get_event_loop().run_until_complete(main())