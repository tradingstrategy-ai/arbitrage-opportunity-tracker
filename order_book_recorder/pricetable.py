from typing import List, Dict

from rich.table import Table

from order_book_recorder.watcher import Watcher


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
