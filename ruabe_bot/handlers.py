from telegram import Update
from telegram.ext import ContextTypes

from .config import ADMIN_IDS
from .rules import RULES_TEXT, SAFETY_TEXT
from .decisions import (
    cancel_rejection_with_reason,
    process_admin_decision,
    start_rejection_with_reason,
)
from .menus import (
    back_to_faq_menu,
    send_faq_with_back,
    send_main_menu,
    send_section_with_back,
    show_faq_answer,
)
from .questionnaire_flow import handle_answer, questionnaire_back, reset_application, start_application
from .submit import submit_application
from .telegram_safe import delete_section_messages, safe_callback_answer, safe_delete_query_message

# ============================================================
# Сюда попадают все нажатия inline-кнопок.
# ============================================================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    if data == "back":
        await safe_callback_answer(query)
        await delete_section_messages(context, user_id)
        await safe_delete_query_message(query)
        await send_main_menu(context, user_id)

    elif data == "q_back":
        await questionnaire_back(query, context)

    elif data == "rules":
        await safe_callback_answer(query)
        await send_section_with_back(query, context, RULES_TEXT)

    elif data == "faq":
        await safe_callback_answer(query)
        await send_faq_with_back(query, context)

    elif data.startswith("faq_item:"):
        faq_id = data.split(":", 1)[1]
        await show_faq_answer(query, context, faq_id)

    elif data == "faq_back":
        await back_to_faq_menu(query, context)

    elif data == "safety":
        await safe_callback_answer(query)
        await send_section_with_back(query, context, SAFETY_TEXT)

    elif data == "apply":
        await safe_callback_answer(query)
        await start_application(query, context)

    elif data.startswith("answer:"):
        await handle_answer(query, context)

    elif data.startswith("reset_application:"):
        target_user_id = int(data.split(":")[1])
        await reset_application(query, context, target_user_id)

    elif data.startswith("submit_application:"):
        target_user_id = int(data.split(":")[1])
        await submit_application(query, context, target_user_id)

    elif data.startswith("accept:"):
        if query.from_user.id not in ADMIN_IDS:
            await safe_callback_answer(query, "У вас нет прав для этого действия.", show_alert=True)
            return

        target_user_id = int(data.split(":")[1])
        await process_admin_decision(query, context, target_user_id, "approve")

    elif data.startswith("reject_with_reason:"):
        if query.from_user.id not in ADMIN_IDS:
            await safe_callback_answer(query, "У вас нет прав для этого действия.", show_alert=True)
            return

        target_user_id = int(data.split(":")[1])
        await start_rejection_with_reason(query, context, target_user_id)

    elif data.startswith("cancel_reject_reason:"):
        if query.from_user.id not in ADMIN_IDS:
            await safe_callback_answer(query, "У вас нет прав для этого действия.", show_alert=True)
            return

        target_user_id = int(data.split(":")[1])
        await cancel_rejection_with_reason(query, context, target_user_id)

    elif data.startswith("reject:"):
        if query.from_user.id not in ADMIN_IDS:
            await safe_callback_answer(query, "У вас нет прав для этого действия.", show_alert=True)
            return

        target_user_id = int(data.split(":")[1])
        await process_admin_decision(query, context, target_user_id, "reject")

    else:
        await safe_callback_answer(query, "Неизвестное действие.", show_alert=True)

