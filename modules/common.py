import yaml
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from rich.console import Console
from modules.template_engine import render_template
from modules.storage import db_get_user_by_telegram_id, db_get_email_by_id
from modules.states import UserState
from modules.config import telegram_start
from modules.log_utils import log_async_call
from modules.logging_config import logger
from modules.auth_utils import is_admin

console = Console()

@log_async_call
async def handle_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.first_name or user.username or "user"

    try:
        user_data = db_get_user_by_telegram_id(user.id)

        if user_data and user_data.get("is_authorized"):
            # Уже авторизован
            email = db_get_email_by_id(user_data["email_id"])
            text = render_template("welcome_user.txt", username=username, email=email)
            logger.info(f"User {user.id} is already authorized. Email: {email}")

            if telegram_start.get("show_action_button_if_authorized", False):
                context.user_data["state"] = UserState.WAITING_FOR_REQUEST_BUTTON
                button_text = telegram_start.get("action_button_text", "Submit a request")
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(text=button_text, callback_data="submit_request")]
                ])

                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            else:
                context.user_data["state"] = UserState.IDLE
                await update.message.reply_text(text, parse_mode="HTML")

        else:
            # Не авторизован
            context.user_data["state"] = UserState.WAITING_FOR_EMAIL
            text = render_template("auth_start.txt", username=username)
            logger.info(f"User {user.id} is not authorized. Prompting for email.")
            await update.message.reply_text(text, parse_mode="HTML")

    except Exception as e:
        logger.exception(f"Error in handle_start_command for user {user.id}")
        await update.message.reply_text("An unexpected error occurred. Please try again later.")

@log_async_call
async def handle_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        admin = is_admin(user_id)
        template = "help_admin.txt" if admin else "help_user.txt"
        text = render_template(template)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode="HTML")
    
    except Exception as e:
        logger.exception("Error in handle_help_command")
        await update.message.reply_text("An unexpected error occurred. Please try again later.")

@log_async_call
async def handle_my_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    user_data = db_get_user_by_telegram_id(user.id)
    email = None

    if user_data and user_data.get("is_authorized"):
        email = db_get_email_by_id(user_data.get("email_id"))

    text = render_template(
        "my_id.txt",
        telegram_id=user.id,
        username=user.username or user.first_name or "user",
        chat_id=chat.id,
        email=email
    )

    await update.message.reply_text(text)
