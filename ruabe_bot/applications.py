import html

from .database import get_application_history
from .questionnaire import QUESTIONNAIRE
from .sessions import get_or_create_session
from .utils import risk_icon, user_display_html

# ============================================================
# МОДУЛЬ 11. СБОРКА ТЕКСТА ЗАЯВКИ
# Здесь формируется предпросмотр для пользователя и заявка для админов.
# ============================================================

def build_preview_text(user):
    """Показывает пользователю его ответы перед отправкой заявки."""
    session = get_or_create_session(user.id)

    text = "📋 Ваша заявка готова к отправке.\n\nПроверьте ответы ниже:\n\n"

    for index, question in enumerate(QUESTIONNAIRE, start=1):
        answer_data = session["answers"].get(question["id"])
        answer_text = answer_data["text"] if answer_data else "нет ответа"

        text += f"{index}. {question['question']}\n"
        text += f"Ответ: {answer_text}\n\n"

    text += "Если всё верно — отправьте заявку. Если хотите изменить ответы — заполните анкету заново."
    return text


def application_history_status_text(status):
    """Возвращает понятный текст статуса для истории заявок."""
    if status == "approved":
        return "одобрен"
    if status == "rejected_with_reason":
        return "отклонён с причиной"
    if status == "rejected":
        return "отклонён"
    if status == "blacklisted":
        return "добавлен в чёрный список"

    return status


def build_application_history_text(user_id):
    """Формирует блок истории прошлых заявок для администраторов."""
    history = get_application_history(user_id)

    if not history:
        return ""

    text = "📚 История заявок\n\n"

    for item in reversed(history):
        decided_at = item["decided_at"].strftime("%d.%m.%Y")
        status_text = application_history_status_text(item["status"])
        admin_name = html.escape(item["admin_name"])

        text += (
            f"• {decided_at} — {status_text}, "
            f"админ: {admin_name}\n"
        )

    return f"{text}\n"


def yes_no_text(value):
    """Форматирует булево значение для заявки."""
    if value is None:
        return "не удалось проверить"

    return "есть" if value else "нет"


def build_applicant_extra_info_text(extra_info):
    """Формирует блок дополнительной информации о пользователе."""
    if not extra_info:
        return ""

    has_avatar = yes_no_text(extra_info.get("has_avatar"))
    is_premium = "да" if extra_info.get("is_premium") else "нет"
    language_code = html.escape(extra_info.get("language_code") or "неизвестно")

    return (
        "Дополнительно:\n"
        f"• Аватарка: {has_avatar}\n"
        f"• Premium: {is_premium}\n"
        f"• Язык Telegram: {language_code}\n\n"
    )


def build_application_text(user, extra_info=None):
    """Формирует итоговую заявку для администраторов."""
    session = get_or_create_session(user.id)

    text = (
        "📝 Новая заявка в чат\n\n"
        f"{user_display_html(user)}\n\n"
    )

    text += build_applicant_extra_info_text(extra_info)

    text += build_application_history_text(user.id)

    if session["resets"] > 0:
        text += f"🔁 Анкета перезаполнялась: {session['resets']} раз(а)\n"

    if session["history_risky"]:
        text += "\n⚠️ Ранее выбирались подозрительные ответы:\n"

        for item in session["history_risky"]:
            text += f"• {html.escape(item)}\n"

        text += "\n"

    text += "Ответы:\n\n"

    for index, question in enumerate(QUESTIONNAIRE, start=1):
        answer_data = session["answers"].get(question["id"])

        if answer_data:
            answer_text = html.escape(answer_data["text"])
            risk = answer_data["risk"]
        else:
            answer_text = "нет ответа"
            risk = "warn"

        text += f"{index}. {html.escape(question['question'])}\n"
        text += f"{risk_icon(risk)} {answer_text}\n\n"

    return text
