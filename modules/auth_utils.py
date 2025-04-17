import os
from dotenv import load_dotenv
from modules.storage import db_is_admin

load_dotenv()
ROOT_ADMIN_ID = int(os.getenv("ROOT_ADMIN_ID", 0))

def is_admin(telegram_id: int) -> bool:
    try:
        telegram_id = int(telegram_id)
    except (ValueError, TypeError):
        return False
    return telegram_id == ROOT_ADMIN_ID or db_is_admin(telegram_id)

def is_root_admin(telegram_id: int) -> bool:
    try:
        return int(telegram_id) == ROOT_ADMIN_ID
    except (ValueError, TypeError):
        return False