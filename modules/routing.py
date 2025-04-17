from telegram import Update
from telegram.ext import ContextTypes
from modules.states import UserState
from modules.auth import handle_authorization, handle_email_change_confirmation
from modules.flow import handle_topic_selection, handle_text_submission, handle_idle_state, handle_unknown_message
from modules.log_utils import log_async_call
from modules.logging_config import logger


@log_async_call
async def route_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Главный маршрутизатор сообщений пользователя в зависимости от его состояния.
    Вызывается при любом текстовом сообщении, не являющемся командой.
    """
    # Безопасная инициализация состояния, если оно ещё не задано
    state = context.user_data.get("state")
    if state is None:
        context.user_data["state"] = UserState.IDLE
        state = UserState.IDLE
        logger.info(f"Initialized state for user {update.effective_user.id}: {state}")
    else:
        logger.info(f"Routing message for user {update.effective_user.id} in state: {state}")

    # Роутинг на основании текущего состояния
    if state == UserState.IDLE:
        await handle_idle_state(update, context)
        
    if state == UserState.WAITING_FOR_EMAIL:
        await handle_authorization(update, context)

    elif state == UserState.CONFIRMING_EMAIL_CHANGE:
        await handle_email_change_confirmation(update, context)

    elif state == UserState.WAITING_FOR_TOPIC:
        await handle_topic_selection(update, context)

    elif state == UserState.WAITING_FOR_MESSAGE_TEXT:
        await handle_text_submission(update, context)

    else:
        await handle_unknown_message(update, context)


def reset_user_state(context: ContextTypes.DEFAULT_TYPE):
    """
    Сброс состояния пользователя в IDLE (по умолчанию).
    """
    context.user_data["state"] = UserState.IDLE
