import os
import logging

import ccxt
import ccxtpro
from ccxtpro.base.exchange import Exchange as ProExchange
from ccxt.base.exchange import Exchange as SyncExchange


logger = logging.getLogger(__name__)


# Watch depths for different coins

# $100, $500, $2000, $5000
#BTC_DEPTHS = [0.002, 0.01, 0.04, 0.1]
#ETH_DEPTHS = [0.0285, 0.1428, 0.5714, 1.4285]

BTC_DEPTHS = [0.1]
ETH_DEPTHS = [1.4285]

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


async def setup_exchanges():
    exchanges = {
        "Huobi": ccxtpro.huobi({'enableRateLimit': True}),
        "Kraken": ccxtpro.kraken({'enableRateLimit': True}),
        "Gemini": ccxt.gemini({'enableRateLimit': True}),
        "Coinbase": ccxtpro.coinbasepro({'enableRateLimit': True}),
        "Exmo": ccxt.exmo({'enableRateLimit': True}),
    }

    for name, xchg in exchanges.items():

        if isinstance(xchg, ProExchange):
            # CCXT Pro
            logger.info("Loading markets for %s", name)
            await xchg.load_markets()
        else:
            # CCXT blocking API
            xchg.load_markets()

    return exchanges