# ============================================================
# RUABE BOT
# Единый модульный файл bot.py
#
# Как пользоваться этим кодом в будущем:
# - Каждый большой блок отделён заголовком "МОДУЛЬ".
# - Если нужно изменить FAQ — ищи МОДУЛЬ 3.
# - Если нужно изменить анкету — ищи МОДУЛЬ 4.
# - Если нужно изменить базу данных — ищи МОДУЛЬ 5.
# - Если нужно изменить кнопки — ищи МОДУЛЬ 6.
# - Если нужно изменить логику заявок — ищи МОДУЛЬ 12.
# ============================================================


# region МОДУЛЬ 1. ИМПОРТЫ
# ============================================================
# Здесь подключаются библиотеки, которые нужны боту.
# ============================================================

import os
import html
import asyncio
from datetime import datetime, timedelta, timezone

import psycopg2
from psycopg2.extras import Json

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# endregion

# region МОДУЛЬ 2. ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ И НАСТРОЙКИ
# ============================================================
# МОДУЛЬ 2. ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ И НАСТРОЙКИ
# Эти значения берутся из Render Environment.
# ============================================================

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_IDS = [int(x.strip()) for x in os.environ["ADMIN_IDS"].split(",")]
CHAT_LINK = os.environ.get("CHAT_LINK", "temporary")
LOG_CHAT_ID = int(os.environ["LOG_CHAT_ID"])
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
PORT = int(os.environ.get("PORT", 10000))
DATABASE_URL = os.environ["DATABASE_URL"]

MAIN_CHAT_ID_RAW = os.environ.get("MAIN_CHAT_ID", "").strip()
MAIN_CHAT_ID = int(MAIN_CHAT_ID_RAW) if MAIN_CHAT_ID_RAW else None

COOLDOWN_MINUTES = 30
APPLICATION_TTL_DAYS = 3
# endregion

# region МОДУЛЬ 3. ВРЕМЕННАЯ ПАМЯТЬ БОТА
# ============================================================
# Эти данные живут только до перезапуска Render.
# Важные заявки теперь хранятся в PostgreSQL.
# ============================================================

section_messages = {}
user_sessions = {}
application_cooldowns = {}
application_locks = {}

# Здесь временно хранится состояние администратора,
# если он нажал "Отклонить с причиной" и должен написать текст причины.
admin_rejection_drafts = {}

# endregion

# region МОДУЛЬ 4. ТЕКСТЫ: ПРАВИЛА И БЕЗОПАСНОСТЬ
# ============================================================
# МОДУЛЬ 4. ТЕКСТЫ: ПРАВИЛА И БЕЗОПАСНОСТЬ
# Здесь можно менять тексты разделов "Правила" и "Безопасность".
# ============================================================

