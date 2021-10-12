import os
import logging

import ccxt
import ccxtpro
from ccxtpro.base.exchange import Exchange as ProExchange
from ccxt.base.exchange import Exchange as SyncExchange


logger = logging.getLogger(__name__)


async def setup_exchanges():
    exchanges = {
        "huobi": ccxtpro.huobi({'enableRateLimit': True}),
        "kraken": ccxtpro.kraken({'enableRateLimit': True}),
        "gemini": ccxt.gemini({'enableRateLimit': True}),
        "coinbase": ccxtpro.coinbasepro({'enableRateLimit': True}),
        "exmo": ccxt.exmo({
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