import re
import yaml
import asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from modules.states import UserState
from modules.template_engine import render_template
from modules.storage import (
    db_add_user,
    db_get_user_by_telegram_id,
    db_update_user_email,
    db_get_email_row,
    db_get_email_by_id,
)
from modules.config import auth_config, telegram_start, authorization_ui, ticket_categories
from modules.log_utils import log_async_call
from modules.logging_config import logger
from rich.console import Console

console = Console()

email_pattern = re.compile(auth_config["email_pattern"])
email_autocomplete = auth_config["email_autocomplete"]

confirm_buttons = authorization_ui.get("confirm_change_buttons", {})
yes_text = confirm_buttons.get("yes", "Yes")
no_text = confirm_buttons.get("no", "No")

def normalize_email(input_text: str) -> str:
    if "@" not in input_text:
        return input_text.strip() + email_autocomplete
    return input_text.strip()

def is_valid_email(email: str) -> bool:
    return email_pattern.fullmatch(email) is not None

@log_async_call
async def handle_authorization(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    raw_input = update.message.text.strip()
    email = normalize_email(raw_input)
    username = user.first_name or user.username or "user"
    
    try:
        if not is_valid_email(email):
            text = render_template("auth_invalid.txt", username=username)
            logger.warning(f"Invalid email format from user {user.id}: '{raw_input}'")
            await update.message.reply_text(text)
            return

        # Получение текущих данных пользователя
        user_data = db_get_user_by_telegram_id(user.id)

        if user_data and user_data.get("is_authorized"):
            current_email_id = user_data.get("email_id")
            current_email = db_get_email_by_id(current_email_id)

            if current_email == email:
                text = render_template("auth_already.txt", email=current_email)
                logger.info(f"User {user.id} attempted to re-auth with same email: {email}")
                await update.message.reply_text(text)
                return

            # Иначе email отличается — запрашиваем подтверждение
            context.user_data["state"] = UserState.CONFIRMING_EMAIL_CHANGE
            context.user_data["pending_email"] = email
            text = render_template("auth_change_confirm.txt", old_email=current_email, new_email=email)
            logger.info(f"User {user.id} attempting to change email: {current_email} -> {email}")
            keyboard = [[yes_text, no_text]]
            await update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
            return

        # Авторизация или повторная
        
        # Проверка, зарегистрирован ли email в системе
        email_row = db_get_email_row(email)
        if not email_row:
            # Email не зарегистрирован — сохраняем пользователя, но без авторизации
            db_add_user(email=email, telegram_id=user.id, username=user.username, full_name=user.full_name, authorized=False)
            text = render_template("auth_not_registered.txt", email=email)
            context.user_data["state"] = UserState.WAITING_FOR_EMAIL
            logger.warning(f"Unregistered email attempt by user {user.id}: {email}")
            await update.message.reply_text(text)
            return
        elif email_row["is_banned"]:
            # Email есть, но он заблокирован — пользователь не должен быть авторизован
            db_add_user(email=email, telegram_id=user.id, username=user.username, full_name=user.full_name, authorized=False)
            text = render_template("auth_banned.txt", email=email)
            context.user_data["state"] = UserState.WAITING_FOR_EMAIL
            logger.warning(f"User {user.id} attempted to auth with banned email: {email}")
            await update.message.reply_text(text)
            return
            
        # Email зарегистрирован — авторизация
        db_add_user(email=email, telegram_id=user.id, username=user.username, full_name=user.full_name, authorized=True)
        logger.info(f"User {user.id} authorized successfully with email: {email}")

        text = render_template("auth_success.txt", username=username, email=email)
        await update.message.reply_text(text)
        
        if auth_config.get("send_topic_after_auth", True):
            delay = auth_config.get("delay_after_auth_success", 0)
            if delay > 0:
                await asyncio.sleep(delay)

            if auth_config.get("send_welcome_before_topic", False):
                text = render_template("welcome_user.txt", username=username, email=email, parse_mode="HTML")

                if telegram_start.get("show_action_button_if_authorized", False):
                    # Показываем кнопку — ждём нажатие, не отправляем топики
                    context.user_data["state"] = UserState.WAITING_FOR_REQUEST_BUTTON
                    button_text = telegram_start.get("action_button_text", "Submit a request")
                    keyboard = [[button_text]]
                    await update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
                    return
                else:
                    await update.message.reply_text(text)

            # Переход в состояние выбора темы
            context.user_data["state"] = UserState.WAITING_FOR_TOPIC
            text = render_template("select_topic.txt")
            keyboard = [[cat] for cat in categories]
            await update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        else:
            context.user_data["state"] = UserState.IDLE

    except Exception as e:
        logger.exception(f"Exception in handle_authorization for user {user.id}: {e}")
        await update.message.reply_text("An unexpected error occurred. Please try again later.")
    
@log_async_call
async def handle_email_change_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    decision = update.message.text.strip()
    pending_email = context.user_data.get("pending_email")
    user = update.effective_user
    username = user.first_name or user.username or "user"
    try:
        if decision == yes_text:
            success = db_update_user_email(user.id, pending_email)
            if success:
                context.user_data["email"] = pending_email
                context.user_data["state"] = UserState.IDLE
                text = render_template("auth_changed.txt", username=username, email=pending_email)
                console.print(f"[yellow]User {user.id} requests email change to: {pending_email}[/yellow]")
                await update.message.reply_text(text)
            else:
                db_add_user(email=pending_email, telegram_id=user.id, username=user.username, full_name=user.full_name, authorized=False)
                text = render_template("auth_not_registered.txt", email=pending_email)
                context.user_data["state"] = UserState.WAITING_FOR_EMAIL
                await update.message.reply_text(text)
        else:
            context.user_data["pending_email"] = None
            context.user_data["state"] = UserState.IDLE
            text = render_template("auth_change_cancelled.txt", username=username)
            await update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())
    except Exception as e:
        logger.exception(f"Exception in handle_email_change_confirmation for user {user.id}: {e}")
        await update.message.reply_text("An unexpected error occurred. Please try again later.")