from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .config import ADMIN_IDS
from .faq import FAQ_ITEMS
from .questionnaire import QUESTIONNAIRE
from .utils import user_profile_url

# ============================================================
# Здесь находятся все inline-кнопки бота.
# ============================================================

def main_menu(user_id=None):
    """Главное меню бота."""
    keyboard = [
        [InlineKeyboardButton("📜 Правила", callback_data="rules")],
        [InlineKeyboardButton("❓ FAQ", callback_data="faq")],
        [InlineKeyboardButton("🛡️ Безопасность", callback_data="safety")],
        [InlineKeyboardButton("📩 Связь с администрацией", callback_data="contact_admin")],
        [InlineKeyboardButton("📝 Подать заявку", callback_data="apply")],
    ]

    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("🚫 Чёрный список", callback_data="blacklist")])

    return InlineKeyboardMarkup(keyboard)


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


def username_required_keyboard(user_id):
    """Кнопки экрана, если для отправки заявки нужен username."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Проверить и отправить заявку", callback_data=f"submit_application:{user_id}")],
        [InlineKeyboardButton("🔄 Заполнить заново", callback_data=f"reset_application:{user_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")],
    ])


def admin_decision_keyboard(user_id, username=None):
    """Кнопки для администраторов под заявкой."""
    keyboard = []

    if username:
        keyboard.append([
            InlineKeyboardButton(
                "👤 Открыть профиль",
                url=user_profile_url(user_id, username)
            )
        ])

    keyboard.extend([
        [
            InlineKeyboardButton("✅ Принять", callback_data=f"accept:{user_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject:{user_id}"),
        ],
        [
            InlineKeyboardButton(
                "✉️ Отклонить с причиной",
                callback_data=f"reject_with_reason:{user_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "🚫 Добавить в чёрный список",
                callback_data=f"blacklist_start:{user_id}"
            )
        ]
    ])

    return InlineKeyboardMarkup(keyboard)


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


def approval_confirmation_keyboard(user_id):
    """Кнопка подтверждения правил перед выдачей ссылки."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Подтверждаю",
                callback_data=f"confirm_approval:{user_id}"
            )
        ]
    ])


def cancel_blacklist_reason_keyboard(user_id):
    """Кнопка отмены добавления пользователя в чёрный список."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🚫 Отменить",
                callback_data=f"blacklist_cancel:{user_id}"
            )
        ]
    ])


def blacklist_menu_keyboard(entries):
    """Клавиатура списка чёрного списка."""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить по ID", callback_data="blacklist_manual_start")]
    ]

    for entry in entries:
        keyboard.append([
            InlineKeyboardButton(
                f"{entry['user_id']}",
                callback_data=f"blacklist_view:{entry['user_id']}"
            )
        ])

    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)


def blacklist_entry_keyboard(user_id):
    """Кнопки карточки пользователя в чёрном списке."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Убрать из чёрного списка",
                callback_data=f"blacklist_remove:{user_id}"
            )
        ],
        [InlineKeyboardButton("⬅️ Назад", callback_data="blacklist")]
    ])


def cancel_manual_blacklist_keyboard():
    """Кнопка отмены ручного добавления в чёрный список."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚫 Отменить", callback_data="blacklist_manual_cancel")]
    ])


def cancel_contact_admin_keyboard():
    """Кнопка отмены сообщения администрации."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚫 Отменить", callback_data="contact_admin_cancel")]
    ])


def contact_admin_settings_keyboard(enabled):
    """Кнопки управления связью с администрацией для админов."""
    if enabled:
        toggle_text = "🔕 Отключить связь"
    else:
        toggle_text = "🔔 Включить связь"

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(toggle_text, callback_data="contact_admin_toggle")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])
