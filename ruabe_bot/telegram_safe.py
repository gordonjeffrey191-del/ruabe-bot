from .config import LOG_CHAT_ID
from .state import section_messages

# ============================================================
# МОДУЛЬ 12. БЕЗОПАСНЫЕ ДЕЙСТВИЯ TELEGRAM
# Здесь функции, которые не должны ломать бота при ошибках Telegram.
# ============================================================

async def safe_callback_answer(query, text=None, show_alert=False):
    """Отвечает на нажатие кнопки. Ошибки игнорируются, чтобы бот не падал."""
    try:
        await query.answer(text=text, show_alert=show_alert)
    except Exception:
        pass


async def log_event(context, text):
    """Отправляет технический лог в лог-чат."""
    try:
        await context.bot.send_message(
            chat_id=LOG_CHAT_ID,
            text=text
        )
    except Exception:
        pass


async def delete_section_messages(context, user_id):
    """Удаляет старые сообщения разделов: правила, FAQ, безопасность."""
    message_ids = section_messages.pop(user_id, [])

    for message_id in message_ids:
        try:
            await context.bot.delete_message(
                chat_id=user_id,
                message_id=message_id
            )
        except Exception:
            pass


async def safe_delete_query_message(query):
    """Безопасно удаляет сообщение, на котором была нажата кнопка."""
    try:
        await query.delete_message()
    except Exception:
        pass
