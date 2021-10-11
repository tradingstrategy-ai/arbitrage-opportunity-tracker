"""Fire up bunch of exchange connectors and see if they have interesting trading pairs for us"""
import ccxt
import ccxtpro
import asyncio


interesting_base_tokens = ["BTC", "ETH"]

interesting_quote_tokens = ["EUR", "GBP"]



async def main():

    very_interesting = []
    little_interesting = []

    exchanges = {
        "huobi": ccxt.huobi({'enableRateLimit': True}),
        "kraken": ccxt.kraken({'enableRateLimit': True}),
        "gemini": ccxt.gemini({'enableRateLimit': True}),
        "coinbase": ccxt.coinbase({'enableRateLimit': True}),
        "exmo": ccxt.exmo({'enableRateLimit': True}),
    }

    for name, x in exchanges.items():
        # import ipdb ; ipdb.set_trace()
        # await x.load_markets()
        x.load_markets()
        symbols = x.symbols
        for s in symbols:
            if s.endswith("EUR") or s.endswith("GBP"):
                if s.startswith("BTC") or s.startswith("ETH"):
                    very_interesting.append(f"{name}:{s}")
                else:
                    little_interesting.append(f"{name}:{s}")
        # await x.close()

    for pair in very_interesting:
        print("*** ", pair)

    for pair in little_interesting:
        print("* ", pair)


asyncio.get_event_loop().run_until_complete(main())