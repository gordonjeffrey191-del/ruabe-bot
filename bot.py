import os
import asyncio
from datetime import datetime, timedelta, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_IDS = [int(x.strip()) for x in os.environ["ADMIN_IDS"].split(",")]
CHAT_LINK = os.environ.get("CHAT_LINK", "temporary")
LOG_CHAT_ID = int(os.environ["LOG_CHAT_ID"])
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
PORT = int(os.environ.get("PORT", 10000))

MAIN_CHAT_ID_RAW = os.environ.get("MAIN_CHAT_ID", "").strip()
MAIN_CHAT_ID = int(MAIN_CHAT_ID_RAW) if MAIN_CHAT_ID_RAW else None

COOLDOWN_MINUTES = 30

section_messages = {}
user_sessions = {}
pending_applications = set()
application_cooldowns = {}

application_status = {}
application_locks = {}
admin_application_messages = {}
admin_application_texts = {}


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


FAQ_ITEMS = [
    ("Что может стать причиной отказа?", "Причиной отказа могут стать подозрительное поведение, неадекватные ответы в анкете, нарушение правил ещё до вступления, серьёзные нарушения в прошлых чатах сообщества или явное несоответствие атмосфере сообщества."),
    ("Зачем нужна заявка на вступление?", "Заявка нужна для того, чтобы снизить количество случайных, конфликтных или вредоносных участников и сохранить комфортную атмосферу в сообществе."),
    ("Сколько обычно рассматривается заявка?", "Обычно заявки рассматриваются довольно быстро, но точное время зависит от активности администрации."),
    ("Можно ли использовать анонимный/новый аккаунт?", "Да, использование анонимных или новых аккаунтов допускается, однако администрация может уделять таким аккаунтам больше внимания."),
    ("Можно ли скрывать возраст?", "Да, вы не обязаны раскрывать свой реальный возраст. Однако чат предназначен только для лиц старше 16 лет. Если администрации станет известно, что участнику меньше 16 лет, он будет заблокирован без возможности апелляции."),
    ("Чат ориентирован только на SFW-тематику?", "Нет. В чате присутствуют разные темы общения, включая отдельный подчат 18+ для обсуждения NSFW-тематики. Однако даже в нём запрещена публикация порнографии, в том числе в частично скрытом или зацензуренном виде."),
    ("Насколько важна активность новичков?", "Чат ориентирован на живое общение, поэтому активность новых участников приветствуется и ценится."),
    ("Можно ли просто читать чат?", "Постоянное нахождение исключительно в роли наблюдателя не приветствуется. Сообщество строится вокруг активного участия в общении."),
    ("Насколько чат активный?", "Активность зависит от времени суток и дней недели, но в чате регулярно происходят обсуждения и общение."),
    ("Что делать, если возник конфликт с участником?", "Рекомендуется не усугублять конфликт и обратиться к администрации при необходимости."),
    ("Что делать, если кто-то нарушает правила?", "Сообщите об этом администрации и по возможности приложите контекст ситуации."),
    ("Есть ли ограничения на никнеймы и аватарки?", "Да. Никнеймы и аватарки не должны нарушать правила сообщества или содержать запрещённый контент."),
    ("Есть ли ограничения по стране проживания?", "Нет, ограничений по стране проживания нет."),
    ("Нужно ли представляться после вступления?", "Нет, это не обязательно. Однако знакомство с участниками обычно помогает быстрее влиться в общение."),
    ("Можно ли покинуть чат и вернуться позже?", "Да, в большинстве случаев повторное вступление возможно."),
    ("Можно ли пригласить друга?", "Обычно да, однако приглашённый участник также должен пройти одобрение через бота."),
    ("Есть ли в чате подтемы и отдельные подчаты?", "Да. В сообществе присутствуют отдельные подчаты для разных тем и форматов общения."),
    ("Есть ли в чате раздел знакомств?", "Да, в сообществе присутствует отдельный подчат для знакомств."),
    ("Есть ли раздел для творчества и артов?", "Да, участники могут делиться своим творчеством и работами в соответствующих разделах сообщества."),
    ("Можно ли обсуждать личные проблемы?", "Да, если обсуждение остаётся в рамках правил и уважительного общения."),
    ("Есть ли у сообщества Discord или другие платформы?", "Да. У сообщества есть официальный Discord-сервер, где участники проводят совместные активности, ивенты и общаются на дополнительные темы."),
    ("Можно ли попасть в чат без Reddit?", "Да, наличие Reddit-аккаунта не является обязательным условием для вступления."),
]