RULES_TEXT = """🗓 Правила чата

1. В чате могут находиться только лица старше 16 лет.
Участие в подчатах «Познакомимся?» и «Вопросы 18+» разрешено только с 18 лет. Если пользователь скрывает или указывает недостоверный возраст, администрация не несёт за это ответственности.

2. Запрещено использовать языки, кроме русского, украинского и белорусского, в качестве основных.
Наказание: устное предупреждение (только при первом нарушении). При продолжении — предупреждение на неделю и мут на 30 минут. Длительное игнорирование требования — бан.

3. Запрещена публикация порнографии (в том числе частично скрытой или зацензуренной), шок-контента, а также политических, военных и религиозных символов или намёков на них.
Наказание: мут на 1 час, предупреждение сроком от недели до неограниченного либо бан — в зависимости от тяжести нарушения.

4. Запрещено обсуждение наркотиков, религии, политики, военной тематики и суицида вне специального подчата для дискуссий.
Полностью запрещены пропаганда суицида, распространение суицидальных мыслей и навязывание суицида как способа решения проблем.
Наказание: мут на 30 минут и предупреждение на месяц.

5. Запрещены:
- спам однотипными сообщениями более 3 раз подряд в течение часа;
- использование игровых и развлекательных ботов вне подчатов «Ботоферма» и «Правда или действие».
Наказание: мут на 1 час и предупреждение на неделю. Интенсивный спам — бан без возможности апелляции.

6. Запрещены:
- проявления ненависти;
- личные оскорбления;
- слежка за участниками;
- разглашение личной информации;
- дезинформация;
- пробив и попытки деанона.

Наказание: мут на 30 минут и предупреждение на месяц. За слежку, пробив или причинение вреда участникам — бан без возможности апелляции.

Каждый участник самостоятельно несёт ответственность за сохранение собственной анонимности и должен осознавать риски при публикации личной информации.

7. Запрещена реклама своих или чужих соцсетей, сайтов, сообществ и других ресурсов без согласования с администрацией, а также использование ботов сторонних каналов.
Наказание: бессрочное предупреждение или бан. В случае случайного срабатывания возможен пересмотр наказания.

8. Длительные споры, не соответствующие теме подчата, и конфликтные дискуссии должны переводиться в специальный подчат.
Переход на личности, оскорбления и провокации считаются нарушением правил.
Наказание: устное предупреждение с просьбой перейти в соответствующий подчат. При игнорировании — мут 30 минут. За переход на личности — мут 30 минут и/или предупреждение.

9. Запрещён обход наказаний и бана с использованием дополнительных аккаунтов.
Наказание: бан всех аккаунтов, участвующих в обходе, с возможностью апелляции.

10. Запрещены попрошайничество, вымогательство, просьбы занять деньги и иные финансовые манипуляции в рамках чата.
Наказание: бессрочное предупреждение и удаление соответствующих сообщений.

11. Запрещено использовать правила чата для манипуляций, давления на участников или намеренных провокаций.
Правила применяются исходя из их смысла и контекста ситуации.
Наказание: предупреждение на месяц.

12. В спорных ситуациях администрация принимает решения с учётом контекста, здравого смысла и необходимости поддержания комфортной атмосферы в чате.

13. Чат ориентирован на активное общение и участие в жизни сообщества.
Постоянное нахождение в чате исключительно в роли наблюдателя не приветствуется.

Неактивность более 7 дней или полное отсутствие активности у новичков может стать причиной удаления из чата с возможностью возвращения.
Исключения возможны при наличии прошлой активности или заранее сообщённого отсутствия.
"""


SAFETY_TEXT = """🛡️ Безопасность

• Не публикуйте личную информацию без необходимости.
• С осторожностью делитесь фотографиями, контактами и другими приватными данными.
• Администрация никогда не запрашивает пароли, коды подтверждения или доступ к аккаунтам.
• Если кто-либо вызывает у вас подозрения или нарушает правила — обратитесь к администрации.
• Помните, что ответственность за сохранение собственной анонимности всегда остаётся за самим участником.
"""
# endregion

# region МОДУЛЬ 5. FAQ
# ============================================================
# МОДУЛЬ 5. FAQ
# Здесь находятся все вопросы и ответы FAQ.
# button  — короткий текст на кнопке.
# question — полный вопрос внутри ответа.
# answer — ответ, который увидит пользователь.
# ============================================================

