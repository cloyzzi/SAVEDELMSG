import aiosqlite
from datetime import datetime, timedelta
from typing import Optional

DB_PATH = "business_bot.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                business_connection_id TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER,
                message_id INTEGER,
                chat_id INTEGER,
                from_user_id INTEGER,
                from_username TEXT,
                from_first_name TEXT,
                text TEXT,
                caption TEXT,
                media_type TEXT,
                media_path TEXT,
                is_deleted INTEGER DEFAULT 0,
                is_protected INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(user_id)
            )
        """)
        
        # Таблица подписок
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER PRIMARY KEY,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Таблица админов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица платежей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                months INTEGER,
                payment_id TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        await db.commit()


async def add_user(user_id: int, username: str, first_name: str, connection_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO users (user_id, username, first_name, business_connection_id, is_active)
            VALUES (?, ?, ?, ?, 1)
        """, (user_id, username, first_name, connection_id))
        await db.commit()


async def get_user_by_connection(connection_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE business_connection_id = ?", (connection_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def save_message(
    owner_id: int, message_id: int, chat_id: int, from_user_id: int,
    from_username: str, from_first_name: str, text: str, caption: str,
    media_type: str, media_path: str, is_protected: bool
):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO messages (
                owner_id, message_id, chat_id, from_user_id, from_username,
                from_first_name, text, caption, media_type, media_path, is_protected
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            owner_id, message_id, chat_id, from_user_id, from_username,
            from_first_name, text, caption, media_type, media_path, 1 if is_protected else 0
        ))
        await db.commit()


async def mark_deleted(owner_id: int, chat_id: int, message_ids: list):
    async with aiosqlite.connect(DB_PATH) as db:
        placeholders = ",".join("?" * len(message_ids))
        await db.execute(f"""
            UPDATE messages SET is_deleted = 1
            WHERE owner_id = ? AND chat_id = ? AND message_id IN ({placeholders})
        """, [owner_id, chat_id] + message_ids)
        await db.commit()


async def get_deleted_messages(owner_id: int, chat_id: int, message_ids: list):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        placeholders = ",".join("?" * len(message_ids))
        async with db.execute(f"""
            SELECT * FROM messages
            WHERE owner_id = ? AND chat_id = ? AND message_id IN ({placeholders})
        """, [owner_id, chat_id] + message_ids) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_user_stats(owner_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM messages WHERE owner_id = ?", (owner_id,)) as c:
            total = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM messages WHERE owner_id = ? AND is_deleted = 1", (owner_id,)) as c:
            deleted = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM messages WHERE owner_id = ? AND media_type IS NOT NULL", (owner_id,)) as c:
            media = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM messages WHERE owner_id = ? AND is_protected = 1", (owner_id,)) as c:
            protected = (await c.fetchone())[0]
        return {"total": total, "deleted": deleted, "media": media, "protected": protected}


# ==================== ПОДПИСКИ ====================

async def get_subscription(user_id: int):
    """Получить подписку пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM subscriptions WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def check_subscription(user_id: int) -> bool:
    """Проверить активна ли подписка"""
    sub = await get_subscription(user_id)
    if not sub:
        return False
    
    expires_at = datetime.fromisoformat(sub['expires_at'])
    return expires_at > datetime.now()


async def add_subscription(user_id: int, months: int):
    """Добавить/продлить подписку"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем текущую подписку
        sub = await get_subscription(user_id)
        
        if sub and datetime.fromisoformat(sub['expires_at']) > datetime.now():
            # Продлеваем от текущей даты истечения
            expires_at = datetime.fromisoformat(sub['expires_at']) + timedelta(days=30 * months)
        else:
            # Новая подписка от текущего момента
            expires_at = datetime.now() + timedelta(days=30 * months)
        
        await db.execute("""
            INSERT OR REPLACE INTO subscriptions (user_id, expires_at, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (user_id, expires_at))
        await db.commit()
        
        return expires_at


async def remove_subscription(user_id: int):
    """Удалить подписку"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
        await db.commit()


# ==================== АДМИНЫ ====================

async def is_admin(user_id: int) -> bool:
    """Проверить является ли пользователь админом"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id FROM admins WHERE user_id = ?", (user_id,)
        ) as cursor:
            return await cursor.fetchone() is not None


async def add_admin(user_id: int):
    """Добавить админа"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,)
        )
        await db.commit()


async def remove_admin(user_id: int):
    """Удалить админа"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        await db.commit()


async def get_all_admins():
    """Получить всех админов"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM admins") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# ==================== ПЛАТЕЖИ ====================

async def save_payment(user_id: int, amount: int, months: int, payment_id: str, status: str):
    """Сохранить платеж"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO payments (user_id, amount, months, payment_id, status)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, amount, months, payment_id, status))
        await db.commit()


# ==================== СТАТИСТИКА ====================

async def get_total_stats():
    """Общая статистика для админов"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as c:
            total_users = (await c.fetchone())[0]
        
        async with db.execute(
            "SELECT COUNT(*) FROM subscriptions WHERE expires_at > CURRENT_TIMESTAMP"
        ) as c:
            active_subs = (await c.fetchone())[0]
        
        async with db.execute("SELECT COUNT(*) FROM messages") as c:
            total_messages = (await c.fetchone())[0]
        
        async with db.execute(
            "SELECT SUM(amount) FROM payments WHERE status = 'paid'"
        ) as c:
            total_revenue = (await c.fetchone())[0] or 0
        
        return {
            "users": total_users,
            "active_subs": active_subs,
            "messages": total_messages,
            "revenue": total_revenue
        }


async def get_all_users():
    """Получить всех пользователей"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users ORDER BY created_at DESC") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]