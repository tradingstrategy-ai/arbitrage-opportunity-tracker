# Arbitrage opportunity tracker

Record centralised cryptocurrency exchange orderbooks to track arbitrage opportunities between exchanges.

This recorder records the depth at specific levels to a Redis Time Series database.

This project uses [CCXT Pro](https://ccxt.pro/) that is a paid service. You need to access to the private Github repository of CCXT Pro to install this project.

**This project is not going to be actively maintained. If you are interested using this code please reach out in Discord.** 

# Instalation

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
python record.py
```

# Background

This pile of scripts was originally created to see what fiat pair arbitrage opportunities there exists in the markets. The code is designed for crude arbitrage, not for high-frequency systems. The main goal is to have easily modifieable code base.

# More information

[Visit Trading Strategy Discord for help with algorithmic trading](https://tradingstrategy.ai/community).

