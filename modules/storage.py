import os
import sqlite3
from dotenv import load_dotenv
from modules.log_utils import log_sync_call
from modules.logging_config import logger

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "database/db.sqlite3")
ROOT_ADMIN_ID = int(os.getenv("ROOT_ADMIN_ID", 0))

@log_sync_call
def db_init():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Таблица разрешенных email-адресов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS allowed_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            is_banned INTEGER DEFAULT 0
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_allowed_email ON allowed_emails(email)")

    # Таблица пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            full_name TEXT,
            email_id INTEGER,
            is_authorized INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_topic TEXT,
            last_message TEXT,
            request_count INTEGER DEFAULT 0,
            FOREIGN KEY (email_id) REFERENCES allowed_emails(id)
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email_id ON users(email_id)")

    # Триггер для обновления updated_at
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_users_updated_at
        AFTER UPDATE ON users
        FOR EACH ROW
        BEGIN
            UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
        END;
    """)

    # Таблица админов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            telegram_id INTEGER PRIMARY KEY,
            is_top_level INTEGER DEFAULT 0
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_admins_telegram_id ON admins(telegram_id)")

    conn.commit()
    conn.close()
    logger.info("Database initialized")

@log_sync_call
def db_add_allowed_email(email: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO allowed_emails (email, is_banned)
        VALUES (?, 0)
        ON CONFLICT(email) DO UPDATE SET is_banned = 0
    """, (email,))
    conn.commit()
    conn.close()

@log_sync_call
def db_remove_allowed_email(email: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM allowed_emails WHERE email = ?", (email,))
    conn.commit()
    conn.close()

@log_sync_call
def db_ban_allowed_email(email: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE allowed_emails SET is_banned = 1 WHERE email = ?", (email,))
    conn.commit()
    conn.close()

@log_sync_call
def db_unban_allowed_email(email: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE allowed_emails SET is_banned = 0 WHERE email = ?", (email,))
    conn.commit()
    conn.close()

@log_sync_call
def db_get_user_by_telegram_id(telegram_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None
    
@log_sync_call
def db_get_email_by_id(email_id: int) -> str:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM allowed_emails WHERE id = ?", (email_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None
    
@log_sync_call
def db_get_email_row(email: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM allowed_emails WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

@log_sync_call
def db_add_user(email: str, telegram_id: int, username: str = None, full_name: str = None, authorized: bool = True):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, is_banned FROM allowed_emails WHERE email = ?", (email,))
    email_row = cursor.fetchone()

    if not email_row:
        cursor.execute("INSERT INTO allowed_emails (email, is_banned) VALUES (?, 1)", (email,))
        conn.commit()
        cursor.execute("SELECT id, is_banned FROM allowed_emails WHERE email = ?", (email,))
        email_row = cursor.fetchone()

    email_id, is_banned = email_row
    is_authorized = int(authorized and not is_banned)

    cursor.execute("""
        INSERT OR REPLACE INTO users (telegram_id, username, full_name, email_id, is_authorized)
        VALUES (?, ?, ?, ?, ?)
    """, (telegram_id, username, full_name, email_id, is_authorized))

    conn.commit()
    conn.close()
    
@log_sync_call
def db_update_user_email(telegram_id: int, new_email: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, is_banned FROM allowed_emails WHERE email = ?", (new_email,))
    email_row = cursor.fetchone()
    if not email_row or email_row[1]:
        conn.close()
        return False

    email_id = email_row[0]

    cursor.execute("""
        UPDATE users SET email_id = ?, is_authorized = 1 WHERE telegram_id = ?
    """, (email_id, telegram_id))
    conn.commit()
    conn.close()
    return True
    
@log_sync_call
def db_is_admin(telegram_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM admins WHERE telegram_id = ?", (telegram_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] > 0

@log_sync_call
def db_add_admin(telegram_id: int, is_top_level: bool = False):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO admins (telegram_id, is_top_level) VALUES (?, ?)", (telegram_id, int(is_top_level)))
    conn.commit()
    conn.close()

@log_sync_call
def db_remove_admin(telegram_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM admins WHERE telegram_id = ?", (telegram_id,))
    conn.commit()
    conn.close()

@log_sync_call
def db_list_admins():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admins")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

