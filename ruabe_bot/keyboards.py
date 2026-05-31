from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .faq import FAQ_ITEMS
from .questionnaire import QUESTIONNAIRE
from .utils import user_profile_url

# ============================================================
# Здесь находятся все inline-кнопки бота.
# ============================================================

def main_menu():
    """Главное меню бота."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 Правила", callback_data="rules")],
        [InlineKeyboardButton("❓ FAQ", callback_data="faq")],
        [InlineKeyboardButton("🛡️ Безопасность", callback_data="safety")],
        [InlineKeyboardButton("📝 Подать заявку", callback_data="apply")],
    ])


def back_button():
    """Обычная кнопка назад в главное меню."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])


def faq_menu_keyboard():
    """Список FAQ-вопросов в виде кнопок."""
    keyboard = []

    for item in FAQ_ITEMS:
        keyboard.append([
            InlineKeyboardButton(
                item["button"],
                callback_data=f"faq_item:{item['id']}"
            )
        ])

    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)


def faq_answer_keyboard():
    """Кнопка назад из FAQ-ответа к списку FAQ-вопросов."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад", callback_data="faq_back")]
    ])


def question_keyboard(question_index):
    """Клавиатура для конкретного вопроса анкеты."""
    question = QUESTIONNAIRE[question_index]
    keyboard = []

    for row in question["buttons"]:
        keyboard.append([
            InlineKeyboardButton(
                answer["text"],
                callback_data=f"answer:{question_index}:{answer['id']}"
            )
            for answer in row
        ])

    if question_index == 0:
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
    else:
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="q_back")])

    return InlineKeyboardMarkup(keyboard)


def submit_application_keyboard(user_id):
    """Кнопки предпросмотра заявки перед отправкой админам."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Отправить заявку", callback_data=f"submit_application:{user_id}")],
        [InlineKeyboardButton("🔄 Заполнить заново", callback_data=f"reset_application:{user_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")],
    ])


def admin_decision_keyboard(user_id, username=None):
    """Кнопки для администраторов под заявкой."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "👤 Открыть профиль",
                url=user_profile_url(user_id, username)
            )
        ],
        [
            InlineKeyboardButton("✅ Принять", callback_data=f"accept:{user_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject:{user_id}"),
        ],
        [
            InlineKeyboardButton(
                "✉️ Отклонить с причиной",
                callback_data=f"reject_with_reason:{user_id}"
            )
        ]
    ])


def cancel_rejection_reason_keyboard(user_id):
    """Кнопка отмены написания причины отказа."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🚫 Отменить",
                callback_data=f"cancel_reject_reason:{user_id}"
            )
        ]
    ])
