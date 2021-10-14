# Arbitrage opportunity tracker

This Python application listens to centralised cryptocurrency exchange orderbooks to track arbitrage opportunities between exchanges.

When there is an arbitrage opportunity an alert is generated.

This project uses [CCXT Pro](https://ccxt.pro/) that is a paid service. You need to access to the private Github repository of CCXT Pro to install this project.

**This project is not going to be actively maintained. If you are interested using this code please reach out in Discord.** 

# Installation

Checkout.

Get submodules.

```python
git submodule update --recursive --init
```

Install with Poetry

```shell
poetry install
```

# Running

Start Redis with Timeseries extension for recording depth data.
This will start a Redis instance with password configured by `REDIS_PASSWORD` environment variable.

```shell
# Read REDIS_HOST and REDIS_PASSWORD
source secrets-local.env 
docker-compose up
```

Activate Poetry shell extensions

```shell
poetry shell
```

Then 

```shell
python order_book_recorder/main.py --no-live
```

# Configuring the Python Telegram bot for a group chat 

Get a Telegram API key from Botfather.

Add the bot in to a chat group.

Add the `TELEGRAM_API_KEY` in `secrets.env`.

Query active messages using JQ.

```shell
# Read TG API key from the secrets file
source secrets.env

# Get the chat messages for the bot and extract chat id from those
curl https://api.telegram.org/bot$TELEGRAM_API_KEY/getUpdates | jq
```

Extract chat id from the output and add it to `secrets.env`:

```
export TELEGRAM_CHAT_ID="-111113672"
```


# Examining time series data

Ask and bid price is recorded to [Redis Timeseries](https://oss.redis.com/redistimeseries/) at depths specified in the config.

Here is an example how to examine this data with `redis-cli`:

```shell
docker exec -it redistimeseries redis-cli
```

Then:

```
AUTH yourlocalpassword
keys *
```

You should see recorder data:


```
  1) 
  2) "Orderbook depth: Coinbase BTC-EUR bid at 0.04"
  3) "Orderbook depth: Exmo BTC-GBP ask at 0.04"
  4) "Orderbook depth: Bitfinex BTC-EUR bid at 0.04"
```

You can query it. For example to get Bitfinex ETH-EUR ask prices all-time.

```
127.0.0.1:6379> TS.RANGE "Orderbook depth: Bitfinex ETH-EUR ask at 3" - + AGGREGTION avg
 1) 1) (integer) 1634236371966
    2) 3252.50454148169
 2) 1) (integer) 1634236373112
    2) 3252.43330625139
...
```

# Background

This pile of scripts was originally created to see what fiat pair arbitrage opportunities there exists in the markets. The code is designed for crude arbitrage, not for high-frequency systems. The main goal is to have easily modifieable code base.

# More information

[Visit Trading Strategy Discord for help with algorithmic trading](https://tradingstrategy.ai/community).

