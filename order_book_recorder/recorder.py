"""Redis Timeseries order book depth recorder"""


import logging
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List

# https://github.com/RedisTimeSeries/redistimeseries-py
import redis
from redistimeseries.client import Client

from order_book_recorder import config
from order_book_recorder.side import Side
from order_book_recorder.utils import to_async

logger = logging.getLogger(__name__)

_connection: Client = None


# Create a thread pool where sync exchange APIs will be executed
redis_thread_pool = ThreadPoolExecutor()

# In-process counter of Redis writes we have done
redis_updates = 0

def is_enabled():
    return config.REDIS_CONFIG


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


def init_time_series(exchange: str, base_pair: str, quote_pair: str, side: Side, depth: float):
    key = format_key(exchange, base_pair, quote_pair, side, depth)
    rts = get_client()
    if not rts.redis.exists(key):
        labels = {
            "type": "orderbook_depth",
            "exchange": exchange,
            "base_pair": base_pair,
            "quote_pair": quote_pair,
            "side": side.value,
            "depth": depth
        }
        logger.info(f"Created redis key {key}")
        rts.create(key, labels=labels)


def record_order_book_price(rts: Client, timestamp_ms: int, exchange: str, base_pair: str, quote_pair: str, side: Side, depth: float, value: float) -> Optional[dict]:
    """Record order book state for later analysis.

    Example for what is the price of a Bitcoin if buying Bitcoin with 1000 USD in Kucoin.
    Value is the value of Bitcoin bought at the price.

    :param timestamp_ms: Bot tick UNIX timestamp as milliseconds
    :param exchange: "kucoin"
    :param base_pair: "BTC"
    :param quote_pair: "USDT"
    :param side: "buy"
    :param depth: Depth of the recording as quantity of base pair
    :param reporter: "mikko"
    :param value: 32,123
    """

    global redis_updates

    assert type(timestamp_ms) == int, "Got invalid timestamp: %s" % type(timestamp_ms)
    assert type(value) == float, "Got invalid value: %s" % type(value)

    key = format_key(exchange, base_pair, quote_pair, side, depth)

    try:
        # Redis Timeseries expects timestamps as milliseconds
        rts.add(key, timestamp_ms, value)
        redis_updates += 1

    except redis.exceptions.ResponseError as e:
        if str(e) == 'TSDB: Error at upsert, update is not supported in BLOCK mode':
            # Ignore duplicate keys
            logger.exception(e)
            return None

        #existing = rts.range(key, timestamp, timestamp)
        raise RuntimeError(f"Could not record {key}={value} at timestamp {timestamp_ms}: {e}") from e


@to_async(executor=redis_thread_pool)
def record_depths(timestamp_ms: int, depth_data: List[dict]):
    """Write multiple depths to the Redis.

    Run in a separate thread to not to block.
    """

    assert is_enabled(), "Redis recording is not turned on"

    rts = get_client()

    for r in depth_data:
        # See Watcher.get_depth_record()
        exchange_name = r["exchange_name"]
        market = r["market"]
        base_pair, quote_pair = market.split("/")
        for depth, price in r["ask_levels"].items():
            record_order_book_price(rts, timestamp_ms, exchange_name, base_pair, quote_pair, Side.ask, depth, price)
        for depth, price in r["bid_levels"].items():
            record_order_book_price(rts, timestamp_ms, exchange_name, base_pair, quote_pair, Side.bid, depth, price)


