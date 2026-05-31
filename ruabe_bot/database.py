import psycopg2
from psycopg2.extras import Json

from .config import DATABASE_URL

# ============================================================
# МОДУЛЬ 7. БАЗА ДАННЫХ POSTGRESQL
# Здесь бот сохраняет заявки, чтобы они не пропадали после
# сна или перезапуска Render.
# ============================================================

def db_connect():
    """Создаёт подключение к PostgreSQL."""
    return psycopg2.connect(DATABASE_URL)


def init_db():
    """Создаёт таблицу заявок, если её ещё нет, и удаляет старые заявки."""
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    user_id BIGINT PRIMARY KEY,
                    status TEXT NOT NULL,
                    application_text TEXT NOT NULL,
                    admin_messages JSONB NOT NULL DEFAULT '[]'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS application_history (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    status TEXT NOT NULL,
                    admin_id BIGINT NOT NULL,
                    admin_name TEXT NOT NULL,
                    decided_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_application_history_user_decided
                ON application_history (user_id, decided_at DESC);
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS blacklist (
                    user_id BIGINT PRIMARY KEY,
                    reason TEXT NOT NULL,
                    admin_id BIGINT NOT NULL,
                    admin_name TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)

            cur.execute("""
                DELETE FROM applications
                WHERE updated_at < NOW() - INTERVAL '3 days';
            """)


def save_application_to_db(user_id, application_text):
    """Сохраняет новую заявку или перезаписывает старую заявку пользователя."""
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO applications (
                    user_id,
                    status,
                    application_text,
                    admin_messages,
                    created_at,
                    updated_at
                )
                VALUES (%s, 'pending', %s, '[]'::jsonb, NOW(), NOW())
                ON CONFLICT (user_id)
                DO UPDATE SET
                    status = 'pending',
                    application_text = EXCLUDED.application_text,
                    admin_messages = '[]'::jsonb,
                    created_at = NOW(),
                    updated_at = NOW();
            """, (user_id, application_text))


def update_application_messages_in_db(user_id, admin_messages):
    """Сохраняет ID сообщений с заявкой у администраторов."""
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE applications
                SET admin_messages = %s, updated_at = NOW()
                WHERE user_id = %s;
            """, (Json(admin_messages), user_id))


def get_application_from_db(user_id):
    """Возвращает заявку пользователя из базы, если она не старше 3 дней."""
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT status, application_text, admin_messages
                FROM applications
                WHERE user_id = %s
                  AND updated_at >= NOW() - INTERVAL '3 days';
            """, (user_id,))

            row = cur.fetchone()

            if not row:
                return None

            status, application_text, admin_messages = row

            return {
                "status": status,
                "application_text": application_text,
                "admin_messages": admin_messages or [],
            }


def set_application_status_in_db(user_id, status):
    """Меняет статус заявки: pending, approved или rejected."""
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE applications
                SET status = %s, updated_at = NOW()
                WHERE user_id = %s;
            """, (status, user_id))


def add_application_history(user_id, status, admin_id, admin_name):
    """Сохраняет решение по заявке в историю пользователя."""
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO application_history (
                    user_id,
                    status,
                    admin_id,
                    admin_name,
                    decided_at
                )
                VALUES (%s, %s, %s, %s, NOW());
            """, (user_id, status, admin_id, admin_name))


def get_application_history(user_id, limit=5):
    """Возвращает последние решения по заявкам пользователя."""
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT status, admin_id, admin_name, decided_at
                FROM application_history
                WHERE user_id = %s
                ORDER BY decided_at DESC
                LIMIT %s;
            """, (user_id, limit))

            return [
                {
                    "status": status,
                    "admin_id": admin_id,
                    "admin_name": admin_name,
                    "decided_at": decided_at,
                }
                for status, admin_id, admin_name, decided_at in cur.fetchall()
            ]


def add_user_to_blacklist(user_id, reason, admin_id, admin_name):
    """Добавляет пользователя в чёрный список или обновляет причину."""
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO blacklist (
                    user_id,
                    reason,
                    admin_id,
                    admin_name,
                    created_at
                )
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (user_id)
                DO UPDATE SET
                    reason = EXCLUDED.reason,
                    admin_id = EXCLUDED.admin_id,
                    admin_name = EXCLUDED.admin_name,
                    created_at = NOW();
            """, (user_id, reason, admin_id, admin_name))


def remove_user_from_blacklist(user_id):
    """Удаляет пользователя из чёрного списка."""
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM blacklist
                WHERE user_id = %s;
            """, (user_id,))


def get_blacklist_entry(user_id):
    """Возвращает запись чёрного списка по пользователю."""
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT reason, admin_id, admin_name, created_at
                FROM blacklist
                WHERE user_id = %s;
            """, (user_id,))

            row = cur.fetchone()

            if not row:
                return None

            reason, admin_id, admin_name, created_at = row

            return {
                "user_id": user_id,
                "reason": reason,
                "admin_id": admin_id,
                "admin_name": admin_name,
                "created_at": created_at,
            }


def get_blacklist_entries(limit=50):
    """Возвращает список пользователей в чёрном списке."""
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT user_id, reason, admin_id, admin_name, created_at
                FROM blacklist
                ORDER BY created_at DESC
                LIMIT %s;
            """, (limit,))

            return [
                {
                    "user_id": user_id,
                    "reason": reason,
                    "admin_id": admin_id,
                    "admin_name": admin_name,
                    "created_at": created_at,
                }
                for user_id, reason, admin_id, admin_name, created_at in cur.fetchall()
            ]


def has_pending_application(user_id):
    """Проверяет, есть ли у пользователя активная заявка на рассмотрении."""
    app = get_application_from_db(user_id)
    return bool(app and app["status"] == "pending")
