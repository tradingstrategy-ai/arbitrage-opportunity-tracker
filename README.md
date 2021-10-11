# Order book recorder

Record centralised cryptocurrency exchange orderbooks to track arbitrage opportunities.

This recorder records the depth at specific levels to a Redis Time Series database.

This project uses [CCXT Pro](https://ccxt.pro/) that is a paid service. You need to access to the private Github repository of CCXT Pro to install this project.

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

# More information

[Visit Trading Strategy Discord for help with algorithmic trading](https://tradingstrategy.ai/community).