FAQ_ITEMS = [
    {
        "id": "reject_reason",
        "button": "Что может стать причиной отказа?",
        "question": "Что может стать причиной отказа?",
        "answer": "Причиной отказа могут стать подозрительное поведение, неадекватные ответы в анкете, нарушение правил ещё до вступления, серьёзные нарушения в прошлых чатах сообщества или явное несоответствие атмосфере сообщества.",
    },
    {
        "id": "why_application",
        "button": "Зачем нужна заявка?",
        "question": "Зачем нужна заявка на вступление?",
        "answer": "Заявка нужна для того, чтобы снизить количество случайных, конфликтных или вредоносных участников и сохранить комфортную атмосферу в сообществе.",
    },
    {
        "id": "review_time",
        "button": "Сколько рассматривается заявка?",
        "question": "Сколько обычно рассматривается заявка?",
        "answer": "Обычно заявки рассматриваются довольно быстро, но точное время зависит от активности администрации.",
    },
    {
        "id": "new_account",
        "button": "Можно ли использовать новый аккаунт?",
        "question": "Можно ли использовать анонимный/новый аккаунт?",
        "answer": "Да, использование анонимных или новых аккаунтов допускается, однако администрация может уделять таким аккаунтам больше внимания.",
    },
    {
        "id": "hide_age",
        "button": "Можно ли скрывать возраст?",
        "question": "Можно ли скрывать возраст?",
        "answer": "Да, вы не обязаны раскрывать свой реальный возраст. Однако чат предназначен только для лиц старше 16 лет. Если администрации станет известно, что участнику меньше 16 лет, он будет заблокирован без возможности апелляции.",
    },
    {
        "id": "sfw",
        "button": "Чат только для SFW-тем?",
        "question": "Чат ориентирован только на SFW-тематику?",
        "answer": "Нет. В чате присутствуют разные темы общения, включая отдельный подчат 18+ для обсуждения NSFW-тематики. Однако даже в нём запрещена публикация порнографии, в том числе в частично скрытом или зацензуренном виде.",
    },
    {
        "id": "activity",
        "button": "Насколько важна активность?",
        "question": "Насколько важна активность новичков?",
        "answer": "Чат ориентирован на живое общение, поэтому активность новых участников приветствуется и ценится.",
    },
    {
        "id": "read_only",
        "button": "Можно ли просто читать чат?",
        "question": "Можно ли просто читать чат?",
        "answer": "Постоянное нахождение исключительно в роли наблюдателя не приветствуется. Сообщество строится вокруг активного участия в общении.",
    },
    {
        "id": "chat_active",
        "button": "Насколько чат активный?",
        "question": "Насколько чат активный?",
        "answer": "Активность зависит от времени суток и дней недели, но в чате регулярно происходят обсуждения и общение.",
    },
    {
        "id": "conflict",
        "button": "Что делать при конфликте?",
        "question": "Что делать, если возник конфликт с участником?",
        "answer": "Рекомендуется не усугублять конфликт и обратиться к администрации при необходимости.",
    },
    {
        "id": "rules_violation",
        "button": "Что делать при нарушениях?",
        "question": "Что делать, если кто-то нарушает правила?",
        "answer": "Сообщите об этом администрации и по возможности приложите контекст ситуации.",
    },
    {
        "id": "nick_avatar",
        "button": "Есть ли ограничения на ник и аватар?",
        "question": "Есть ли ограничения на никнеймы и аватарки?",
        "answer": "Да. Никнеймы и аватарки не должны нарушать правила сообщества или содержать запрещённый контент.",
    },
    {
        "id": "country",
        "button": "Есть ли ограничения по стране?",
        "question": "Есть ли ограничения по стране проживания?",
        "answer": "Нет, ограничений по стране проживания нет.",
    },
    {
        "id": "introduce",
        "button": "Нужно ли представляться?",
        "question": "Нужно ли представляться после вступления?",
        "answer": "Нет, это не обязательно. Однако знакомство с участниками обычно помогает быстрее влиться в общение.",
    },
    {
        "id": "return_later",
        "button": "Можно ли уйти и вернуться позже?",
        "question": "Можно ли покинуть чат и вернуться позже?",
        "answer": "Да, в большинстве случаев повторное вступление возможно.",
    },
    {
        "id": "invite_friend",
        "button": "Можно ли пригласить друга?",
        "question": "Можно ли пригласить друга?",
        "answer": "Обычно да, однако приглашённый участник также должен пройти одобрение через бота.",
    },
    {
        "id": "subchats",
        "button": "Есть ли отдельные подчаты?",
        "question": "Есть ли в чате подтемы и отдельные подчаты?",
        "answer": "Да. В сообществе присутствуют отдельные подчаты для разных тем и форматов общения.",
    },
    {
        "id": "dating_section",
        "button": "Есть ли раздел знакомств?",
        "question": "Есть ли в чате раздел знакомств?",
        "answer": "Да, в сообществе присутствует отдельный подчат для знакомств.",
    },
    {
        "id": "creative",
        "button": "Есть ли раздел творчества?",
        "question": "Есть ли раздел для творчества и артов?",
        "answer": "Да, участники могут делиться своим творчеством и работами в соответствующих разделах сообщества.",
    },
    {
        "id": "personal_problems",
        "button": "Можно ли обсуждать личные проблемы?",
        "question": "Можно ли обсуждать личные проблемы?",
        "answer": "Да, если обсуждение остаётся в рамках правил и уважительного общения.",
    },
    {
        "id": "discord",
        "button": "Есть ли Discord чата?",
        "question": "Есть ли у сообщества Discord или другие платформы?",
        "answer": "Да. У сообщества есть официальный Discord-сервер, где участники проводят совместные активности, ивенты и общаются на дополнительные темы.",
    },
    {
        "id": "without_reddit",
        "button": "Можно ли попасть без Reddit?",
        "question": "Можно ли попасть в чат без Reddit?",
        "answer": "Да, наличие Reddit-аккаунта не является обязательным условием для вступления.",
    },
]
# endregion

