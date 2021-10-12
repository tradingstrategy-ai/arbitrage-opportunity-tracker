import logging
from typing import List

from rich.table import Table


class BufferedOutputHandler(logging.Handler):
    """Keep log meessages in a memory buffer"""

    def __init__(self, buffer):
        logging.Handler.__init__(self)
        self.buffer = buffer

    def emit(self, record):
        """
        Emit a record.

        If a formatter is specified, it is used to format the record.
        The record is then written to the stream with a trailing newline.  If
        exception information is present, it is formatted using
        traceback.print_exception and appended to the stream.  If the stream
        has an 'encoding' attribute, it is used to determine how to do the
        output to the stream.
        """
        try:
            msg = self.format(record)
            self.buffer.append(msg)
        except RecursionError:  # See issue 36272
            raise
        except Exception:
            raise 
            # self.handleError(record)


def refresh_log_messages(messages: List[str]) -> Table:
    """Show log tail"""
    table = Table()
    table.add_column("Message")

    messages = messages[-20:]

    for msg in messages:
        table.add_row(msg)

    return table
