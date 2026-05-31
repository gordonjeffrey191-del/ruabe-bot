import html

from .faq import FAQ_ITEMS
from .questionnaire import QUESTIONNAIRE

# ============================================================
# Здесь мелкие функции для поиска, форматирования и защиты.
# ============================================================

def risk_icon(risk):
    """Возвращает значок риска для ответа анкеты."""
    if risk == "ok":
        return "✅"
    if risk == "warn":
        return "⚠️"
    if risk == "red":
        return "❌"
    return "✅"


def find_answer(question_index, answer_id):
    """Находит ответ анкеты по номеру вопроса и короткому ID ответа."""
    question = QUESTIONNAIRE[question_index]

    for row in question["buttons"]:
        for answer in row:
            if answer["id"] == answer_id:
                return answer

    return None


def find_faq_item(faq_id):
    """Находит FAQ-вопрос по короткому ID."""
    for item in FAQ_ITEMS:
        if item["id"] == faq_id:
            return item

    return None


def user_profile_url(user_id, username=None):
    """Возвращает ссылку на профиль пользователя для администраторов."""
    if username:
        return f"https://t.me/{username}"

    return f"tg://user?id={user_id}"


def user_display_html(user):
    """
    Формирует кликабельный блок пользователя для заявки.
    Имя и ID можно нажать, чтобы открыть профиль пользователя.
    """

    full_name = html.escape(user.full_name)

    if user.username:
        username_url = html.escape(user_profile_url(user.id, user.username), quote=True)
        username = f'<a href="{username_url}">@{html.escape(user.username)}</a>'
    else:
        username = "username отсутствует"

    clickable_name = (
        f'<a href="tg://user?id={user.id}">{full_name}</a>'
    )

    clickable_id = (
        f'<a href="tg://user?id={user.id}">{user.id}</a>'
    )

    profile_url = html.escape(user_profile_url(user.id, user.username), quote=True)
    profile_link = f'<a href="{profile_url}">открыть аккаунт</a>'

    return (
        f"Имя: {clickable_name}\n"
        f"Username: {username}\n"
        f"ID: <code>{user.id}</code>\n"
        f"ID-ссылка: {clickable_id}\n"
        f"Профиль: {profile_link}"
    )


def user_display_plain(user):
    """Формирует обычный текстовый блок пользователя для технических логов."""

    username = (
        f"@{user.username}"
        if user.username
        else "username отсутствует"
    )

    return (
        f"Имя: {user.full_name}\n"
        f"Username: {username}\n"
        f"ID: {user.id}"
    )


def split_text(text, max_length=3900):
    """Делит слишком длинный текст на несколько сообщений Telegram."""

    parts = []

    while len(text) > max_length:
        split_at = text.rfind("\n\n", 0, max_length)

        if split_at == -1:
            split_at = max_length

        parts.append(text[:split_at])
        text = text[split_at:].strip()

    parts.append(text)

    return parts


def main_menu_text():
    """Текст главного меню бота."""

    return (
        "👋 Добро пожаловать в RUABE.\n\n"
        "Мы активный Telegram-чат с живым общением, обсуждениями и сообществом людей из Reddit.\n\n"
        "Перед подачей заявки рекомендуем ознакомиться с информацией ниже."
    )