# region МОДУЛЬ 6. АНКЕТА
# ============================================================
# МОДУЛЬ 6. АНКЕТА
# Здесь меняются вопросы анкеты, кнопки и маркеры риска.
#
# risk:
# ok   — нормальный ответ, в заявке будет ✅
# warn — стоит обратить внимание, в заявке будет ⚠️
# red  — красный флаг, в заявке будет ❌
# ============================================================

QUESTIONNAIRE = [
    {
        "id": "age",
        "question": "Сколько вам лет?",
        "buttons": [
            [{"id": "under16", "text": "Меньше 16", "risk": "red"}],
            [
                {"id": "16_17", "text": "16–17", "risk": "warn"},
                {"id": "18_21", "text": "18–21", "risk": "ok"},
            ],
            [
                {"id": "22_25", "text": "22–25", "risk": "ok"},
                {"id": "26_30", "text": "26–30", "risk": "ok"},
            ],
            [
                {"id": "31_38", "text": "31–38", "risk": "ok"},
                {"id": "38plus", "text": "38+", "risk": "ok"},
            ],
        ],
    },
    {
        "id": "motivation",
        "question": "Зачем вы хотите вступить в чат?",
        "buttons": [
            [
                {"id": "chat", "text": "Общение", "risk": "ok"},
                {"id": "dating", "text": "Знакомства", "risk": "ok"},
            ],
            [
                {"id": "discuss", "text": "Дискуссии", "risk": "ok"},
                {"id": "people", "text": "Найти новых людей", "risk": "ok"},
            ],
            [{"id": "learn_members", "text": "Узнать об участниках", "risk": "warn"}],
            [
                {"id": "look", "text": "Посмотреть чат", "risk": "warn"},
                {"id": "adult", "text": "18+ общение", "risk": "red"},
            ],
        ],
    },
    {
        "id": "style",
        "question": "Какой формат общения вам ближе?",
        "buttons": [
            [{"id": "active", "text": "Активное общение", "risk": "ok"}],
            [{"id": "sometimes", "text": "Иногда участвовать", "risk": "ok"}],
            [{"id": "read", "text": "Больше читать", "risk": "warn"}],
            [{"id": "unknown", "text": "Пока не знаю", "risk": "warn"}],
        ],
    },
    {
        "id": "rules_attitude",
        "question": "Как вы относитесь к правилам в сообществах?",
        "buttons": [
            [{"id": "order", "text": "Они нужны для порядка", "risk": "ok"}],
            [{"id": "adequate", "text": "Главное — адекватность", "risk": "ok"}],
            [{"id": "depends", "text": "Зависит от сообщества", "risk": "warn"}],
            [{"id": "strict_bad", "text": "Слишком строгие правила мешают общению", "risk": "red"}],
        ],
    },
    {
        "id": "anonymity",
        "question": "Как вы относитесь к анонимности участников в интернете?",
        "buttons": [
            [{"id": "respect", "text": "Её важно уважать", "risk": "ok"}],
            [{"id": "own_resp", "text": "Каждый сам отвечает за свою анонимность", "risk": "warn"}],
            [{"id": "depends", "text": "Зависит от ситуации", "risk": "warn"}],
            [
                {
                    "id": "their_problem",
                    "text": "Если человек раскрывает информацию о себе — это его проблема",
                    "risk": "red",
                }
            ],
            [{"id": "no_anon", "text": "Интернет без анонимности был бы интереснее", "risk": "red"}],
        ],
    },
]
# endregion

