from os import getenv

from dotenv import load_dotenv


load_dotenv()


def get_int_env(name: str):
    value = getenv(name)

    if value is None or str(value).strip() == "":
        return None

    try:
        return int(value)
    except ValueError:
        return None


BINANCE_API_KEY = getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = getenv("BINANCE_SECRET_KEY")

# Existing Telegram bot token used by telegram_message_sender.py
TELEGRAM_API_KEY = getenv("TELEGRAM_API_KEY")

# Telegram Client API credentials for analytical social scanner.
# These are NOT Telegram Bot API credentials.
TELEGRAM_API_ID = get_int_env("TELEGRAM_API_ID")
TELEGRAM_API_HASH = getenv("TELEGRAM_API_HASH")
TELEGRAM_SESSION_NAME = getenv("TELEGRAM_SESSION_NAME", "crypto_scanner_session")

# Optional future alert chat id.
TELEGRAM_ALERT_CHAT_ID = getenv("TELEGRAM_ALERT_CHAT_ID")
