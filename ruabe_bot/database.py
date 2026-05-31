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


def has_pending_application(user_id):
    """Проверяет, есть ли у пользователя активная заявка на рассмотрении."""
    app = get_application_from_db(user_id)
    return bool(app and app["status"] == "pending")