# region МОДУЛЬ 7. БАЗА ДАННЫХ POSTGRESQL
# ============================================================
# МОДУЛЬ 7. БАЗА ДАННЫХ POSTGRESQL
# Здесь бот сохраняет заявки, чтобы они не пропадали после
# сна или перезапуска Render.
# ============================================================

def db_connect():
    """Создаёт подключение к PostgreSQL."""
    return psycopg2.connect(DATABASE_URL)


def init_db():
    """Создаёт таблицу заявок, если её ещё нет, и удаляет старые заявки."""
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    user_id BIGINT PRIMARY KEY,
                    status TEXT NOT NULL,
                    application_text TEXT NOT NULL,
                    admin_messages JSONB NOT NULL DEFAULT '[]'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)

            cur.execute("""
                DELETE FROM applications
                WHERE updated_at < NOW() - INTERVAL '3 days';
            """)


def save_application_to_db(user_id, application_text):
    """Сохраняет новую заявку или перезаписывает старую заявку пользователя."""
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO applications (
                    user_id,
                    status,
                    application_text,
                    admin_messages,
                    created_at,
                    updated_at
                )
                VALUES (%s, 'pending', %s, '[]'::jsonb, NOW(), NOW())
                ON CONFLICT (user_id)
                DO UPDATE SET
                    status = 'pending',
                    application_text = EXCLUDED.application_text,
                    admin_messages = '[]'::jsonb,
                    created_at = NOW(),
                    updated_at = NOW();
            """, (user_id, application_text))


def update_application_messages_in_db(user_id, admin_messages):
    """Сохраняет ID сообщений с заявкой у администраторов."""
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE applications
                SET admin_messages = %s, updated_at = NOW()
                WHERE user_id = %s;
            """, (Json(admin_messages), user_id))


def get_application_from_db(user_id):
    """Возвращает заявку пользователя из базы, если она не старше 3 дней."""
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT status, application_text, admin_messages
                FROM applications
                WHERE user_id = %s
                  AND updated_at >= NOW() - INTERVAL '3 days';
            """, (user_id,))

            row = cur.fetchone()

            if not row:
                return None

            status, application_text, admin_messages = row

            return {
                "status": status,
                "application_text": application_text,
                "admin_messages": admin_messages or [],
            }


def set_application_status_in_db(user_id, status):
    """Меняет статус заявки: pending, approved или rejected."""
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE applications
                SET status = %s, updated_at = NOW()
                WHERE user_id = %s;
            """, (status, user_id))


def has_pending_application(user_id):
    """Проверяет, есть ли у пользователя активная заявка на рассмотрении."""
    app = get_application_from_db(user_id)
    return bool(app and app["status"] == "pending")
# endregion

# region МОДУЛЬ 8. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
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


