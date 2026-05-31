import asyncio
import html
from datetime import datetime, timedelta, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from .config import ADMIN_IDS, CHAT_LINK, MAIN_CHAT_ID
from .database import (
    add_application_history,
    get_application_from_db,
    set_application_status_in_db,
)
from .keyboards import approval_confirmation_keyboard, cancel_rejection_reason_keyboard
from .state import admin_rejection_drafts, application_locks
from .telegram_safe import log_event, safe_callback_answer

# ============================================================
# Здесь администраторы принимают или отклоняют заявки.
# ============================================================

APPROVAL_INFO_TEXT = """🎉 Ваша заявка была одобрена.

📌 Важная информация о чате RUABE

1. В чате могут находиться только лица старше 16 лет.
2. RUABE не является площадкой для поиска сексуальных отношений. Чат предназначен для общения, однако знакомства и отношения между участниками могут возникать естественным образом.
3. RUABE не является NSFW-сообществом. Публикация порнографического контента в чате запрещена.
4. RUABE ориентирован на активное общение. Постоянное нахождение в чате исключительно в роли наблюдателя может привести к удалению из сообщества.
5. Если удаление произошло по причине неактивности или недопонимания, пользователь может повторно подать заявку. После двух удалений за неактивность пользователь заносится в чёрный список сообщества и больше не сможет подать заявку.
6. Каждый участник самостоятельно несёт ответственность за сохранение собственной анонимности и за информацию, которую раскрывает о себе.
7. Наличие аватарки является обязательным условием нахождения в сообществе. Аккаунты без аватарки могут быть отклонены на этапе рассмотрения заявки или удалены из чата.

Подтверждаете ли вы, что ознакомились с правилами и условиями вступления в чат RUABE и согласны их соблюдать?"""


async def approve_user(context, user_id):
    """Отправляет пользователю условия вступления перед выдачей ссылки."""
    await context.bot.send_message(
        chat_id=user_id,
        text=APPROVAL_INFO_TEXT,
        reply_markup=approval_confirmation_keyboard(user_id)
    )


async def send_chat_invite(context, user_id):
    """Создаёт одноразовую ссылку и отправляет её пользователю."""
    if MAIN_CHAT_ID:
        invite = await context.bot.create_chat_invite_link(
            chat_id=MAIN_CHAT_ID,
            name=f"Invite for {user_id}",
            member_limit=1,
            expire_date=datetime.now(timezone.utc) + timedelta(hours=24)
        )

        invite_link = invite.invite_link

        await log_event(
            context,
            "🔗 Создана одноразовая invite-ссылка\n\n"
            f"Пользователь ID: {user_id}\n"
            "Лимит: 1 вход\n"
            "Срок: 24 часа"
        )
    else:
        invite_link = CHAT_LINK

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚪 Войти в чат", url=invite_link)]
    ])

    await context.bot.send_message(
        chat_id=user_id,
        text=(
            "✅ Спасибо за подтверждение.\n\n"
            "Нажмите кнопку ниже, чтобы войти в чат."
        ),
        reply_markup=keyboard
    )


async def confirm_approval(query, context, user_id):
    """Выдаёт ссылку только после подтверждения условий вступления."""
    if query.from_user.id != user_id:
        await safe_callback_answer(query, "Это подтверждение не для вас.", show_alert=True)
        return

    app_data = get_application_from_db(user_id)

    if not app_data or app_data["status"] != "approved":
        await safe_callback_answer(
            query,
            "Одобренная заявка не найдена или устарела.",
            show_alert=True
        )
        return

    await safe_callback_answer(query)

    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass

    await send_chat_invite(context, user_id)


async def reject_user(context, user_id):
    """Отправляет пользователю стандартное сообщение об отказе."""
    await context.bot.send_message(
        chat_id=user_id,
        text="Ваша заявка была отклонена."
    )


