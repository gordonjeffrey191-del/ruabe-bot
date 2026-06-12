import html
from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.ext import ContextTypes

from .config import ADMIN_IDS
from .database import is_contact_admin_enabled, set_contact_admin_enabled
from .keyboards import (
    cancel_contact_admin_keyboard,
    cancel_contact_reply_keyboard,
    contact_admin_message_keyboard,
    contact_admin_settings_keyboard,
    main_menu,
)
from .state import admin_contact_reply_drafts, user_contact_cooldowns, user_contact_drafts
from .telegram_safe import safe_callback_answer
from .utils import user_display_html

CONTACT_COOLDOWN_SECONDS = 60


def contact_cooldown_remaining(user_id):
    """Возвращает остаток cooldown для связи с администрацией."""
    last_sent = user_contact_cooldowns.get(user_id)

    if not last_sent:
        return None

    cooldown_end = last_sent + timedelta(seconds=CONTACT_COOLDOWN_SECONDS)
    now = datetime.now(timezone.utc)

    if now >= cooldown_end:
        return None

    return cooldown_end - now


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

    remaining = contact_cooldown_remaining(user_id)

    if remaining:
        seconds = max(1, int(remaining.total_seconds()))

        await safe_callback_answer(query)

        await query.edit_message_text(
            "📩 Связь с администрацией\n\n"
            f"Повторное сообщение можно будет отправить через {seconds} сек.",
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


async def start_contact_reply(query, context, user_id):
    """Запускает режим ответа администратора пользователю."""
    if query.from_user.id not in ADMIN_IDS:
        await safe_callback_answer(query, "У вас нет прав для этого действия.", show_alert=True)
        return

    admin_contact_reply_drafts[query.from_user.id] = {
        "user_id": user_id,
        "started_at": datetime.now(timezone.utc),
    }

    await safe_callback_answer(query)

    await context.bot.send_message(
        chat_id=query.from_user.id,
        text=(
            "✉️ Ответ пользователю\n\n"
            f"Пользователь ID: {user_id}\n\n"
            "Следующее ваше текстовое сообщение будет отправлено пользователю."
        ),
        reply_markup=cancel_contact_reply_keyboard(user_id)
    )


async def cancel_contact_reply(query, context, user_id):
    """Отменяет режим ответа администратора пользователю."""
    draft = admin_contact_reply_drafts.get(query.from_user.id)

    if not draft or draft["user_id"] != user_id:
        await safe_callback_answer(
            query,
            "Активный ответ пользователю не найден.",
            show_alert=True
        )
        return

    admin_contact_reply_drafts.pop(query.from_user.id, None)

    await safe_callback_answer(query)

    await query.edit_message_text("🚫 Ответ пользователю отменён.")


async def handle_admin_contact_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет ответ администратора пользователю."""
    admin = update.effective_user
    admin_id = admin.id

    if admin_id not in ADMIN_IDS:
        return False

    draft = admin_contact_reply_drafts.get(admin_id)

    if not draft:
        return False

    if update.effective_chat.type != "private":
        return True

    text = update.message.text.strip()

    if not text:
        await update.message.reply_text(
            "Ответ не может быть пустым.",
            reply_markup=cancel_contact_reply_keyboard(draft["user_id"])
        )
        return True

    user_id = draft["user_id"]
    admin_contact_reply_drafts.pop(admin_id, None)

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "📩 Ответ администрации\n\n"
                f"{text}"
            )
        )
    except Exception:
        await update.message.reply_text(
            "⚠️ Не удалось отправить ответ пользователю."
        )
        return True

    await update.message.reply_text(
        "✅ Ответ отправлен пользователю."
    )
    return True


async def handle_user_contact_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пересылает текстовое сообщение пользователя всем администраторам."""
    if update.effective_chat.type != "private":
        return False

    user = update.effective_user

    if user.id not in user_contact_drafts:
        return False

    remaining = contact_cooldown_remaining(user.id)

    if remaining:
        seconds = max(1, int(remaining.total_seconds()))
        user_contact_drafts.pop(user.id, None)

        await update.message.reply_text(
            f"Повторное сообщение можно будет отправить через {seconds} сек.",
            reply_markup=main_menu(user.id)
        )
        return True

    text = update.message.text.strip()

    if not text:
        await update.message.reply_text(
            "Сообщение не может быть пустым.",
            reply_markup=cancel_contact_admin_keyboard()
        )
        return True

    user_contact_drafts.pop(user.id, None)
    user_contact_cooldowns[user.id] = datetime.now(timezone.utc)

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
                parse_mode="HTML",
                reply_markup=contact_admin_message_keyboard(user.id)
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
