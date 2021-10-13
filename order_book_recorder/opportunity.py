"""Find trading opportunitiess in different depths."""
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Opportunity:
    """Describe a found arbitrage opportunity."""

    market: str
    buy_exchange: str
    sell_exchange: str

    #: Market depth for this opportunity
    quantity: float
    buy_price: float
    sell_price: float

    @property
    def profit_without_fees(self) -> float:
        """Get % arbitrage profit this trade would make"""
        return (self.sell_price - self.buy_price) / self.buy_price

    @property
    def diff(self) -> float:
        """Fiat arbitrage window"""
        return self.sell_price - self.buy_price


def find_opportunities(market: str, depth_quantity: float, depth_asks: Dict[str, float], depth_bids: Dict[str, float]) -> List[Opportunity]:
    """Get a list of opportunities, for each depth level, ranked from the best to high.

    A wasteful way of computation to evaluate every opportunity there is.

    :param depth_asks: (exchange, price) tuples of prices
    :param depth_bids: (exchange, price) tuples of prices
    :return:
    """

    opportunities = []
    for ask_exchange, ask_price in depth_asks.items():
        for bid_exchange, bid_price in depth_bids.items():

            o = Opportunity(
                market=market,
                buy_exchange=ask_exchange,
                sell_exchange=bid_exchange,
                buy_price=ask_price,
                sell_price=bid_price,
                quantity=depth_quantity,
            )
            opportunities.append(o)

    opportunities.sort(key=lambda o: o.profit_without_fees, reverse=True)
    return opportunities



