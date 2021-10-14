"""Describe orderbook sides"""
import enum


class Side(enum.Enum):

    # Sell side, orders are trying to sell token at this price
    ask = "ask"

    # Buy side, orders are trying to buy token at this price
    bid = "bid"
