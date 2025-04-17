import logging
import functools
from rich.console import Console
from telegram.error import TelegramError
from modules.logging_config import logger
import sqlite3

console = Console()


def log_async_call(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        logger.debug(f"{func.__name__} called")
        try:
            result = await func(*args, **kwargs)
            logger.debug(f"{func.__name__} completed successfully")
            return result

        except TelegramError as te:
            logger.error(f"Telegram API error in {func.__name__}: {te}")
            console.print(f"[red]Telegram API error in {func.__name__}: {te}[/red]")
            raise

        except sqlite3.DatabaseError as db_err:
            logger.error(f"Database error in {func.__name__}: {db_err}")
            console.print(f"[red]Database error in {func.__name__}: {db_err}[/red]")
            raise

        except Exception as e:
            logger.exception(f"Unhandled exception in {func.__name__}: {e}")
            console.print(f"[red]Unexpected error in {func.__name__}: {e}[/red]")
            raise

    return wrapper

def log_sync_call(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(f"{func.__name__} called")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} completed successfully")
            return result

        except TelegramError as te:
            logger.error(f"Telegram API error in {func.__name__}: {te}")
            console.print(f"[red]Telegram API error in {func.__name__}: {te}[/red]")
            raise

        except sqlite3.DatabaseError as db_err:
            logger.error(f"Database error in {func.__name__}: {db_err}")
            console.print(f"[red]Database error in {func.__name__}: {db_err}[/red]")
            raise

        except Exception as e:
            logger.exception(f"Unhandled exception in {func.__name__}: {e}")
            console.print(f"[red]Unexpected error in {func.__name__}: {e}[/red]")
            raise

    return wrapper