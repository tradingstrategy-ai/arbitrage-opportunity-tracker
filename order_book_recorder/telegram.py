import requests

from order_book_recorder import config


def is_enabled() -> bool:
    return config.TELEGRAM_CHAT_ID and config.TELEGRAM_API_KEY


def send_message(text):
    token = config.TELEGRAM_API_KEY
    chat_id = config.TELEGRAM_CHAT_ID

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {
       "chat_id": chat_id,
       "text": text,
    }
    resp = requests.get(url, params=params)

    # Throw an exception if Telegram API fails
    resp.raise_for_status()