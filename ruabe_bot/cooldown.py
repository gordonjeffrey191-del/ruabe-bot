from datetime import datetime, timedelta, timezone

from .config import COOLDOWN_MINUTES
from .database import get_blacklist_entry, has_pending_application
from .keyboards import back_button
from .state import application_cooldowns

# ============================================================
# МОДУЛЬ 14. ПРОВЕРКА COOLDOWN И ПОВТОРНЫХ ЗАЯВОК
# Здесь бот защищается от спама заявками.
# ============================================================

def cooldown_remaining(user_id):
    """Проверяет, сколько времени осталось до повторной отправки заявки."""
    last_submit = application_cooldowns.get(user_id)

    if not last_submit:
        return None

    cooldown_end = last_submit + timedelta(minutes=COOLDOWN_MINUTES)
    now = datetime.now(timezone.utc)

    if now >= cooldown_end:
        return None

    return cooldown_end - now


async def check_can_apply(query, context):
    """Проверяет, может ли пользователь начать новую заявку."""
    user_id = query.from_user.id

    blacklist_entry = get_blacklist_entry(user_id)

    if blacklist_entry:
        await query.edit_message_text(
            "❌ Вас добавили в чёрный список чата RUABE.\n\n"
            f"🗂️ Причина: {blacklist_entry['reason']}",
            reply_markup=back_button()
        )
        return False

    if has_pending_application(user_id):
        await query.edit_message_text(
            "⏳ Ваша заявка уже находится на рассмотрении администрации.\n\n"
            "Пожалуйста, дождитесь решения.",
            reply_markup=back_button()
        )
        return False

    remaining = cooldown_remaining(user_id)

    if remaining:
        minutes = max(1, int(remaining.total_seconds() // 60))

        await query.edit_message_text(
            f"⏳ Вы уже недавно отправляли заявку.\n\n"
            f"Повторная отправка будет доступна примерно через {minutes} мин.",
            reply_markup=back_button()
        )
        return False

    return True
