import logging
import string
import time
import asyncio
from asyncio import Task, create_task
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, List, Union, Callable

import ccxt
from rich.layout import Layout

import ccxtpro
from ccxtpro.base.exchange import Exchange as ProExchange
from ccxt.base.exchange import Exchange as SyncExchange
from ccxt.base.errors import RateLimitExceeded
import typer
from rich.live import Live
from rich.table import Table
from rich.console import Console

from order_book_recorder.config import setup_exchanges
from order_book_recorder.logger import setup_logging
from order_book_recorder.logtable import refresh_log_messages, BufferedOutputHandler
from order_book_recorder.pricetable import refresh_live
from order_book_recorder.utils import to_async
from order_book_recorder.watcher import Watcher

DEPTHS = [100, 500, 1000, 3000, 5000]


MARKETS = ["BTC/GBP", "ETH/GBP", "BTC/EUR", "ETH/EUR"]


logger: logging.Logger = None


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
        try:
            result = await d
        except Exception as e:
            raise RuntimeError(f"Error while processing exchange {d.get_name()}") from e

    # Go through finished tasks
    for w in watchers:
        if w.is_done():
            # Refresh the price
            # logger.info(f"Refreshing {w.exchange_name}: {w.pair}")
            try:
                w.refresh_depths()
            except Exception as e:
                raise RuntimeError(f"Error while refreshing depth data for exchange {w.exchange_name}") from e


async def run_core(live=True):

    global logger
    logger = setup_logging()

    exchanges = await setup_exchanges()

    watchers = []

    # market -> exchange -> Watcher lookup
    watchers_by_market: Dict[str, Dict[str, Watcher]] = defaultdict(dict)

    def generate_table():
        table = refresh_live(exchanges, MARKETS, watchers_by_market)
        return table

    def print_log(msg):
        assert isinstance(msg, str)
        captured_log.append(msg)

    # Create first batch of the tasks
    for exchange_name, exchange in exchanges.items():
        for market in MARKETS:
            if market in exchange.symbols:
                logger.info("Starting to watch market %s: %s", exchange_name, market)
                watcher = Watcher(exchange_name, market, exchange)
                watchers.append(watcher)
                watchers_by_market[market][exchange_name] = watcher

    if live:

        captured_log: List[str] = []
        live_log_handler = BufferedOutputHandler(captured_log)

        logger.handlers.clear()
        logger.handlers.append(live_log_handler)

        def generate_log_panel():
            table = refresh_log_messages(captured_log)
            return table

        layout = Layout()

        layout.split_row(
            Layout(name="left"),
            Layout(name="right"),
        )

        console = Console()

        with Live(layout, console=console, screen=True, auto_refresh=False) as live:

            last_update = time.time()

            layout["left"].update(generate_table())
            layout["right"].update(generate_log_panel())
            # live.update(generate_table(), refresh=True)

            # Run the main loop
            while True:

                await run_duty_cycle(watchers)

                if time.time() - last_update > 4.0:
                    layout["left"].update(generate_table())
                    layout["right"].update(generate_log_panel())
                    live.refresh()
                    last_update = time.time()

    else:
        # Raw console logging
        while True:
            await run_duty_cycle(watchers)



def main(live: bool = True):
    asyncio.get_event_loop().run_until_complete(run_core(live))


if __name__ == "__main__":
    typer.run(main)