QUESTIONNAIRE = [
    {
        "id": "age",
        "question": "Сколько вам лет?",
        "buttons": [
            [{"id": "under16", "text": "Меньше 16", "risk": "red"}],
            [{"id": "16_17", "text": "16–17", "risk": "warn"}, {"id": "18_21", "text": "18–21", "risk": "ok"}],
            [{"id": "22_25", "text": "22–25", "risk": "ok"}, {"id": "26_30", "text": "26–30", "risk": "ok"}],
            [{"id": "31_38", "text": "31–38", "risk": "ok"}, {"id": "38plus", "text": "38+", "risk": "ok"}],
        ],
    },
    {
        "id": "motivation",
        "question": "Зачем вы хотите вступить в чат?",
        "buttons": [
            [{"id": "chat", "text": "Общение", "risk": "ok"}, {"id": "dating", "text": "Знакомства", "risk": "ok"}],
            [{"id": "discuss", "text": "Дискуссии", "risk": "ok"}, {"id": "people", "text": "Найти новых людей", "risk": "ok"}],
            [{"id": "learn_members", "text": "Узнать об участниках", "risk": "warn"}],
            [{"id": "look", "text": "Посмотреть чат", "risk": "warn"}, {"id": "adult", "text": "18+ общение", "risk": "red"}],
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
            [{"id": "their_problem", "text": "Если человек раскрывает информацию о себе — это его проблема", "risk": "red"}],
            [{"id": "no_anon", "text": "Интернет без анонимности был бы интереснее", "risk": "red"}],
        ],
    },
]


def risk_icon(risk):
    if risk == "ok":
        return "✅"
    if risk == "warn":
        return "⚠️"
    if risk == "red":
        return "❌"
    return "✅"


def find_answer(question_index, answer_id):
    question = QUESTIONNAIRE[question_index]
    for row in question["buttons"]:
        for answer in row:
            if answer["id"] == answer_id:
                return answer
    return None


def user_display(user):
    username = f"@{user.username}" if user.username else "username отсутствует"
    return (
        f"Имя: {user.full_name}\n"
        f"Username: {username}\n"
        f"ID: {user.id}"
    )


def build_faq_blocks():
    blocks = []
    for question, answer in FAQ_ITEMS:
        blocks.append(
            "━━━━━━━━━━━━━━\n"
            f"❓ {question}\n\n"
            f"💬 Ответ: {answer}\n"
            "━━━━━━━━━━━━━━"
        )
    return blocks


FAQ_BLOCKS = build_faq_blocks()


def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 Правила", callback_data="rules")],
        [InlineKeyboardButton("❓ FAQ", callback_data="faq")],
        [InlineKeyboardButton("🛡️ Безопасность", callback_data="safety")],
        [InlineKeyboardButton("📝 Подать заявку", callback_data="apply")]
    ])


def back_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])


