import os
import logging

import ccxt
import ccxtpro
from ccxtpro.base.exchange import Exchange as ProExchange


logger = logging.getLogger(__name__)


# Watch depths for different coins
# Adjust this levels with CCXT order book sample limit

# $100, $500, $2000, $5000
# BTC_DEPTHS = [0.002, 0.01, 0.04, 0.1]
# ETH_DEPTHS = [0.0285, 0.1428, 0.5714, 1.4285]

BTC_DEPTHS = [0.04, 0.2]
ETH_DEPTHS = [0.5, 3]

# BTC_DEPTHS = [0.04]
# ETH_DEPTHS = [0.5]

MARKETS = ["BTC/GBP", "ETH/GBP", "BTC/EUR", "ETH/EUR"]

MARKET_DEPTHS = {
    "BTC/GBP": BTC_DEPTHS,
    "BTC/EUR": BTC_DEPTHS,
    "ETH/GBP": ETH_DEPTHS,
    "ETH/EUR": ETH_DEPTHS,
}

# Raise alert if the profitability is more than 15 BPS
# ALERT_THRESHOLD = 0.0018
ALERT_THRESHOLD = 0.0018

# Retrigger alert for every 5 BPS move to higher arb
RETRIGGER_THRESHOLD = 0.0005

TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

TELEGRAM_API_KEY = os.environ.get("TELEGRAM_API_KEY")


if os.environ.get("REDIS_HOST"):
    REDIS_CONFIG = {
        "host": os.environ["REDIS_HOST"],
        "port": 6379,
        "retry_on_timeout": True,
        "socket_timeout": 20
    }

    if os.environ.get("REDIS_PASSWORD"):
        REDIS_CONFIG["password"] = os.environ["REDIS_PASSWORD"]

    # Fire and forget Redis io
    REDIS_BG_WRITES = True

else:
    REDIS_CONFIG = None


async def setup_exchanges():
    exchanges = {
        "Huobi": ccxtpro.huobi({'enableRateLimit': True}),
        "Kraken": ccxtpro.kraken({'enableRateLimit': True}),
        "FTX": ccxtpro.ftx({'enableRateLimit': True}),
        "Bitfinex": ccxtpro.bitfinex({'enableRateLimit': True}),
        "Bitstamp": ccxtpro.bitstamp({'enableRateLimit': True}),
        "Gemini": ccxt.gemini({'enableRateLimit': True}),
        "Coinbase": ccxtpro.coinbasepro({'enableRateLimit': True}),
        "Exmo": ccxt.exmo({'enableRateLimit': True}),
    }

    for name, xchg in exchanges.items():

        if isinstance(xchg, ProExchange):
            # CCXT Pro
            logger.info("Loading markets for %s %s", name, xchg)
            await xchg.load_markets()
        else:
            # CCXT blocking API
            logger.info("Calling blocking API for %s %s", name, xchg)
            xchg.load_markets()

    return exchanges