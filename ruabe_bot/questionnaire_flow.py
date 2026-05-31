from datetime import datetime, timezone

from .applications import build_preview_text
from .questionnaire import QUESTIONNAIRE
from .cooldown import check_can_apply
from .keyboards import back_button, question_keyboard, submit_application_keyboard
from .menus import send_main_menu
from .sessions import (
    add_history_from_current_answers,
    get_or_create_session,
    start_new_session,
)
from .state import user_sessions
from .telegram_safe import delete_section_messages, log_event, safe_callback_answer, safe_delete_query_message
from .utils import find_answer, user_display_plain

# ============================================================
# МОДУЛЬ 15. ПРОХОЖДЕНИЕ АНКЕТЫ
# Здесь пользователь отвечает на вопросы анкеты.
# ============================================================

async def send_question(query, context, user_id):
    """Показывает текущий вопрос анкеты."""
    session = get_or_create_session(user_id)
    question_index = session["current_step"]
    question = QUESTIONNAIRE[question_index]

    await query.edit_message_text(
        question["question"],
        reply_markup=question_keyboard(question_index)
    )


async def start_application(query, context):
    """Запускает анкету пользователя."""
    user_id = query.from_user.id

    can_apply = await check_can_apply(query, context)

    if not can_apply:
        return

    await delete_section_messages(context, user_id)
    start_new_session(user_id)

    await log_event(
        context,
        "🟦 Пользователь начал анкету\n\n"
        f"{user_display_plain(query.from_user)}"
    )

    await send_question(query, context, user_id)


async def handle_answer(query, context):
    """Обрабатывает выбор ответа на вопрос анкеты."""
    user_id = query.from_user.id

    data_parts = query.data.split(":", 2)
    question_index = int(data_parts[1])
    answer_id = data_parts[2]

    session = get_or_create_session(user_id)

    if question_index != session["current_step"]:
        await safe_callback_answer(query, "Эта кнопка уже неактуальна.", show_alert=True)
        return

    answer_data = find_answer(question_index, answer_id)

    if not answer_data:
        await safe_callback_answer(query, "Ответ не найден.", show_alert=True)
        return

    question = QUESTIONNAIRE[question_index]
    session["answers"][question["id"]] = answer_data

    await safe_callback_answer(query)

    if question_index + 1 < len(QUESTIONNAIRE):
        session["current_step"] += 1
        await send_question(query, context, user_id)
    else:
        await query.edit_message_text(
            build_preview_text(query.from_user),
            reply_markup=submit_application_keyboard(user_id)
        )


async def questionnaire_back(query, context):
    """Кнопка Назад внутри анкеты. Возвращает на предыдущий вопрос."""
    user_id = query.from_user.id
    session = get_or_create_session(user_id)

    current_step = session["current_step"]

    await safe_callback_answer(query)

    if current_step <= 0:
        await safe_delete_query_message(query)
        await send_main_menu(context, user_id)
        return

    previous_step = current_step - 1
    previous_question = QUESTIONNAIRE[previous_step]

    session["answers"].pop(previous_question["id"], None)
    session["current_step"] = previous_step

    await send_question(query, context, user_id)


async def reset_application(query, context, user_id):
    """Полностью сбрасывает анкету и сохраняет прошлые ⚠️/❌ ответы в историю."""
    if query.from_user.id != user_id:
        await safe_callback_answer(query, "Это не ваша заявка.", show_alert=True)
        return

    await safe_callback_answer(query)

    add_history_from_current_answers(user_id)

    previous_session = get_or_create_session(user_id)
    previous_session["resets"] += 1

    resets = previous_session["resets"]
    history = previous_session["history_risky"]

    user_sessions[user_id] = {
        "current_step": 0,
        "answers": {},
        "history_risky": history,
        "resets": resets,
        "started_at": datetime.now(timezone.utc),
    }

    await log_event(
        context,
        "🟨 Пользователь сбросил анкету\n\n"
        f"{user_display_plain(query.from_user)}\n"
        f"Количество сбросов: {resets}"
    )

    await send_question(query, context, user_id)
