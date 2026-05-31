from datetime import datetime, timezone

from .applications import build_application_text
from .config import ADMIN_IDS, LOG_CHAT_ID
from .questionnaire import QUESTIONNAIRE
from .cooldown import cooldown_remaining
from .database import (
    get_blacklist_entry,
    has_pending_application,
    save_application_to_db,
    update_application_messages_in_db,
)
from .keyboards import admin_decision_keyboard, back_button
from .state import application_cooldowns, user_sessions
from .telegram_safe import log_event, safe_callback_answer
from .utils import collect_applicant_extra_info, user_display_plain

# ============================================================
# МОДУЛЬ 16. ОТПРАВКА ЗАЯВКИ АДМИНАМ
# Здесь заявка сохраняется в базу и рассылается администраторам.
# ============================================================

async def submit_application(query, context, user_id):
    """Отправляет готовую заявку администраторам."""
    if query.from_user.id != user_id:
        await safe_callback_answer(query, "Это не ваша заявка.", show_alert=True)
        return

    blacklist_entry = get_blacklist_entry(user_id)

    if blacklist_entry:
        await safe_callback_answer(query)
        await query.edit_message_text(
            "❌ Вас добавили в чёрный список чата RUABE.\n\n"
            f"🗂️ Причина: {blacklist_entry['reason']}",
            reply_markup=back_button()
        )
        return

    if has_pending_application(user_id):
        await safe_callback_answer(query)
        await query.edit_message_text(
            "⏳ Ваша заявка уже находится на рассмотрении администрации.",
            reply_markup=back_button()
        )
        return

    remaining = cooldown_remaining(user_id)

    if remaining:
        minutes = max(1, int(remaining.total_seconds() // 60))

        await safe_callback_answer(query)
        await query.edit_message_text(
            f"⏳ Вы уже недавно отправляли заявку.\n\n"
            f"Повторная отправка будет доступна примерно через {minutes} мин.",
            reply_markup=back_button()
        )
        return

    session = user_sessions.get(user_id)

    if not session or len(session["answers"]) < len(QUESTIONNAIRE):
        await safe_callback_answer(query)
        await query.edit_message_text(
            "Заявка не найдена или заполнена не полностью.",
            reply_markup=back_button()
        )
        return

    await safe_callback_answer(query)

    application_cooldowns[user_id] = datetime.now(timezone.utc)

    extra_info = await collect_applicant_extra_info(context.bot, query.from_user)
    application_text = build_application_text(query.from_user, extra_info)

    save_application_to_db(user_id, application_text)

    admin_messages = []

    await context.bot.send_message(
        chat_id=LOG_CHAT_ID,
        text="📌 Заявка сохранена в лог:\n\n" + application_text,
        parse_mode="HTML"
    )

    await log_event(
        context,
        "🟩 Пользователь отправил заявку\n\n"
        f"{user_display_plain(query.from_user)}"
    )

    for admin_id in ADMIN_IDS:
        try:
            msg = await context.bot.send_message(
                chat_id=admin_id,
                text=application_text,
                reply_markup=admin_decision_keyboard(user_id, query.from_user.username),
                parse_mode="HTML"
            )

            admin_messages.append({
                "chat_id": admin_id,
                "message_id": msg.message_id,
            })
        except Exception as error:
            await log_event(
                context,
                "⚠️ Не удалось отправить заявку администратору\n\n"
                f"Админ ID: {admin_id}\n"
                f"Пользователь ID: {user_id}\n"
                f"Ошибка: {error}"
            )

    update_application_messages_in_db(user_id, admin_messages)

    await query.edit_message_text(
        "✅ Спасибо! Заявка отправлена администрации.",
        reply_markup=back_button()
    )