def user_display_html(user):
    """
    Формирует кликабельный блок пользователя для заявки.
    Имя и ID можно нажать, чтобы открыть профиль пользователя.
    """

    full_name = html.escape(user.full_name)

    username = (
        f"@{html.escape(user.username)}"
        if user.username
        else "username отсутствует"
    )

    clickable_name = (
        f'<a href="tg://user?id={user.id}">{full_name}</a>'
    )

    clickable_id = (
        f'<a href="tg://user?id={user.id}">{user.id}</a>'
    )

    return (
        f"Имя: {clickable_name}\n"
        f"Username: {username}\n"
        f"ID: {clickable_id}"
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

# endregion

# region МОДУЛЬ 9. КЛАВИАТУРЫ
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


def admin_decision_keyboard(user_id):
    """Кнопки для администраторов под заявкой."""
    return InlineKeyboardMarkup([
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

# endregion

# region МОДУЛЬ 10. СЕССИИ АНКЕТЫ
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
# endregion

# region МОДУЛЬ 11. СБОРКА ТЕКСТА ЗАЯВКИ
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
# endregion

# region МОДУЛЬ 12. БЕЗОПАСНЫЕ ДЕЙСТВИЯ TELEGRAM
# ============================================================
# МОДУЛЬ 12. БЕЗОПАСНЫЕ ДЕЙСТВИЯ TELEGRAM
# Здесь функции, которые не должны ломать бота при ошибках Telegram.
# ============================================================

async def safe_callback_answer(query, text=None, show_alert=False):
    """Отвечает на нажатие кнопки. Ошибки игнорируются, чтобы бот не падал."""
    try:
        await query.answer(text=text, show_alert=show_alert)
    except Exception:
        pass


async def log_event(context, text):
    """Отправляет технический лог в лог-чат."""
    try:
        await context.bot.send_message(
            chat_id=LOG_CHAT_ID,
            text=text
        )
    except Exception:
        pass


async def delete_section_messages(context, user_id):
    """Удаляет старые сообщения разделов: правила, FAQ, безопасность."""
    message_ids = section_messages.pop(user_id, [])

    for message_id in message_ids:
        try:
            await context.bot.delete_message(
                chat_id=user_id,
                message_id=message_id
            )
        except Exception:
            pass


async def safe_delete_query_message(query):
    """Безопасно удаляет сообщение, на котором была нажата кнопка."""
    try:
        await query.delete_message()
    except Exception:
        pass
# endregion

# region МОДУЛЬ 13. ГЛАВНОЕ МЕНЮ И ИНФОРМАЦИОННЫЕ РАЗДЕЛЫ
# ============================================================
# МОДУЛЬ 13. ГЛАВНОЕ МЕНЮ И ИНФОРМАЦИОННЫЕ РАЗДЕЛЫ
# Здесь логика /start, правил, FAQ и безопасности.
# ============================================================

async def send_main_menu(context, user_id):
    """Отправляет главное меню пользователю."""
    await context.bot.send_message(
        chat_id=user_id,
        text=main_menu_text(),
        reply_markup=main_menu()
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start. Работает только в личке бота, в группах игнорируется."""
    if update.effective_chat.type != "private":
        return

    user_id = update.effective_user.id
    await delete_section_messages(context, user_id)

    await update.message.reply_text(
        main_menu_text(),
        reply_markup=main_menu()
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
# endregion

# region МОДУЛЬ 14. ПРОВЕРКА COOLDOWN И ПОВТОРНЫХ ЗАЯВОК
# ============================================================
# МОДУЛЬ 14. ПРОВЕРКА COOLDOWN И ПОВТОРНЫХ ЗАЯВОК
# Здесь бот защищается от спама заявками.
# ============================================================

def cooldown_remaining(user_id):
    """Проверяет, сколько времени осталось до повторной отправки заявки."""
    last_submit = application_cooldowns.get(user_id)

    if not last_submit:
        return None

    cooldown_end = last_submit + timedelta(minutes=COOLDOWN_MINUTES)
    now = datetime.now(timezone.utc)

    if now >= cooldown_end:
        return None

    return cooldown_end - now


async def check_can_apply(query, context):
    """Проверяет, может ли пользователь начать новую заявку."""
    user_id = query.from_user.id

    if has_pending_application(user_id):
        await query.edit_message_text(
            "⏳ Ваша заявка уже находится на рассмотрении администрации.\n\n"
            "Пожалуйста, дождитесь решения.",
            reply_markup=back_button()
        )
        return False

    remaining = cooldown_remaining(user_id)

    if remaining:
        minutes = max(1, int(remaining.total_seconds() // 60))

        await query.edit_message_text(
            f"⏳ Вы уже недавно отправляли заявку.\n\n"
            f"Повторная отправка будет доступна примерно через {minutes} мин.",
            reply_markup=back_button()
        )
        return False

    return True
# endregion

# region МОДУЛЬ 15. ПРОХОЖДЕНИЕ АНКЕТЫ
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
# endregion

# region МОДУЛЬ 16. ОТПРАВКА ЗАЯВКИ АДМИНАМ
# ============================================================
# МОДУЛЬ 16. ОТПРАВКА ЗАЯВКИ АДМИНАМ
# Здесь заявка сохраняется в базу и рассылается администраторам.
# ============================================================

async def submit_application(query, context, user_id):
    """Отправляет готовую заявку администраторам."""
    if query.from_user.id != user_id:
        await safe_callback_answer(query, "Это не ваша заявка.", show_alert=True)
        return

    if has_pending_application(user_id):
        await safe_callback_answer(query)
        await query.edit_message_text(
            "⏳ Ваша заявка уже находится на рассмотрении администрации.",
            reply_markup=back_button()
        )
        return

    remaining = cooldown_remaining(user_id)

    if remaining:
        minutes = max(1, int(remaining.total_seconds() // 60))

        await safe_callback_answer(query)
        await query.edit_message_text(
            f"⏳ Вы уже недавно отправляли заявку.\n\n"
            f"Повторная отправка будет доступна примерно через {minutes} мин.",
            reply_markup=back_button()
        )
        return

    session = user_sessions.get(user_id)

    if not session or len(session["answers"]) < len(QUESTIONNAIRE):
        await safe_callback_answer(query)
        await query.edit_message_text(
            "Заявка не найдена или заполнена не полностью.",
            reply_markup=back_button()
        )
        return

    await safe_callback_answer(query)

    application_cooldowns[user_id] = datetime.now(timezone.utc)

    application_text = build_application_text(query.from_user)

    save_application_to_db(user_id, application_text)

    admin_messages = []

    await context.bot.send_message(
        chat_id=LOG_CHAT_ID,
        text="📌 Заявка сохранена в лог:\n\n" + application_text,
        parse_mode="HTML"
    )

    await log_event(
        context,
        "🟩 Пользователь отправил заявку\n\n"
        f"{user_display_plain(query.from_user)}"
    )

    for admin_id in ADMIN_IDS:
        try:
            msg = await context.bot.send_message(
                chat_id=admin_id,
                text=application_text,
                reply_markup=admin_decision_keyboard(user_id),
                parse_mode="HTML"
            )

            admin_messages.append({
                "chat_id": admin_id,
                "message_id": msg.message_id,
            })
        except Exception as error:
            await log_event(
                context,
                "⚠️ Не удалось отправить заявку администратору\n\n"
                f"Админ ID: {admin_id}\n"
                f"Пользователь ID: {user_id}\n"
                f"Ошибка: {error}"
            )

    update_application_messages_in_db(user_id, admin_messages)

    await query.edit_message_text(
        "✅ Спасибо! Заявка отправлена администрации.",
        reply_markup=back_button()
    )
# endregion

# region МОДУЛЬ 17. ОДОБРЕНИЕ И ОТКЛОНЕНИЕ ЗАЯВОК
# ============================================================
# Здесь администраторы принимают или отклоняют заявки.
# ============================================================

async def approve_user(context, user_id):
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
            "✅ Ваша заявка одобрена.\n\n"
            "Нажмите кнопку ниже, чтобы войти в чат."
        ),
        reply_markup=keyboard
    )


async def reject_user(context, user_id):
    """Отправляет пользователю стандартное сообщение об отказе."""
    await context.bot.send_message(
        chat_id=user_id,
        text="Спасибо за заявку. Сейчас мы не можем одобрить вступление в чат."
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

# endregion

# region МОДУЛЬ 18. ГЛАВНЫЙ ОБРАБОТЧИК КНОПОК
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

# endregion

# region МОДУЛЬ 19. ЗАПУСК БОТА
# ============================================================
# Здесь создаётся приложение Telegram и запускается webhook.
# ============================================================

def main():
    """Главная функция запуска бота."""
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_rejection_reason))

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
    )

# endregion


if __name__ == "__main__":
    main()