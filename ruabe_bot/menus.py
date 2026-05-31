from telegram import Update
from telegram.ext import ContextTypes

from .rules import RULES_TEXT, SAFETY_TEXT
from .keyboards import back_button, faq_answer_keyboard, faq_menu_keyboard, main_menu
from .telegram_safe import delete_section_messages, safe_callback_answer, safe_delete_query_message
from .utils import find_faq_item, main_menu_text, split_text

# ============================================================
# МОДУЛЬ 13. ГЛАВНОЕ МЕНЮ И ИНФОРМАЦИОННЫЕ РАЗДЕЛЫ
# Здесь логика /start, правил, FAQ и безопасности.
# ============================================================

async def send_main_menu(context, user_id):
    """Отправляет главное меню пользователю."""
    await context.bot.send_message(
        chat_id=user_id,
        text=main_menu_text(),
        reply_markup=main_menu(user_id)
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start. Работает только в личке бота, в группах игнорируется."""
    if update.effective_chat.type != "private":
        return

    user_id = update.effective_user.id
    await delete_section_messages(context, user_id)

    await update.message.reply_text(
        main_menu_text(),
        reply_markup=main_menu(user_id)
    )


async def send_section_with_back(query, context, section_text):
    """Отправляет длинный информационный раздел и кнопку Назад."""
    user_id = query.from_user.id

    await delete_section_messages(context, user_id)
    await safe_delete_query_message(query)

    sent_ids = []
    parts = split_text(section_text)

    for index, part in enumerate(parts):
        is_last_part = index == len(parts) - 1

        msg = await context.bot.send_message(
            chat_id=user_id,
            text=part,
            reply_markup=back_button() if is_last_part else None
        )

        sent_ids.append(msg.message_id)

    section_messages[user_id] = sent_ids


async def send_faq_with_back(query, context):
    """Открывает FAQ как одно сообщение со списком вопросов."""
    user_id = query.from_user.id

    await delete_section_messages(context, user_id)
    await safe_delete_query_message(query)

    msg = await context.bot.send_message(
        chat_id=user_id,
        text="❓ FAQ\n\nВыберите интересующий вопрос:",
        reply_markup=faq_menu_keyboard()
    )

    section_messages[user_id] = [msg.message_id]


async def show_faq_answer(query, context, faq_id):
    """Заменяет список FAQ на ответ выбранного вопроса."""
    item = find_faq_item(faq_id)

    if not item:
        await safe_callback_answer(query, "Вопрос не найден.", show_alert=True)
        return

    await safe_callback_answer(query)

    await query.edit_message_text(
        text=(
            f"❓ {item['question']}\n\n"
            f"💬 {item['answer']}"
        ),
        reply_markup=faq_answer_keyboard()
    )


async def back_to_faq_menu(query, context):
    """Возвращает из FAQ-ответа к списку FAQ-вопросов."""
    await safe_callback_answer(query)

    await query.edit_message_text(
        text="❓ FAQ\n\nВыберите интересующий вопрос:",
        reply_markup=faq_menu_keyboard()
    )
