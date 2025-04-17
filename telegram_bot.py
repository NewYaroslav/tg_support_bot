import os
from dotenv import load_dotenv
from telegram import BotCommand
from telegram.ext import Application, ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from jinja2 import Environment, FileSystemLoader
from rich.console import Console
import colorlog
from modules.template_engine import render_template
from modules.routing import route_message, handle_inline_button
from modules.common import handle_start_command, handle_help_command, handle_my_id_command
from modules.admin_commands import handle_add_email, handle_ban_email, handle_remove_email, handle_check_email
from modules.storage import db_init
from modules.config import telegram_menu
from modules.log_utils import log_async_call, log_sync_call
from modules.logging_config import logger

# Консоль и логгер
console = Console()

# Загрузка .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

@log_async_call
async def setup_bot_commands(app: Application):
    await app.bot.set_my_commands([
        BotCommand(cmd["command"], cmd["description"]) for cmd in telegram_menu
    ])

# Запуск
@log_sync_call
def run_telegram_bot():
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN not set in .env")
        console.print("[bold red]Error: BOT_TOKEN not set in .env[/bold red]")
        exit(1)

    logger.info("Starting Telegram bot...")
    db_init()

    app = ApplicationBuilder().token(BOT_TOKEN).post_init(setup_bot_commands).build()

    app.add_handler(CommandHandler("start", handle_start_command))
    app.add_handler(CommandHandler("help", handle_help_command))
    app.add_handler(CommandHandler("myid", handle_my_id_command))
    app.add_handler(CommandHandler("add_email", handle_add_email))
    app.add_handler(CommandHandler("ban_email", handle_ban_email))
    app.add_handler(CommandHandler("remove_email", handle_remove_email))
    app.add_handler(CommandHandler("check_email", handle_check_email))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_message))
    app.add_handler(CallbackQueryHandler(handle_inline_button))

    console.print("[bold green]Telegram bot is running[/bold green]")
    logger.info("Telegram bot is now polling for messages")
    app.run_polling()

if __name__ == "__main__":
    try:
        run_telegram_bot()
    except KeyboardInterrupt:
        console.print("\n[yellow][!] Stopped by user (Ctrl+C).[/yellow]")