import os
import logging

import ccxt
import ccxtpro
from ccxtpro.base.exchange import Exchange as ProExchange
from ccxt.base.exchange import Exchange as SyncExchange


logger = logging.getLogger(__name__)


# Watch depths for different coins

# $100, $500, $2000, $5000
BTC_DEPTHS = [0.002, 0.01, 0.04, 0.1]
ETH_DEPTHS = [0.0285, 0.1428, 0.5714, 1.4285]

MARKETS = ["BTC/GBP", "ETH/GBP", "BTC/EUR", "ETH/EUR"]

MARKET_DEPTHS = {
    "BTC/GBP": BTC_DEPTHS,
    "BTC/EUR": BTC_DEPTHS,
    "ETH/GBP": ETH_DEPTHS,
    "ETH/EUR": ETH_DEPTHS,
}


async def setup_exchanges():
    exchanges = {
        "Huobi": ccxtpro.huobi({'enableRateLimit': True}),
        "Kraken": ccxtpro.kraken({'enableRateLimit': True}),
        "Gemini": ccxt.gemini({'enableRateLimit': True}),
        "Coinbase": ccxtpro.coinbasepro({'enableRateLimit': True}),
        "Exmo": ccxt.exmo({
            'apiKey': os.environ["EXMO_API_KEY"],
            'secret': os.environ["EXMO_API_SECRET"],
            'enableRateLimit': True
        }),
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