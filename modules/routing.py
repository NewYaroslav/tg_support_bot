import time
from telegram import Update
from telegram.ext import ContextTypes
from modules.states import UserState
from modules.auth import handle_authorization, handle_email_change_confirmation
from modules.flow import handle_request_button, handle_topic_selection, handle_text_submission, handle_idle_state, handle_unknown_message
from modules.media_group_buffer import pending_media_groups, media_group_timestamps
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

    message = update.message
    media_group_id = message.media_group_id

    if media_group_id and media_group_id in media_group_timestamps:
        current_time = time.time()
        pending_media_groups[media_group_id].append({
            "message": message,
            "topic": context.user_data.get("selected_topic", "N/A")
        })
        media_group_timestamps[media_group_id] = current_time
        return  # Ожидаем, пока медиагруппа не соберётся — обрабатываем позже в check_media_group_expiry_loop

    # Роутинг на основании текущего состояния
    if state == UserState.IDLE:
        await handle_idle_state(update, context)
        
    elif state == UserState.WAITING_FOR_EMAIL:
        await handle_authorization(update, context)

    elif state == UserState.CONFIRMING_EMAIL_CHANGE:
        await handle_email_change_confirmation(update, context)
    
    elif state == UserState.WAITING_FOR_REQUEST_BUTTON:
        await handle_request_button(update, context)

    elif state == UserState.WAITING_FOR_TOPIC:
        await handle_topic_selection(update, context)

    elif state == UserState.WAITING_FOR_MESSAGE_TEXT:
        await handle_text_submission(update, context)

    else:
        await handle_unknown_message(update, context)


@log_async_call
async def handle_inline_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    state = context.user_data.get("state")

    if query.data == "submit_request":
        if state == UserState.WAITING_FOR_REQUEST_BUTTON:
            await handle_request_button(update, context)
        else:
            await query.message.reply_text("An unexpected error occurred. Please try again later.")

    elif query.data.startswith("topic:"):
        if state == UserState.WAITING_FOR_TOPIC:
            await handle_topic_selection(update, context)
        else:
            await query.message.reply_text("An unexpected error occurred. Please try again later.")

    else:
        await query.message.reply_text("An unexpected error occurred. Please try again later.")
        