async def reject_user_with_reason(context, user_id, reason_text):
    """Отправляет пользователю отказ с индивидуальным комментарием администратора."""
    await context.bot.send_message(
        chat_id=user_id,
        text=(
            "Спасибо за заявку. Сейчас мы не можем одобрить вступление в чат.\n\n"
            "Комментарий администрации:\n"
            f"{reason_text}"
        )
    )


async def update_admin_application_messages(context, user_id, decision_text):
    """Обновляет сообщения с заявкой у всех администраторов и убирает кнопки."""
    app_data = get_application_from_db(user_id)

    if app_data:
        base_text = app_data["application_text"]
        admin_messages = app_data["admin_messages"]
    else:
        base_text = "📝 Заявка"
        admin_messages = []

    final_text = (
        f"{base_text}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{html.escape(decision_text)}\n"
        "Подробности смотрите в лог-чате."
    )

    for message_info in admin_messages:
        try:
            await context.bot.edit_message_text(
                chat_id=message_info["chat_id"],
                message_id=message_info["message_id"],
                text=final_text,
                reply_markup=None,
                parse_mode="HTML"
            )
        except Exception:
            try:
                await context.bot.edit_message_reply_markup(
                    chat_id=message_info["chat_id"],
                    message_id=message_info["message_id"],
                    reply_markup=None
                )
            except Exception:
                pass


async def start_rejection_with_reason(query, context, user_id):
    """
    Запускает режим написания причины отказа.
    Заявка пока остаётся pending.
    """
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
            "✉️ Напишите причину отказа для заявителя.\n\n"
            f"Пользователь ID: {user_id}\n\n"
            "Следующее ваше текстовое сообщение будет отправлено заявителю как комментарий администрации.\n\n"
            "Ограничение: до 1000 символов."
        ),
        reply_markup=cancel_rejection_reason_keyboard(user_id)
    )

    admin_rejection_drafts[query.from_user.id] = {
        "user_id": user_id,
        "started_at": datetime.now(timezone.utc),
        "prompt_message_id": prompt_message.message_id,
    }


async def cancel_rejection_with_reason(query, context, user_id):
    """Отменяет режим написания причины отказа."""
    draft = admin_rejection_drafts.get(query.from_user.id)

    if not draft or draft["user_id"] != user_id:
        await safe_callback_answer(
            query,
            "Активное написание причины отказа не найдено.",
            show_alert=True
        )
        return

    admin_rejection_drafts.pop(query.from_user.id, None)

    await safe_callback_answer(query)

    await query.edit_message_text(
        "🚫 Отправка причины отказа отменена."
    )


