import os

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
