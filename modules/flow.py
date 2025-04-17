import os
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardRemove, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from modules.states import UserState
from modules.email_sender import send_email
from modules.auth import handle_authorization, is_valid_email, normalize_email
from modules.storage import db_get_user_by_telegram_id, db_get_email_by_id
from modules.template_engine import render_template
from modules.config import ticket_categories
from modules.log_utils import log_async_call
from modules.logging_config import logger
from modules.config import message_limits

# Загрузка переменных назначения
load_dotenv()
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL")
SUPPORT_CHAT_ID = os.getenv("SUPPORT_CHAT_ID")

max_submission_length = message_limits.get("max_submission_length", 1500)

@log_async_call
async def handle_idle_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.first_name or user.username or "user"
    user_input = update.message.text.strip()

    if is_valid_email(normalize_email(user_input)):
        # Вне зависимости от авторизации пробуем авторизоваться или переавторизоваться
        logger.debug(f"User {user.id} provided email-like input in IDLE state: '{user_input}'")
        await handle_authorization(update, context)
        return

    try:
        user_data = db_get_user_by_telegram_id(user.id)
        is_authorized = user_data and user_data.get("is_authorized")

        if not is_authorized:
            # Не авторизован и сообщение не email — предлагаем ввести почту
            context.user_data["state"] = UserState.WAITING_FOR_EMAIL
            text = render_template("auth_start.txt", username=username)
            logger.info(f"User {user.id} prompted for email input")
            await update.message.reply_text(text)
            return

        # Авторизован, но сообщение не email
        await handle_unknown_message(update, context);
    
    except Exception as e:
        logger.exception(f"Error in handle_idle_state for user {user.id}: {e}")
        await update.message.reply_text("An unexpected error occurred. Please try again later.")
        
@log_async_call
async def handle_request_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    query = update.callback_query
    try:
        context.user_data["state"] = UserState.WAITING_FOR_TOPIC
        text = render_template("select_topic.txt")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(cat, callback_data=f"topic:{cat}")]
            for cat in ticket_categories
        ])
        await query.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)
    
    except Exception as e:
        logger.exception(f"Error in handle_request_button for user {user.id}: {e}")
        await update.message.reply_text("An unexpected error occurred. Please try again later.")

@log_async_call
async def handle_topic_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    query = update.callback_query
    selected_topic = query.data.removeprefix("topic:")

    if selected_topic not in ticket_categories:
        logger.warning(f"Invalid topic selected by user {user.id}: {selected_topic}")
        text = render_template("invalid_topic.txt")
        await query.message.reply_text(text)
        return

    logger.info(f"User {user.id} selected topic: {selected_topic}")
    context.user_data["selected_topic"] = selected_topic
    context.user_data["state"] = UserState.WAITING_FOR_MESSAGE_TEXT

    try:
        text = render_template("enter_message.txt", topic=selected_topic)
        await query.message.reply_text(text, parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
    except Exception as e:
        logger.exception(f"Error in handle_topic_selection for user {user.id}: {e}")
        await query.message.reply_text("An unexpected error occurred. Please try again later.")

@log_async_call
async def handle_text_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_message = update.message.text.strip()

    if len(user_message) > max_submission_length:
        logger.warning(f"User {user.id} submitted too long message: {len(user_message)} chars")
        warning = render_template("message_too_long.txt", max_length=max_submission_length)
        await update.message.reply_text(warning)
        return

    user_data = db_get_user_by_telegram_id(user.id)
    email = None
    if user_data and user_data.get("email_id"):
        email = db_get_email_by_id(user_data["email_id"])

    if not email:
        logger.error(f"Email not found for user ID {user.id}")
        await update.message.reply_text("An unexpected error occurred. Please try again later.")
        return

    topic = context.user_data.get("selected_topic", "N/A")
    username = user.username or user.first_name or "N/A"
    telegram_id = user.id

    text_summary = render_template(
        "ticket_summary.txt",
        username=username,
        telegram_id=telegram_id,
        email=email,
        topic=topic,
        message=user_message
    )

    try:
        if SUPPORT_CHAT_ID:
            try:
                await context.bot.send_message(chat_id=SUPPORT_CHAT_ID, text=text_summary)
                logger.info(f"Message from user {user.id} sent to support chat")
            except Exception as e:
                logger.error(f"Failed to send message to support chat: {e}")

        if SUPPORT_EMAIL:
            try:
                html_body = render_template(
                    "support_email.html",
                    telegram_username=username,
                    telegram_id=telegram_id,
                    email=email,
                    topic=topic,
                    message=user_message
                )
                send_email(
                    subject=f"New support request: {topic}",
                    to_address=SUPPORT_EMAIL,
                    text_body=text_summary,
                    html_body=html_body
                )
                logger.info(f"Email from user {user.id} sent to {SUPPORT_EMAIL}")
            except Exception as e:
                logger.error(f"Failed to send email to support: {e}")

        await update.message.reply_text(
            render_template("ticket_sent.txt"),
            reply_markup=ReplyKeyboardRemove()
        )

        context.user_data["state"] = UserState.IDLE

    except Exception as e:
        logger.exception(f"Error in handle_text_submission: {e}")
        await update.message.reply_text("An unexpected error occurred. Please try again later.")
       
@log_async_call    
async def handle_unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        username = user.first_name or user.username or "user"
        logger.info(f"Unknown message from user {user.id}")
        text = render_template("invalid_input.txt", username=username)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

    except Exception as e:
        logger.exception(f"Error in handle_unknown_message: {e}")
        await update.message.reply_text("An unexpected error occurred. Please try again later.")
