from order_book_recorder import telegram


async def notify(title, msg):
    if telegram.is_enabled():
        # TODO Do fancy formatting later
        msg = title + "\n" + msg
        await telegram.send_message(msg)