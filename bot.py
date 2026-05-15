import os
import html
from datetime import datetime, timedelta, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_IDS = [int(x.strip()) for x in os.environ["ADMIN_IDS"].split(",")]
CHAT_LINK = os.environ.get("CHAT_LINK", "temporary")
LOG_CHAT_ID = int(os.environ["LOG_CHAT_ID"])
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
PORT = int(os.environ.get("PORT", 10000))

MAIN_CHAT_ID_RAW = os.environ.get("MAIN_CHAT_ID", "").strip()
MAIN_CHAT_ID = int(MAIN_CHAT_ID_RAW) if MAIN_CHAT_ID_RAW else None

questions = [
    "1/3. Как вы нашли наше сообщество?",
    "2/3. Что вам интересно в чате?",
    "3/3. Готовы ли вы участвовать в общении, а не только читать?"
]

user_answers = {}
section_messages = {}


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


def build_faq_text():
    text = "❓ FAQ\n\n"
    for question, answer in FAQ_ITEMS:
        text += f"❓ {question}\n\n"
        text += f"💬 Ответ: {answer}\n\n"
    return text.strip()


FAQ_TEXT = build_faq_text()


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


def build_application_text(user):
    user_id = user.id
    username = f"@{user.username}" if user.username else "username отсутствует"

    text = (
        "📝 Новая заявка в чат\n\n"
        f"Имя: {user.full_name}\n"
        f"Username: {username}\n"
        f"ID: {user_id}\n\n"
    )

    for i, answer in enumerate(user_answers.get(user_id, []), start=1):
        text += (
            f"{questions[i - 1]}\n"
            f"Ответ: {answer}\n\n"
        )

    return text


def build_preview_text(user):
    text = "📋 Ваша заявка готова к отправке.\n\nПроверьте ответы ниже:\n\n"

    for i, answer in enumerate(user_answers.get(user.id, []), start=1):
        text += (
            f"{questions[i - 1]}\n"
            f"Ответ: {answer}\n\n"
        )

    text += "Если всё верно — отправьте заявку. Если хотите изменить ответы — заполните анкету заново."
    return text


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
    message = await context.bot.send_message(
        chat_id=user_id,
        text=main_menu_text(),
        reply_markup=main_menu()
    )
    return message.message_id


async def send_section_with_back(query, context, section_text, parse_mode=None):
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
            parse_mode=parse_mode,
            reply_markup=back_button() if is_last_part else None
        )

        sent_ids.append(msg.message_id)

    section_messages[user_id] = sent_ids


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await delete_section_messages(context, user_id)

    await update.message.reply_text(
        main_menu_text(),
        reply_markup=main_menu()
    )


async def send_first_question(query, context):
    user_id = query.from_user.id
    user_answers[user_id] = []

    await delete_section_messages(context, user_id)

    await query.edit_message_text(
        "📝 Сейчас будет несколько коротких общих вопросов.\n\n"
        "Ответы увидит только администрация."
    )

    await context.bot.send_message(
        chat_id=user_id,
        text=questions[0]
    )


async def submit_application(query, context, user_id):
    if query.from_user.id != user_id:
        await query.answer("Это не ваша заявка.", show_alert=True)
        return

    if user_id not in user_answers or len(user_answers[user_id]) < len(questions):
        await query.edit_message_text(
            "Заявка не найдена или заполнена не полностью.",
            reply_markup=back_button()
        )
        return

    user = query.from_user
    application_text = build_application_text(user)

    await context.bot.send_message(
        chat_id=LOG_CHAT_ID,
        text="📌 Заявка сохранена в лог:\n\n" + application_text
    )

    for admin_id in ADMIN_IDS:
        await context.bot.send_message(
            chat_id=admin_id,
            text=application_text,
            reply_markup=admin_decision_keyboard(user_id)
        )

    await query.edit_message_text(
        "✅ Спасибо! Заявка отправлена администрации.",
        reply_markup=back_button()
    )


async def approve_user(query, context, user_id):
    if MAIN_CHAT_ID:
        invite = await context.bot.create_chat_invite_link(
            chat_id=MAIN_CHAT_ID,
            name=f"Invite for {user_id}",
            member_limit=1,
            expire_date=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        invite_link = invite.invite_link
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

    await query.edit_message_text(
        "✅ Заявка одобрена. Ссылка отправлена пользователю."
    )

    await context.bot.send_message(
        chat_id=LOG_CHAT_ID,
        text=f"✅ Заявка пользователя ID {user_id} была одобрена."
    )


async def reject_user(query, context, user_id):
    await context.bot.send_message(
        chat_id=user_id,
        text="Спасибо за заявку. Сейчас мы не можем одобрить вступление в чат."
    )

    await query.edit_message_text("❌ Заявка отклонена.")

    await context.bot.send_message(
        chat_id=LOG_CHAT_ID,
        text=f"❌ Заявка пользователя ID {user_id} была отклонена."
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "back":
        await delete_section_messages(context, user_id)
        await safe_delete_query_message(query)
        await send_main_menu(context, user_id)

    elif data == "rules":
        await send_section_with_back(query, context, RULES_TEXT)

    elif data == "faq":
        await send_section_with_back(query, context, FAQ_TEXT)

    elif data == "safety":
        await send_section_with_back(query, context, SAFETY_TEXT)

    elif data == "apply":
        await send_first_question(query, context)

    elif data.startswith("reset_application:"):
        target_user_id = int(data.split(":")[1])

        if query.from_user.id != target_user_id:
            await query.answer("Это не ваша заявка.", show_alert=True)
            return

        await send_first_question(query, context)

    elif data.startswith("submit_application:"):
        target_user_id = int(data.split(":")[1])
        await submit_application(query, context, target_user_id)

    elif data.startswith("accept:"):
        if query.from_user.id not in ADMIN_IDS:
            await query.edit_message_text("У вас нет прав для этого действия.")
            return

        target_user_id = int(data.split(":")[1])

        try:
            await approve_user(query, context, target_user_id)
        except Exception as error:
            await query.edit_message_text(
                "❌ Не удалось создать или отправить ссылку.\n\n"
                f"Ошибка: {error}"
            )

    elif data.startswith("reject:"):
        if query.from_user.id not in ADMIN_IDS:
            await query.edit_message_text("У вас нет прав для этого действия.")
            return

        target_user_id = int(data.split(":")[1])
        await reject_user(query, context, target_user_id)


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    if user_id not in user_answers:
        return

    user_answers[user_id].append(update.message.text)
    step = len(user_answers[user_id])

    if step < len(questions):
        await update.message.reply_text(questions[step])
        return

    await update.message.reply_text(
        build_preview_text(user),
        reply_markup=submit_application_keyboard(user_id)
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
    )


if __name__ == "__main__":
    main()