from telegram import Update
from telegram.ext import ContextTypes

from .blacklist import handle_admin_text
from .contact import handle_admin_contact_reply, handle_user_contact_message


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Распределяет текстовые сообщения между пользовательскими и админскими режимами."""
    handled = await handle_admin_contact_reply(update, context)

    if handled:
        return

    handled = await handle_user_contact_message(update, context)

    if handled:
        return

    await handle_admin_text(update, context)
