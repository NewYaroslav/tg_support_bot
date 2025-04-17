from telegram import Update
from telegram.ext import ContextTypes
from modules.log_utils import log_async_call
from modules.logging_config import logger
from modules.storage import (
    db_add_allowed_email,
    db_ban_allowed_email,
    db_remove_allowed_email,
    db_get_email_row,
)
from modules.auth_utils import is_admin
from modules.template_engine import render_template
from modules.config import authorization_ui

email_status_labels = authorization_ui.get("email_status_labels", {})

@log_async_call
async def handle_add_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(render_template("not_authorized.txt"))
        return

    if not context.args:
        await update.message.reply_text(render_template("email_required.txt", command="/add_email"))
        return

    added = []
    for email in context.args:
        email = email.strip()
        db_add_allowed_email(email)
        logger.info(f"Admin {user.id} added allowed email: {email}")
        added.append(email)

    await update.message.reply_text(render_template("email_added.txt", emails=added))

@log_async_call
async def handle_ban_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(render_template("not_authorized.txt"))
        return

    if not context.args:
        await update.message.reply_text(render_template("email_required.txt", command="/ban_email"))
        return

    banned = []
    for email in context.args:
        email = email.strip()
        db_ban_allowed_email(email)
        logger.info(f"Admin {user.id} banned email: {email}")
        banned.append(email)

    await update.message.reply_text(render_template("email_banned.txt", emails=banned))

@log_async_call
async def handle_remove_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(render_template("not_authorized.txt"))
        return

    if not context.args:
        await update.message.reply_text(render_template("email_required.txt", command="/remove_email"))
        return

    removed = []
    for email in context.args:
        email = email.strip()
        db_remove_allowed_email(email)
        logger.info(f"Admin {user.id} removed allowed email: {email}")
        removed.append(email)

    await update.message.reply_text(render_template("email_removed.txt", emails=removed))

@log_async_call
async def handle_check_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(render_template("not_authorized.txt"))
        return

    if not context.args:
        await update.message.reply_text(render_template("email_required.txt", command="/check_email"))
        return

    results = []
    for email in context.args:
        email = email.strip()
        row = db_get_email_row(email)
        if not row:
            results.append(render_template("email_status_not_found.txt", email=email))
        else:
            status_key = "banned" if row["is_banned"] else "allowed"
            status_label = email_status_labels.get(status_key, status_key)
            results.append(render_template("email_status_found.txt", email=email, status_key=status_label))

    await update.message.reply_text("\n".join(results))