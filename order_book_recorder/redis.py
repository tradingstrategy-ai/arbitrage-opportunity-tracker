"""Redis Timeseries order book depth recorder"""

import enum
import logging
import socket
import time
from typing import Optional

# https://github.com/RedisTimeSeries/redistimeseries-py
import redis
from redistimeseries.client import Client


logger = logging.getLogger(__name__)

_connection: Client = None


class Side(enum.Enum):
    """
    https://en.wikipedia.org/wiki/Bid%E2%80%93ask_spread

    Ask > bid always
    """

    # Sell side
    ask = "ask"

    # Buy side
    bid = "bid"


def is_enabled(self):
    return


def has_db():
    return _connection != None


def get_client() -> Client:
    assert _connection
    return _connection


def init_connection(conf: dict):
    global _connection
    # https://github.com/RedisTimeSeries/redistimeseries-py

    if _connection:
        logger.info("Redis already initialised")
        return _connection

    logger.info("Connecting to redis: %s" % conf)
    if not conf:
        return

    # https://redis-py.readthedocs.io/en/stable/#redis.Redis
    _connection = Client(**conf)
    return _connection


def test_connection():
    """Raise an error if the connection does work."""
    rts = get_client()

    # rts.redis.check_health()
    # Do a dummy write to check we are connected
    host = socket.gethostname()
    rts.redis.lpush(f"recorder_connected_{host}", time.time())


def format_key(exchange: str, base_pair: str, quote_pair: str, side: Side, depth: float):
    """Get a key to used as the timeseries name."""
    return f"Orderbook depth: {exchange} {base_pair}-{quote_pair} {side.value} at {depth}"


def init_time_series(exchange: str, base_pair: str, quote_pair: str, side: Side, depth: Depth):
    key = format_key(exchange, base_pair, quote_pair, side, depth)
    rts = get_client()
    if not rts.redis.exists(key):
        labels = {
            "type": "orderbook_depth",
            "exchange": exchange,
            "base_pair": base_pair,
            "quote_pair": quote_pair,
            "side": side.value,
            "depth": depth.value
        }
        logger.info(f"Created redis key {key}")
        rts.create(key, labels=labels)


def start_tick(timestamp: int, owner_name: str):
    """Report the bot is active."""
    r = get_client().redis
    # key = f"Bot {}"
    r.hset("bot", owner_name, timestamp)


def start_order_book_depth_recording(timestamp: int, exchange: str, base_pair: str, quote_pair: str):
    """Create a Redis key that expires in 5 minutes just to give us a count of active orbderbooks."""
    r = get_client().redis
    key = f"{exchange} {base_pair}-{quote_pair}"
    r.hset("orderbook scan", key, timestamp)


def record_order_book_price(timestamp: int, exchange: str, base_pair: str, quote_pair: str, side: Side, depth: Depth, reporter: str, value: float) -> Optional[dict]:
    """Record order book state for later analysis.

    Example for what is the price of a Bitcoin if buying Bitcoin with 1000 USD in Kucoin.
    Value is the value of Bitcoin bought at the price.

    :param timestamp: Bot tick UNIX timestamp as seconds
    :param exchange: "kucoin"
    :param base_pair: "BTC"
    :param quote_pair: "USDT"
    :param side: "buy"
    :param depth: Depth of the recording as quantity of base pair
    :param reporter: "mikko"
    :param value: 32,123
    """

    assert type(timestamp) == int, "Got invalid timestamp: %s" % type(timestamp)
    assert type(value) == float, "Got invalid value: %s" % type(value)

    # Expose for testing
    global _last_recorded_entry

    rts = get_client()
    key = format_key(exchange, base_pair, quote_pair, side, depth)

    #logger.debug(f"Recording {key} {timestamp} {value}")

    try:
        # Redis Timeseries expects timestamps as milliseconds
        rts.add(key, timestamp * 1000, value)
    except redis.exceptions.ResponseError as e:
        if str(e) == 'TSDB: Error at upsert, update is not supported in BLOCK mode':
            # Ignore duplicate keys
            return None

        #existing = rts.range(key, timestamp, timestamp)
        raise RuntimeError(f"Could not record {key}={value} at timestamp {timestamp}: {e}") from e

    return {"key": key, "value": value }


