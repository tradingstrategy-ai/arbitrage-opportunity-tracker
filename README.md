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

# Background

This pile of scripts was originally created to see what fiat pair arbitrage opportunities there exists in the markets. The code is designed for crude arbitrage, not for high-frequency systems. The main goal is to have easily modifieable code base.

# More information

[Visit Trading Strategy Discord for help with algorithmic trading](https://tradingstrategy.ai/community).

