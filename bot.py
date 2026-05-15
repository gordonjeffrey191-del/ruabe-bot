import os
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
ADMIN_IDS = [int(x) for x in os.environ["ADMIN_IDS"].split(",")]
CHAT_LINK = os.environ["CHAT_LINK"]
LOG_CHAT_ID = int(os.environ["LOG_CHAT_ID"])
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
PORT = int(os.environ.get("PORT", 10000))

questions = [
    "1/3. Как вы нашли наше сообщество?",
    "2/3. Что вам интересно в чате?",
    "3/3. Готовы ли вы участвовать в общении, а не только читать?"
]

user_answers = {}

RULES_TEXT = """📜 Правила чата

1. В чате могут находиться только лица старше 16 лет.
Участие в подчатах «Познакомимся?» и «Вопросы 18+» разрешено только с 18 лет. Если пользователь скрывает или указывает недостоверный возраст, администрация не несёт за это ответственности.

2. Запрещено использовать языки, кроме русского, украинского и белорусского, в качестве основных.
Наказание: устное предупреждение при первом нарушении. При продолжении — предупреждение на неделю и мут на 30 минут. Длительное игнорирование требования — бан.

3. Запрещена публикация порнографии, шок-контента, а также политических, военных и религиозных символов или намёков на них.
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


def main_menu():
    keyboard = [
        [InlineKeyboardButton("📜 Правила", callback_data="rules")],
        [InlineKeyboardButton("❓ FAQ", callback_data="faq")],
        [InlineKeyboardButton("🛡️ Безопасность", callback_data="safety")],
        [InlineKeyboardButton("📝 Подать заявку", callback_data="apply")]
    ]
    return InlineKeyboardMarkup(keyboard)


def back_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 Добро пожаловать в RUABE.\n\n"
        "Мы активный Telegram-чат с живым общением, обсуждениями и сообществом людей из Reddit.\n\n"
        "Перед подачей заявки рекомендуем ознакомиться с информацией ниже."
    )

    await update.message.reply_text(text, reply_markup=main_menu())


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "back":
        await query.edit_message_text(
            "👋 Добро пожаловать в RUABE.\n\n"
            "Мы активный Telegram-чат с живым общением, обсуждениями и сообществом людей из Reddit.\n\n"
            "Перед подачей заявки рекомендуем ознакомиться с информацией ниже.",
            reply_markup=main_menu()
        )

    elif data == "rules":
        await query.edit_message_text(
            "📜 Правила отправлены ниже.",
            reply_markup=back_button()
        )

        for part in split_text(RULES_TEXT):
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text=part
            )

    elif data == "faq":
        await query.edit_message_text(
            "❓ FAQ\n\n"
            "Ответы на частые вопросы будут добавлены позже.",
            reply_markup=back_button()
        )

    elif data == "safety":
        await query.edit_message_text(
            "🛡️ Безопасность\n\n"
            "Рекомендации по безопасности будут добавлены позже.",
            reply_markup=back_button()
        )

    elif data == "apply":
        user_id = query.from_user.id
        user_answers[user_id] = []

        await query.edit_message_text(
            "📝 Сейчас будет несколько коротких общих вопросов.\n\n"
            "Ответы увидит только администрация."
        )

        await context.bot.send_message(
            chat_id=user_id,
            text=questions[0]
        )

    elif data.startswith("accept:"):
        if query.from_user.id not in ADMIN_IDS:
            await query.edit_message_text("У вас нет прав для этого действия.")
            return

        user_id = int(data.split(":")[1])

        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ Ваша заявка одобрена.\n\nСсылка на чат:\n{CHAT_LINK}"
        )

        await query.edit_message_text(
            "✅ Заявка одобрена. Ссылка отправлена пользователю."
        )

        await context.bot.send_message(
            chat_id=LOG_CHAT_ID,
            text=f"✅ Заявка пользователя ID {user_id} была одобрена."
        )

    elif data.startswith("reject:"):
        if query.from_user.id not in ADMIN_IDS:
            await query.edit_message_text("У вас нет прав для этого действия.")
            return

        user_id = int(data.split(":")[1])

        await context.bot.send_message(
            chat_id=user_id,
            text="Спасибо за заявку. Сейчас мы не можем одобрить вступление в чат."
        )

        await query.edit_message_text("❌ Заявка отклонена.")

        await context.bot.send_message(
            chat_id=LOG_CHAT_ID,
            text=f"❌ Заявка пользователя ID {user_id} была отклонена."
        )


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

    username = f"@{user.username}" if user.username else "username отсутствует"

    text = (
        "📝 Новая заявка в чат\n\n"
        f"Имя: {user.full_name}\n"
        f"Username: {username}\n"
        f"ID: {user_id}\n\n"
    )

    for i, answer in enumerate(user_answers[user_id], start=1):
        text += (
            f"{questions[i - 1]}\n"
            f"Ответ: {answer}\n\n"
        )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Принять", callback_data=f"accept:{user_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject:{user_id}")
        ]
    ])

    await context.bot.send_message(
        chat_id=LOG_CHAT_ID,
        text="📌 Заявка сохранена в лог:\n\n" + text
    )

    for admin_id in ADMIN_IDS:
        await context.bot.send_message(
            chat_id=admin_id,
            text=text,
            reply_markup=keyboard
        )

    await update.message.reply_text(
        "✅ Спасибо! Заявка отправлена администрации."
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
    