def question_keyboard(question_index):
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
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Отправить заявку", callback_data=f"submit_application:{user_id}")],
        [InlineKeyboardButton("🔄 Заполнить заново", callback_data=f"reset_application:{user_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])


def admin_decision_keyboard(user_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Принять", callback_data=f"accept:{user_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject:{user_id}")
        ]
    ])


def split_text(text, max_length=3900):
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
    return (
        "👋 Добро пожаловать в RUABE.\n\n"
        "Мы активный Telegram-чат с живым общением, обсуждениями и сообществом людей из Reddit.\n\n"
        "Перед подачей заявки рекомендуем ознакомиться с информацией ниже."
    )


def get_or_create_session(user_id):
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
    risky = []
    for question in QUESTIONNAIRE:
        qid = question["id"]
        if qid not in session["answers"]:
            continue

        answer_data = session["answers"][qid]
        risk = answer_data["risk"]

        if risk in ("warn", "red"):
            risky.append(
                f"{risk_icon(risk)} {question['question']} — {answer_data['text']}"
            )

    return risky


def add_history_from_current_answers(user_id):
    session = user_sessions.get(user_id)
    if not session:
        return

    risky = collect_risky_answers(session)
    for item in risky:
        if item not in session["history_risky"]:
            session["history_risky"].append(item)


def build_preview_text(user):
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
    session = get_or_create_session(user.id)

    text = (
        "📝 Новая заявка в чат\n\n"
        f"{user_display(user)}\n\n"
    )

    if session["resets"] > 0:
        text += f"🔁 Анкета перезаполнялась: {session['resets']} раз(а)\n"

    if session["history_risky"]:
        text += "\n⚠️ Ранее выбирались подозрительные ответы:\n"
        for item in session["history_risky"]:
            text += f"• {item}\n"
        text += "\n"

    text += "Ответы:\n\n"

    for index, question in enumerate(QUESTIONNAIRE, start=1):
        answer_data = session["answers"].get(question["id"])

        if answer_data:
            answer_text = answer_data["text"]
            risk = answer_data["risk"]
        else:
            answer_text = "нет ответа"
            risk = "warn"

        text += f"{index}. {question['question']}\n"
        text += f"{risk_icon(risk)} {answer_text}\n\n"

    return text


async def safe_callback_answer(query, text=None, show_alert=False):
    try:
        await query.answer(text=text, show_alert=show_alert)
    except Exception:
        pass


async def log_event(context, text):
    try:
        await context.bot.send_message(
            chat_id=LOG_CHAT_ID,
            text=text
        )
    except Exception:
        pass


async def delete_section_messages(context, user_id):
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
    try:
        await query.delete_message()
    except Exception:
        pass


async def send_main_menu(context, user_id):
    await context.bot.send_message(
        chat_id=user_id,
        text=main_menu_text(),
        reply_markup=main_menu()
    )


async def send_section_with_back(query, context, section_text):
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
    user_id = query.from_user.id

    await delete_section_messages(context, user_id)
    await safe_delete_query_message(query)

    sent_ids = []

    header = await context.bot.send_message(
        chat_id=user_id,
        text="❓ FAQ"
    )
    sent_ids.append(header.message_id)

    for index, block in enumerate(FAQ_BLOCKS):
        is_last_block = index == len(FAQ_BLOCKS) - 1

        msg = await context.bot.send_message(
            chat_id=user_id,
            text=block,
            reply_markup=back_button() if is_last_block else None
        )

        sent_ids.append(msg.message_id)

    section_messages[user_id] = sent_ids


def cooldown_remaining(user_id):
    last_submit = application_cooldowns.get(user_id)
    if not last_submit:
        return None

    cooldown_end = last_submit + timedelta(minutes=COOLDOWN_MINUTES)
    now = datetime.now(timezone.utc)

    if now >= cooldown_end:
        return None

    return cooldown_end - now


async def check_can_apply(query, context):
    user_id = query.from_user.id

    if user_id in pending_applications:
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


async def update_admin_application_messages(context, user_id, decision_text):
    base_text = admin_application_texts.get(user_id, "📝 Заявка")
    final_text = (
        f"{base_text}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{decision_text}\n"
        "Подробности смотрите в лог-чате."
    )

    for message_info in admin_application_messages.get(user_id, []):
        try:
            await context.bot.edit_message_text(
                chat_id=message_info["chat_id"],
                message_id=message_info["message_id"],
                text=final_text,
                reply_markup=None
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await delete_section_messages(context, user_id)

    await update.message.reply_text(
        main_menu_text(),
        reply_markup=main_menu()
    )


async def send_question(query, context, user_id):
    session = get_or_create_session(user_id)
    question_index = session["current_step"]
    question = QUESTIONNAIRE[question_index]

    await query.edit_message_text(
        question["question"],
        reply_markup=question_keyboard(question_index)
    )


async def start_application(query, context):
    user_id = query.from_user.id

    can_apply = await check_can_apply(query, context)
    if not can_apply:
        return

    await delete_section_messages(context, user_id)
    start_new_session(user_id)

    await log_event(
        context,
        "🟦 Пользователь начал анкету\n\n"
        f"{user_display(query.from_user)}"
    )

    await send_question(query, context, user_id)


async def handle_answer(query, context):
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
        f"{user_display(query.from_user)}\n"
        f"Количество сбросов: {resets}"
    )

    await send_question(query, context, user_id)


async def submit_application(query, context, user_id):
    if query.from_user.id != user_id:
        await safe_callback_answer(query, "Это не ваша заявка.", show_alert=True)
        return

    if user_id in pending_applications:
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

    pending_applications.add(user_id)
    application_status[user_id] = "pending"
    application_locks[user_id] = asyncio.Lock()
    application_cooldowns[user_id] = datetime.now(timezone.utc)

    application_text = build_application_text(query.from_user)
    admin_application_texts[user_id] = application_text
    admin_application_messages[user_id] = []

    await context.bot.send_message(
        chat_id=LOG_CHAT_ID,
        text="📌 Заявка сохранена в лог:\n\n" + application_text
    )

    await log_event(
        context,
        "🟩 Пользователь отправил заявку\n\n"
        f"{user_display(query.from_user)}"
    )

    for admin_id in ADMIN_IDS:
        try:
            msg = await context.bot.send_message(
                chat_id=admin_id,
                text=application_text,
                reply_markup=admin_decision_keyboard(user_id)
            )

            admin_application_messages[user_id].append({
                "chat_id": admin_id,
                "message_id": msg.message_id
            })
        except Exception as error:
            await log_event(
                context,
                "⚠️ Не удалось отправить заявку администратору\n\n"
                f"Админ ID: {admin_id}\n"
                f"Пользователь ID: {user_id}\n"
                f"Ошибка: {error}"
            )

    await query.edit_message_text(
        "✅ Спасибо! Заявка отправлена администрации.",
        reply_markup=back_button()
    )


async def approve_user(context, user_id):
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
    await context.bot.send_message(
        chat_id=user_id,
        text="Спасибо за заявку. Сейчас мы не можем одобрить вступление в чат."
    )


async def process_admin_decision(query, context, user_id, decision):
    lock = application_locks.setdefault(user_id, asyncio.Lock())

    async with lock:
        current_status = application_status.get(user_id)

        if current_status is None:
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

        await safe_callback_answer(query)

        admin_name = query.from_user.full_name
        admin_id = query.from_user.id

        if decision == "approve":
            try:
                await approve_user(context, user_id)
            except Exception as error:
                await query.edit_message_text(
                    "❌ Не удалось создать или отправить ссылку.\n\n"
                    f"Ошибка: {error}"
                )

                await log_event(
                    context,
                    "⚠️ Ошибка создания или отправки invite-ссылки\n\n"
                    f"Пользователь ID: {user_id}\n"
                    f"Ошибка: {error}"
                )
                return

            application_status[user_id] = "approved"
            pending_applications.discard(user_id)

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

            application_status[user_id] = "rejected"
            pending_applications.discard(user_id)

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

    elif data.startswith("reject:"):
        if query.from_user.id not in ADMIN_IDS:
            await safe_callback_answer(query, "У вас нет прав для этого действия.", show_alert=True)
            return

        target_user_id = int(data.split(":")[1])
        await process_admin_decision(query, context, target_user_id, "reject")

    else:
        await safe_callback_answer(query, "Неизвестное действие.", show_alert=True)


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
    )


if __name__ == "__main__":
    main()