import asyncio
import logging

import aiohttp

from order_book_recorder import config


logger = logging.getLogger(__name__)


def is_enabled() -> bool:
    return config.TELEGRAM_CHAT_ID and config.TELEGRAM_API_KEY


async def send_message(text, throttle_delay=3.0):
    token = config.TELEGRAM_API_KEY
    chat_id = config.TELEGRAM_CHAT_ID

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {
       "chat_id": chat_id,
       "text": text,
    }

    attempts = 10

    while attempts >= 0:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    return
                elif resp.status == 429:
                    logger.warning("Throttling Telegram, attempts %d", attempts)
                    attempts -= 1
                    await asyncio.sleep(throttle_delay)
                    continue
                else:
                    logger.error("Got Telegram response: %s", resp)
                    raise RuntimeError(f"Bad HTTP response: {resp}")




