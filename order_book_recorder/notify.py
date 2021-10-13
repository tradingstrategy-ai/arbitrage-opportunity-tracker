from order_book_recorder import telegram


def notify(title, msg):
    if telegram.is_enabled():
        # TODO Do fancy formatting later
        msg = title + "\n" + msg
        telegram.send_message(msg)