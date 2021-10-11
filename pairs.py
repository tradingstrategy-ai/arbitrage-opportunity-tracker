


async def find_pairs(exchange, quote_token: str):
    await exchange.load_markets()
    for s in exchange.symbols:
        if quote_token in s:
            print(s)

