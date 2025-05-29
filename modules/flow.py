import os
import time
import asyncio
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardRemove, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
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
from modules.media_group_buffer import pending_media_groups, media_group_timestamps, MEDIA_GROUP_TIMEOUT_SEC

# Загрузка переменных назначения
load_dotenv()
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL")
SUPPORT_CHAT_ID = os.getenv("SUPPORT_CHAT_ID")

max_submission_length = message_limits.get("max_submission_length", 1500)


@log_async_call
async def handle_idle_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.first_name or user.username or "user"
    message = update.message
    user_input = (message.text or message.caption or "").strip()

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

    if query is None:
        logger.error(f"Expected CallbackQuery, but got None (user: {user.id})")
        await update.message.reply_text("Произошла ошибка: кнопка не определена.")
        return

    if not query.data or not query.data.startswith("topic:"):
        logger.warning(f"Unexpected callback data: {query.data}")
        await query.message.reply_text("Неверный выбор. Попробуйте снова.")
        return

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
    message = update.message
    telegram_id = user.id
    username = user.username or user.first_name or "N/A"
    
    # Получить текст, либо подпись, либо пусто
    user_message = message.text or message.caption or ""
    user_message = user_message.strip()

    if not user_message:
        user_message = "(no text)"
        
    # Данные для медиагруппы
    media_group_id = message.media_group_id
    current_time = time.time()

    if len(user_message) > max_submission_length:
        logger.warning(f"User {user.id} submitted too long message: {len(user_message)} chars")
        warning = render_template("message_too_long.txt", max_length=max_submission_length)
        await update.message.reply_text(warning)
        return
        
    if media_group_id:
        pending_media_groups[media_group_id].append({
            "message": message,
            "topic": context.user_data.get("selected_topic", "N/A")
        })
        media_group_timestamps[media_group_id] = current_time
        context.user_data["state"] = UserState.IDLE
        return

    # Получаем email
    user_data = db_get_user_by_telegram_id(user.id)
    email = None
    if user_data and user_data.get("email_id"):
        email = db_get_email_by_id(user_data["email_id"])

    if not email:
        logger.error(f"Email not found for user ID {user.id}")
        await update.message.reply_text("An unexpected error occurred. Please try again later.")
        context.user_data["state"] = UserState.IDLE
        return

    topic = context.user_data.get("selected_topic", "N/A")

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
                
            # Собираем все типы вложений
            media_sent = False
            
            # Фото — может быть несколько
            if message.photo:
                largest_photo = message.photo[-1]  # последнее — самое большое
                try:
                    await context.bot.send_photo(chat_id=SUPPORT_CHAT_ID, photo=largest_photo.file_id)
                    media_sent = True
                except Exception as e:
                    logger.error(f"Failed to send photo from user {user.id}: {e}")

            # Документ
            if message.document:
                try:
                    await context.bot.send_document(chat_id=SUPPORT_CHAT_ID, document=message.document.file_id)
                    media_sent = True
                except Exception as e:
                    logger.error(f"Failed to send document from user {user.id}: {e}")

            # Видео
            if message.video:
                try:
                    await context.bot.send_video(chat_id=SUPPORT_CHAT_ID, video=message.video.file_id)
                    media_sent = True
                except Exception as e:
                    logger.error(f"Failed to send video from user {user.id}: {e}")

            # Голосовые
            if message.voice:
                try:
                    await context.bot.send_voice(chat_id=SUPPORT_CHAT_ID, voice=message.voice.file_id)
                    media_sent = True
                except Exception as e:
                    logger.error(f"Failed to send voice from user {user.id}: {e}")

            # Аудио
            if message.audio:
                try:
                    await context.bot.send_audio(chat_id=SUPPORT_CHAT_ID, audio=message.audio.file_id)
                    media_sent = True
                except Exception as e:
                    logger.error(f"Failed to send audio from user {user.id}: {e}")

            if media_sent:
                logger.info(f"Media from user {user.id} sent to support chat")

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
async def process_media_group(entries, context):
    if not entries:
        return

    first = entries[0]["message"]
    topic = entries[0]["topic"]

    chat_id = first.chat.id
    user = first.from_user
    telegram_id = user.id
    username = user.username or user.first_name or "N/A"

    caption = first.caption or ""

    user_data = db_get_user_by_telegram_id(user.id)
    email = db_get_email_by_id(user_data["email_id"]) if user_data else None

    text_summary = render_template(
        "ticket_summary.txt",
        username=username,
        telegram_id=telegram_id,
        email=email,
        topic=topic,
        message=caption.strip()
    )

    try:
        await context.bot.send_message(chat_id=SUPPORT_CHAT_ID, text=text_summary)

        media = [
            InputMediaPhoto(media=entry["message"].photo[-1].file_id)
            for entry in entries if entry["message"].photo
        ]

        if media:
            await context.bot.send_media_group(chat_id=SUPPORT_CHAT_ID, media=media)

        await first.reply_text(render_template("ticket_sent.txt"))
        
        # context.user_data["state"] = UserState.IDLE

    except Exception as e:
        logger.exception(f"Error in process_media_group: {e}")
        await first.reply_text("An unexpected error occurred. Please try again later.")
    
@log_async_call 
async def check_media_group_expiry_loop(app):
    while True:
        await asyncio.sleep(1.0)

        expired_groups = [
            group_id for group_id, ts in media_group_timestamps.items()
            if time.time() - ts > MEDIA_GROUP_TIMEOUT_SEC
        ]

        for group_id in expired_groups:
            entries = pending_media_groups.pop(group_id, [])
            media_group_timestamps.pop(group_id, None)

            if entries:
                context = ContextTypes.DEFAULT_TYPE(application=app)
                await process_media_group(entries, context)

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
