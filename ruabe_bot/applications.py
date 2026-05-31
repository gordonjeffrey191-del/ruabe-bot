import html

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


def build_application_text(user):
    """Формирует итоговую заявку для администраторов."""
    session = get_or_create_session(user.id)

    text = (
        "📝 Новая заявка в чат\n\n"
        f"{user_display_html(user)}\n\n"
    )

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
