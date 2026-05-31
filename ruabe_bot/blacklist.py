import asyncio
import html
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import ContextTypes

from .config import ADMIN_IDS
from .database import (
    add_application_history,
    add_user_to_blacklist,
    get_application_from_db,
    get_blacklist_entries,
    get_blacklist_entry,
    remove_user_from_blacklist,
    set_application_status_in_db,
)
from .decisions import handle_admin_rejection_reason, update_admin_application_messages
from .keyboards import (
    blacklist_entry_keyboard,
    blacklist_menu_keyboard,
    cancel_blacklist_reason_keyboard,
)
from .state import admin_blacklist_drafts, application_locks
from .telegram_safe import log_event, safe_callback_answer


async def start_blacklist_reason(query, context, user_id):
    """Запускает режим написания причины добавления в чёрный список."""
    app_data = get_application_from_db(user_id)

    if not app_data:
        await safe_callback_answer(
            query,
            "Эта заявка устарела или не найдена.",
            show_alert=True
        )
        return

    if app_data["status"] != "pending":
        await safe_callback_answer(
            query,
            "Эта заявка уже была обработана.",
            show_alert=True
        )
        return

    await safe_callback_answer(query)

    prompt_message = await context.bot.send_message(
        chat_id=query.from_user.id,
        text=(
            "🚫 Напишите причину добавления пользователя в чёрный список.\n\n"
            f"Пользователь ID: {user_id}\n\n"
            "Следующее ваше текстовое сообщение будет сохранено как причина "
            "и отправлено пользователю.\n\n"
            "Ограничение: до 1000 символов."
        ),
        reply_markup=cancel_blacklist_reason_keyboard(user_id)
    )

    admin_blacklist_drafts[query.from_user.id] = {
        "user_id": user_id,
        "started_at": datetime.now(timezone.utc),
        "prompt_message_id": prompt_message.message_id,
    }


async def cancel_blacklist_reason(query, context, user_id):
    """Отменяет режим добавления пользователя в чёрный список."""
    draft = admin_blacklist_drafts.get(query.from_user.id)

    if not draft or draft["user_id"] != user_id:
        await safe_callback_answer(
            query,
            "Активное добавление в чёрный список не найдено.",
            show_alert=True
        )
        return

    admin_blacklist_drafts.pop(query.from_user.id, None)

    await safe_callback_answer(query)

    await query.edit_message_text(
        "🚫 Добавление в чёрный список отменено."
    )


async def handle_admin_blacklist_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Принимает причину добавления пользователя в чёрный список."""
    admin = update.effective_user
    admin_id = admin.id

    if admin_id not in ADMIN_IDS:
        return False

    draft = admin_blacklist_drafts.get(admin_id)

    if not draft:
        return False

    if update.effective_chat.type != "private":
        return True

    reason_text = update.message.text.strip()

    if not reason_text:
        await update.message.reply_text("Причина не может быть пустой.")
        return True

    if len(reason_text) > 1000:
        await update.message.reply_text(
            "Причина слишком длинная. Сократите текст до 1000 символов."
        )
        return True

    user_id = draft["user_id"]
    lock = application_locks.setdefault(user_id, asyncio.Lock())

    async with lock:
        app_data = get_application_from_db(user_id)

        if not app_data:
            admin_blacklist_drafts.pop(admin_id, None)
            await update.message.reply_text("Эта заявка устарела или не найдена.")
            return True

        if app_data["status"] != "pending":
            admin_blacklist_drafts.pop(admin_id, None)
            await update.message.reply_text(
                "Эта заявка уже была обработана другим администратором."
            )
            return True

        add_user_to_blacklist(user_id, reason_text, admin_id, admin.full_name)

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "Вас добавили в чёрный список чата RUABE.\n\n"
                    f"Причина: {reason_text}"
                )
            )
        except Exception as error:
            await log_event(
                context,
                "⚠️ Не удалось отправить пользователю сообщение о чёрном списке\n\n"
                f"Пользователь ID: {user_id}\n"
                f"Админ: {admin.full_name} ({admin_id})\n"
                f"Ошибка: {error}"
            )

        set_application_status_in_db(user_id, "rejected")
        add_application_history(
            user_id,
            "blacklisted",
            admin_id,
            admin.full_name
        )

        prompt_message_id = draft.get("prompt_message_id")

        if prompt_message_id:
            try:
                await context.bot.delete_message(
                    chat_id=admin_id,
                    message_id=prompt_message_id
                )
            except Exception:
                pass

        admin_blacklist_drafts.pop(admin_id, None)

        decision_text = (
            "🚫 Пользователь добавлен в чёрный список.\n"
            f"Решение принял: {admin.full_name} ({admin_id})."
        )

        await update_admin_application_messages(context, user_id, decision_text)

        await log_event(
            context,
            "🚫 Администратор добавил пользователя в чёрный список\n\n"
            f"Админ: {admin.full_name} ({admin_id})\n"
            f"Пользователь ID: {user_id}\n\n"
            f"Причина:\n{reason_text}"
        )

        await update.message.reply_text(
            "✅ Пользователь добавлен в чёрный список."
        )

    return True


async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Роутер текстовых сообщений администраторов."""
    handled = await handle_admin_blacklist_reason(update, context)

    if handled:
        return

    await handle_admin_rejection_reason(update, context)


async def show_blacklist(query, context):
    """Показывает администраторам список чёрного списка."""
    entries = get_blacklist_entries()

    if entries:
        text = "🚫 Чёрный список\n\n"

        for entry in entries:
            created_at = entry["created_at"].strftime("%d.%m.%Y")
            reason = html.escape(entry["reason"])
            admin_name = html.escape(entry["admin_name"])

            text += (
                f"• <code>{entry['user_id']}</code> — {created_at}\n"
                f"  Причина: {reason}\n"
                f"  Админ: {admin_name}\n\n"
            )

        text += "Выберите пользователя для управления:"
    else:
        text = "🚫 Чёрный список\n\nСписок пуст."

    await safe_callback_answer(query)

    await query.edit_message_text(
        text=text,
        reply_markup=blacklist_menu_keyboard(entries),
        parse_mode="HTML"
    )


async def show_blacklist_entry(query, context, user_id):
    """Показывает карточку пользователя в чёрном списке."""
    entry = get_blacklist_entry(user_id)

    if not entry:
        await safe_callback_answer(
            query,
            "Пользователь не найден в чёрном списке.",
            show_alert=True
        )
        await show_blacklist(query, context)
        return

    created_at = entry["created_at"].strftime("%d.%m.%Y")

    text = (
        "🚫 Пользователь в чёрном списке\n\n"
        f"ID: <code>{user_id}</code>\n"
        f"Дата: {created_at}\n"
        f"Админ: {html.escape(entry['admin_name'])} ({entry['admin_id']})\n\n"
        "Причина:\n"
        f"{html.escape(entry['reason'])}"
    )

    await safe_callback_answer(query)

    await query.edit_message_text(
        text=text,
        reply_markup=blacklist_entry_keyboard(user_id),
        parse_mode="HTML"
    )


async def remove_blacklist_entry(query, context, user_id):
    """Удаляет пользователя из чёрного списка."""
    remove_user_from_blacklist(user_id)

    await safe_callback_answer(query, "Пользователь убран из чёрного списка.")

    await log_event(
        context,
        "✅ Администратор убрал пользователя из чёрного списка\n\n"
        f"Админ: {query.from_user.full_name} ({query.from_user.id})\n"
        f"Пользователь ID: {user_id}"
    )

    await show_blacklist(query, context)
