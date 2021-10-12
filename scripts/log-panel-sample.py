import logging
from typing import List

from rich.layout import Layout
from rich.panel import Panel
from rich import print

from order_book_recorder.logger import setup_logging
from order_book_recorder.logtable import BufferedOutputHandler, refresh_log_messages

logger = logging.getLogger()

captured_log: List[str] = []


def generate_log_panel():
    table = refresh_log_messages(captured_log)
    return table


def setup_log():
    global logger
    logger = setup_logging()
    live_log_handler = BufferedOutputHandler(captured_log)
    logger.handlers.clear()
    logger.handlers.append(live_log_handler)


setup_log()


layout = Layout()

layout.split_row(
    Layout(name="left"),
    Layout(name="right"),
)

logger.error("Error")
logger.info("Test message 1, %d %d", 2, 3)
logger.debug("Not visible")

# layout["left"].update(generate_table())
layout["left"].update(Panel("Hello!"))
layout["right"].update(generate_log_panel())

print(layout)
