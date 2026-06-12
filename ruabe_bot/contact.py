import html
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import ContextTypes

from .config import ADMIN_IDS
from .database import is_contact_admin_enabled, set_contact_admin_enabled
from .keyboards import (
    cancel_contact_admin_keyboard,
    contact_admin_settings_keyboard,
    main_menu,
)
from .state import user_contact_drafts
from .telegram_safe import safe_callback_answer
from .utils import user_display_html


async def start_contact_admin(query, context):
    """Запускает режим отправки сообщения администрации."""
    user_id = query.from_user.id
    enabled = is_contact_admin_enabled()

    if user_id in ADMIN_IDS:
        status_text = "включена" if enabled else "отключена"

        await safe_callback_answer(query)

        await query.edit_message_text(
            "📩 Связь с администрацией\n\n"
            f"Статус функции: {status_text}.",
            reply_markup=contact_admin_settings_keyboard(enabled)
        )
        return

    if not enabled:
        await safe_callback_answer(query)

        await query.edit_message_text(
            "📩 Связь с администрацией\n\n"
            "Сейчас эта функция временно недоступна.",
            reply_markup=main_menu(user_id)
        )
        return

    user_contact_drafts[user_id] = {
        "started_at": datetime.now(timezone.utc),
    }

    await safe_callback_answer(query)

    await query.edit_message_text(
        "📩 Связь с администрацией\n\n"
        "Напишите сообщение следующим текстовым сообщением.",
        reply_markup=cancel_contact_admin_keyboard()
    )


async def toggle_contact_admin(query, context):
    """Переключает доступность связи с администрацией."""
    if query.from_user.id not in ADMIN_IDS:
        await safe_callback_answer(query, "У вас нет прав для этого действия.", show_alert=True)
        return

    enabled = is_contact_admin_enabled()
    new_enabled = not enabled

    set_contact_admin_enabled(new_enabled)

    status_text = "включена" if new_enabled else "отключена"

    await safe_callback_answer(query, f"Связь с администрацией {status_text}.")

    await query.edit_message_text(
        "📩 Связь с администрацией\n\n"
        f"Статус функции: {status_text}.",
        reply_markup=contact_admin_settings_keyboard(new_enabled)
    )


async def cancel_contact_admin(query, context):
    """Отменяет режим отправки сообщения администрации."""
    user_id = query.from_user.id
    user_contact_drafts.pop(user_id, None)

    await safe_callback_answer(query)

    await query.edit_message_text(
        "Отправка сообщения администрации отменена.",
        reply_markup=main_menu(user_id)
    )


async def handle_user_contact_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пересылает текстовое сообщение пользователя всем администраторам."""
    if update.effective_chat.type != "private":
        return False

    user = update.effective_user

    if user.id not in user_contact_drafts:
        return False

    text = update.message.text.strip()

    if not text:
        await update.message.reply_text(
            "Сообщение не может быть пустым.",
            reply_markup=cancel_contact_admin_keyboard()
        )
        return True

    user_contact_drafts.pop(user.id, None)

    admin_text = (
        "📩 Сообщение администрации\n\n"
        f"{user_display_html(user)}\n\n"
        "Текст сообщения:\n"
        f"{html.escape(text)}"
    )

    delivered = 0

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                parse_mode="HTML"
            )
            delivered += 1
        except Exception:
            pass

    if delivered:
        await update.message.reply_text(
            "✅ Сообщение отправлено администрации.",
            reply_markup=main_menu(user.id)
        )
    else:
        await update.message.reply_text(
            "⚠️ Не удалось отправить сообщение администрации. Попробуйте позже.",
            reply_markup=main_menu(user.id)
        )

    return True
