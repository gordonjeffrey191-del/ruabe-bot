from datetime import datetime, timezone

from .questionnaire import QUESTIONNAIRE
from .state import user_sessions
from .utils import risk_icon

# ============================================================
# МОДУЛЬ 10. СЕССИИ АНКЕТЫ
# Здесь хранится временное прохождение анкеты пользователем.
# ============================================================

def get_or_create_session(user_id):
    """Создаёт или возвращает текущую анкетную сессию пользователя."""
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "current_step": 0,
            "answers": {},
            "history_risky": [],
            "resets": 0,
            "started_at": datetime.now(timezone.utc),
        }

    return user_sessions[user_id]


def start_new_session(user_id):
    """Начинает новую анкету, но сохраняет историю подозрительных прошлых ответов."""
    old_session = user_sessions.get(user_id, {})

    user_sessions[user_id] = {
        "current_step": 0,
        "answers": {},
        "history_risky": old_session.get("history_risky", []),
        "resets": old_session.get("resets", 0),
        "started_at": datetime.now(timezone.utc),
    }

    return user_sessions[user_id]


def collect_risky_answers(session):
    """Собирает только подозрительные ответы: ⚠️ и ❌."""
    risky = []

    for question in QUESTIONNAIRE:
        question_id = question["id"]

        if question_id not in session["answers"]:
            continue

        answer_data = session["answers"][question_id]
        risk = answer_data["risk"]

        if risk in ("warn", "red"):
            risky.append(
                f"{risk_icon(risk)} {question['question']} — {answer_data['text']}"
            )

    return risky


def add_history_from_current_answers(user_id):
    """Добавляет текущие ⚠️ и ❌ ответы в историю при перезаполнении анкеты."""
    session = user_sessions.get(user_id)

    if not session:
        return

    risky = collect_risky_answers(session)

    for item in risky:
        if item not in session["history_risky"]:
            session["history_risky"].append(item)