async def handle_admin_rejection_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Принимает текст причины отказа от администратора.
    Работает только если админ заранее нажал "Отклонить с причиной".
    """
    admin = update.effective_user
    admin_id = admin.id

    if admin_id not in ADMIN_IDS:
        return

    draft = admin_rejection_drafts.get(admin_id)

    if not draft:
        return

    if update.effective_chat.type != "private":
        return

    reason_text = update.message.text.strip()

    if not reason_text:
        await update.message.reply_text("Причина отказа не может быть пустой.")
        return

    if len(reason_text) > 1000:
        await update.message.reply_text(
            "Причина слишком длинная. Сократите текст до 1000 символов."
        )
        return

    user_id = draft["user_id"]
    lock = application_locks.setdefault(user_id, asyncio.Lock())

    async with lock:
        app_data = get_application_from_db(user_id)

        if not app_data:
            admin_rejection_drafts.pop(admin_id, None)
            await update.message.reply_text("Эта заявка устарела или не найдена.")
            return

        if app_data["status"] != "pending":
            admin_rejection_drafts.pop(admin_id, None)
            await update.message.reply_text(
                "Эта заявка уже была обработана другим администратором."
            )
            return

        try:
            await reject_user_with_reason(context, user_id, reason_text)
        except Exception as error:
            await log_event(
                context,
                "⚠️ Не удалось отправить пользователю отказ с причиной\n\n"
                f"Пользователь ID: {user_id}\n"
                f"Админ: {admin.full_name} ({admin_id})\n"
                f"Ошибка: {error}"
            )

        set_application_status_in_db(user_id, "rejected")
        add_application_history(
            user_id,
            "rejected_with_reason",
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

        admin_rejection_drafts.pop(admin_id, None)

        decision_text = (
            "❌ Заявка отклонена с причиной.\n"
            f"Решение принял: {admin.full_name} ({admin_id})."
        )

        await update_admin_application_messages(context, user_id, decision_text)

        await log_event(
            context,
            "❌ Администратор отклонил заявку с причиной\n\n"
            f"Админ: {admin.full_name} ({admin_id})\n"
            f"Пользователь ID: {user_id}\n\n"
            f"Причина:\n{reason_text}"
        )

        await update.message.reply_text(
            "✅ Причина отправлена заявителю. Заявка отклонена."
        )


async def process_admin_decision(query, context, user_id, decision):
    """
    Обрабатывает решение администратора.
    Важная защита:
    - если два админа нажали одновременно, сработает только первый;
    - если отправка ссылки не удалась, заявка остаётся активной;
    - после решения кнопки убираются у всех админов.
    """
    lock = application_locks.setdefault(user_id, asyncio.Lock())

    async with lock:
        app_data = get_application_from_db(user_id)

        if not app_data:
            await safe_callback_answer(
                query,
                "Эта заявка устарела или не найдена.",
                show_alert=True
            )

            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass

            return

        current_status = app_data["status"]

        if current_status != "pending":
            if current_status == "approved":
                message = "Эта заявка уже была одобрена другим администратором."
            elif current_status == "rejected":
                message = "Эта заявка уже была отклонена другим администратором."
            else:
                message = "Эта заявка уже была обработана."

            await safe_callback_answer(query, message, show_alert=True)

            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass

            return

        admin_name = query.from_user.full_name
        admin_id = query.from_user.id

        if decision == "approve":
            try:
                await approve_user(context, user_id)
            except Exception as error:
                await safe_callback_answer(
                    query,
                    "Не удалось отправить ссылку пользователю. Заявка осталась активной.",
                    show_alert=True
                )

                await log_event(
                    context,
                    "⚠️ Не удалось одобрить заявку\n\n"
                    "Заявка осталась активной. Кнопки одобрения/отклонения не удалены.\n\n"
                    f"Пользователь ID: {user_id}\n"
                    f"Ошибка: {error}"
                )
                return

            await safe_callback_answer(query)

            set_application_status_in_db(user_id, "approved")
            add_application_history(
                user_id,
                "approved",
                admin_id,
                admin_name
            )

            decision_text = (
                "✅ Заявка одобрена.\n"
                f"Решение принял: {admin_name} ({admin_id})."
            )

            await update_admin_application_messages(context, user_id, decision_text)

            await log_event(
                context,
                f"✅ Администратор одобрил заявку\n\n"
                f"Админ: {admin_name} ({admin_id})\n"
                f"Пользователь ID: {user_id}"
            )

        elif decision == "reject":
            try:
                await reject_user(context, user_id)
            except Exception as error:
                await log_event(
                    context,
                    "⚠️ Не удалось отправить пользователю сообщение об отказе\n\n"
                    f"Пользователь ID: {user_id}\n"
                    f"Ошибка: {error}"
                )

            await safe_callback_answer(query)

            set_application_status_in_db(user_id, "rejected")
            add_application_history(
                user_id,
                "rejected",
                admin_id,
                admin_name
            )

            decision_text = (
                "❌ Заявка отклонена.\n"
                f"Решение принял: {admin_name} ({admin_id})."
            )

            await update_admin_application_messages(context, user_id, decision_text)

            await log_event(
                context,
                f"❌ Администратор отклонил заявку\n\n"
                f"Админ: {admin_name} ({admin_id})\n"
                f"Пользователь ID: {user_id}"
            )
