from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from .config import BOT_TOKEN, PORT, WEBHOOK_URL
from .database import init_db
from .decisions import handle_admin_rejection_reason
from .handlers import buttons
from .menus import start

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



