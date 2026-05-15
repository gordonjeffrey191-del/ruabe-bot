import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
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


# ---------- ГЛАВНОЕ МЕНЮ ----------

def main_menu():
    keyboard = [
        [InlineKeyboardButton("📜 Правила", callback_data="rules")],
        [InlineKeyboardButton("❓ FAQ", callback_data="faq")],
        [InlineKeyboardButton("🛡️ Безопасность", callback_data="safety")],
        [],
        [InlineKeyboardButton("📝 Подать заявку", callback_data="apply")]
    ]

    return InlineKeyboardMarkup(keyboard)


def back_button():
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ]

    return InlineKeyboardMarkup(keyboard)


# ---------- START ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Добро пожаловать в RUABE.\n\n"
        "Перед подачей заявки рекомендуем ознакомиться с информацией ниже."
    )

    await update.message.reply_text(
        text,
        reply_markup=main_menu()
    )


# ---------- КНОПКИ ----------

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    # ГЛАВНОЕ МЕНЮ
    if data == "back":
        await query.edit_message_text(
            "Добро пожаловать в RUABE.\n\n"
            "Перед подачей заявки рекомендуем ознакомиться с информацией ниже.",
            reply_markup=main_menu()
        )

    # ПРАВИЛА
    elif data == "rules":
        await query.edit_message_text(
            "📜 Правила\n\n"
            "Текст правил будет добавлен позже.",
            reply_markup=back_button()
        )

    # FAQ
    elif data == "faq":
        await query.edit_message_text(
            "❓ FAQ\n\n"
            "Ответы на частые вопросы будут добавлены позже.",
            reply_markup=back_button()
        )

    # БЕЗОПАСНОСТЬ
    elif data == "safety":
        await query.edit_message_text(
            "🛡️ Безопасность\n\n"
            "Рекомендации по безопасности будут добавлены позже.",
            reply_markup=back_button()
        )

    # ПОДАТЬ ЗАЯВКУ
    elif data == "apply":
        user_id = query.from_user.id
        user_answers[user_id] = []

        await query.edit_message_text(
            "Сейчас будет несколько коротких общих вопросов.\n"
            "Ответы увидит только администрация."
        )

        await context.bot.send_message(
            chat_id=user_id,
            text=questions[0]
        )

    # ОДОБРЕНИЕ
    elif data.startswith("accept:"):
        if query.from_user.id not in ADMIN_IDS:
            await query.edit_message_text("У вас нет прав для этого действия.")
            return

        user_id = int(data.split(":")[1])

        await context.bot.send_message(
            chat_id=user_id,
            text=f"Ваша заявка одобрена ✅\n\nСсылка на чат:\n{CHAT_LINK}"
        )

        await query.edit_message_text(
            "✅ Заявка одобрена. Ссылка отправлена пользователю."
        )

        await context.bot.send_message(
            chat_id=LOG_CHAT_ID,
            text=f"✅ Заявка пользователя ID {user_id} была одобрена."
        )

    # ОТКЛОНЕНИЕ
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


# ---------- АНКЕТА ----------

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

    username = (
        f"@{user.username}"
        if user.username
        else "username отсутствует"
    )

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
            InlineKeyboardButton(
                "✅ Принять",
                callback_data=f"accept:{user_id}"
            ),
            InlineKeyboardButton(
                "❌ Отклонить",
                callback_data=f"reject:{user_id}"
            )
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
        "Спасибо! Заявка отправлена администрации."
    )


# ---------- ЗАПУСК ----------

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
