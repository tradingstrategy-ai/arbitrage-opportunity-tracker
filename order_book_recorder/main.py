import datetime
import logging
import time
import asyncio
from collections import defaultdict
from typing import Dict, List

from rich.layout import Layout

import typer
from rich.live import Live
from rich.console import Console

from order_book_recorder import telegram
from order_book_recorder.alert import update_alerts
from order_book_recorder.config import setup_exchanges, MARKETS, BTC_DEPTHS, ETH_DEPTHS, MARKET_DEPTHS, ALERT_THRESHOLD, \
    RETRIGGER_THRESHOLD
from order_book_recorder.logger import setup_logging
from order_book_recorder.logtable import refresh_log_messages, BufferedOutputHandler
from order_book_recorder.notify import notify
from order_book_recorder.opportunity import Opportunity, find_opportunities
from order_book_recorder.pricetable import refresh_live
from order_book_recorder.watcher import Watcher


logger: logging.Logger = None


def update_opportunities(watchers: List[Watcher], measured_market_depths: Dict[str, List[float]]) -> Dict[str, Dict[str, List[Opportunity]]]:
    """Update the available opportunities to arbitrage across markets in different depths."""

    all_opportunities = defaultdict(dict)

    # Build a map of markets and their deptjs
    for market, depths in measured_market_depths.items():

        # Get all exchanges connected to this pair
        market_watchers = filter(lambda w: w.market == market, watchers)

        market_watchers = list(market_watchers)

        assert len(market_watchers) > 0, f"Could not find watchers for the market {market}"

        # Analyse opportunity per depth
        for depth in depths:

            depth_asks = {}
            depth_bids = {}

            # Create depth tables
            for watcher in market_watchers:

                if depth in watcher.ask_levels:
                    # Watcher might not have data available yet
                    depth_asks[watcher.exchange_name] = watcher.ask_levels[depth]
                    depth_bids[watcher.exchange_name] = watcher.bid_levels[depth]

            # Find opportunities in this depth
            opportunities = find_opportunities(market, depth, depth_asks, depth_bids)

            # logger.info("Opportunities for %s %s: %s, asks %s, bids %s", market, depth, opportunities, depth_asks, depth_bids)
            all_opportunities[market][depth] = opportunities

    return all_opportunities


async def run_duty_cycle(watchers: List[Watcher]) -> Dict[str, Dict[str, List[Opportunity]]]:
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

    # Update the opportunities
    opportunities = update_opportunities(watchers, MARKET_DEPTHS)

    return opportunities


async def run_core_live(exchanges: dict, watchers: List[Watcher], watchers_by_market: Dict[str, Dict[str, Watcher]]):
    """Run the app with interactive Rich dashboard."""

    captured_log: List[str] = []
    live_log_handler = BufferedOutputHandler(captured_log)

    logger.handlers.clear()
    logger.handlers.append(live_log_handler)

    def draw_price_table():
        table = refresh_live(exchanges, MARKETS, watchers_by_market)
        return table

    def draw_opportunity_table():
        table = refresh_live(exchanges, MARKETS, watchers_by_market)
        return table

    def generate_log_panel():
        table = refresh_log_messages(captured_log)
        return table

    layout = Layout()

    layout.split_row(
        Layout(name="left"),
        Layout(name="right"),
    )

    layout["left"].split_column(
        Layout(name="top"),
        Layout(name="bottom"),
    )

    console = Console()

    with Live(layout, console=console, screen=True, auto_refresh=False) as live:

        last_update = time.time()

        layout["left"].update(draw_price_table())
        layout["right"].update(generate_log_panel())
        # live.update(generate_table(), refresh=True)

        # Run the main loop
        while True:

            await run_duty_cycle(watchers)

            if time.time() - last_update > 4.0:
                layout["left"].update(draw_price_table())
                layout["right"].update(generate_log_panel())
                live.refresh()
                last_update = time.time()


