"""

"""

import ccxtpro
import asyncio
from pprint import pprint


class WatchedExchange:
    pass


depths = {

}


async def setup_exchanges():
    pass


async def main():
    exchange = ccxtpro.huobi({'enableRateLimit': True})
    await exchange.load_markets()
    print(exchange.symbols)
    import ipdb ; ipdb.set_trace()

    while True:
        orderbook = await exchange.watch_order_book('ETH/BTC')
        print(orderbook['asks'][0], orderbook['bids'][0])

asyncio.get_event_loop().run_until_complete(main())