async def run_core_logged(exchanges: list, watchers: List[Watcher], watchers_by_market: Dict[str, Dict[str, Watcher]]):
    """Run the app with raw console logging."""

    update_delay = 3.0
    last_update = 0

    def log_opportunity(opportunity, market, depth, best):
        base, quote = market.split("/")
        profitability = best.profit_without_fees
        formatted_profitability = f"{profitability * 100:,.5f}%"

        # Fiat prices with two decimals
        buy_price = "{:,.2f}".format(best.buy_price)
        sell_price = "{:,.2f}".format(best.sell_price)
        diff = "{:,.2f}".format(best.diff)

        msg = f"{market} {opportunity} (@{depth:.4f} {base}) is {formatted_profitability:9} by buy {best.buy_exchange:10} {buy_price:10} - sell {best.sell_exchange:10} - {sell_price:10} ({diff} {quote})"
        logger.info(msg)

    while True:
        all_opportunities = await run_duty_cycle(watchers)

        update_alerts(all_opportunities, ALERT_THRESHOLD, RETRIGGER_THRESHOLD)

        # Regularly log the best opportunities to the logging output
        if time.time() - last_update > update_delay:

            logger.info("Opportunities %s", datetime.datetime.utcnow())

            # Log out the prices
            for market, market_watchers in watchers_by_market.items():
                ticker_feed = [f"{market} --- "]
                for name, w in market_watchers.items():
                    ask_price = "{:,.2f}".format(w.ask_price) if w.ask_price else "---"
                    bid_price = "{:,.2f}".format(w.bid_price) if w.bid_price else "---"
                    ticker_feed.append(f"{name} A:{ask_price:10} B:{bid_price:10}")

                logger.info(" ".join(ticker_feed))

            # Write out top opportunities for each market and depth on each cycle
            for market, depths in all_opportunities.items():
                depth_opportunities: List[Opportunity]
                for depth, depth_opportunities in depths.items():

                    if len(depth_opportunities) == 0:
                        # Still connecting to exchanges
                        logger.warning("%s %s - not yet available opportunities", market, depth)
                    else:
                        best = depth_opportunities[0]

                        log_opportunity("#1", market, depth, best)

                        if len(depth_opportunities) >= 2:
                            second_best = depth_opportunities[1]
                            log_opportunity("#2", market, depth, second_best)

            last_update = time.time()


async def run_core(live=True, log_filename=None):

    global logger
    logger = setup_logging(log_filename=log_filename)

    logger.info("Logging to %s", log_filename)
    logger.info("Starting, Telegram available: %s", telegram.is_enabled())

    exchanges = await setup_exchanges()

    exchange_names = ", ".join(list(exchanges.keys()))

    alert_threshold = ALERT_THRESHOLD

    msg = f"""
        Connected exchanges: {exchange_names}
        Profitability alert threshold: {alert_threshold * 100:,.5f}%
    """

    notify(f"⚡️ Arbitrage opportunity tracker starting", msg)

    watchers = []

    # market -> exchange -> Watcher lookup
    watchers_by_market: Dict[str, Dict[str, Watcher]] = defaultdict(dict)

    # Create first batch of the tasks
    for exchange_name, exchange in exchanges.items():
        for market in MARKETS:
            if market in exchange.symbols:
                logger.info("Starting to watch market %s: %s", exchange_name, market)

                if market.startswith("BTC"):
                    depths = BTC_DEPTHS
                elif market.startswith("ETH"):
                    depths = ETH_DEPTHS
                else:
                    raise RuntimeError(f"Cannot handle market {market}")

                watcher = Watcher(exchange_name, market, exchange, depths)
                watchers.append(watcher)
                watchers_by_market[market][exchange_name] = watcher

    if live:
        await run_core_live(exchanges, watchers, watchers_by_market)
    else:
        await run_core_logged(exchanges, watchers, watchers_by_market)


def main(live: bool = True, log_filename: str = None):
    try:
        asyncio.get_event_loop().run_until_complete(run_core(live, log_filename))
    except Exception as e:
        # Make sure we get a crash reason in the logs
        if logger:
            logger.error("Crashed")
            logger.exception(e)
        raise e


if __name__ == "__main__":
    typer.run(main)


