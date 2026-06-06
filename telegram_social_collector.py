import importlib.util
from datetime import datetime
from typing import Any, Dict, List

from credentials import (
    TELEGRAM_API_HASH,
    TELEGRAM_API_ID,
    TELEGRAM_SESSION_NAME,
)


DEFAULT_DEMO_CHANNELS = [
    {
        "username": "example_crypto_news",
        "title": "Example Crypto News",
        "enabled": True,
        "weight": 1.5,
        "authority_score": 80,
    },
    {
        "username": "example_trading_alpha",
        "title": "Example Trading Alpha",
        "enabled": True,
        "weight": 1.2,
        "authority_score": 70,
    },
]


def is_telethon_installed() -> bool:
    return importlib.util.find_spec("telethon") is not None


def has_telegram_client_credentials() -> bool:
    return bool(TELEGRAM_API_ID and TELEGRAM_API_HASH)


def get_collector_status() -> Dict[str, Any]:
    """
    Return safe Telegram collector status.

    This does not connect to Telegram unless credentials and Telethon are available.
    It does not read private channels.
    It does not create orders.
    """
    telethon_installed = is_telethon_installed()
    credentials_ready = has_telegram_client_credentials()

    ready = telethon_installed and credentials_ready

    reasons: List[str] = []

    if not telethon_installed:
        reasons.append("telethon_not_installed")

    if TELEGRAM_API_ID is None:
        reasons.append("telegram_api_id_missing_or_invalid")

    if not TELEGRAM_API_HASH:
        reasons.append("telegram_api_hash_missing")

    return {
        "ready": ready,
        "analytical_only": True,
        "orders_enabled": False,
        "telethon_installed": telethon_installed,
        "credentials_ready": credentials_ready,
        "telegram_api_id_exists": TELEGRAM_API_ID is not None,
        "telegram_api_hash_exists": bool(TELEGRAM_API_HASH),
        "session_name": TELEGRAM_SESSION_NAME,
        "reasons": reasons,
    }


def build_demo_collector_messages(now: datetime | None = None) -> List[Dict[str, Any]]:
    """
    Build demo Telegram-like messages.

    This is used when real Telegram Client API credentials are not configured.
    """
    if now is None:
        now = datetime.now()

    return [
        {
            "channel": "example_crypto_news",
            "message_id": 1,
            "created_at": now.isoformat(timespec="seconds"),
            "text": "SOL breakout after accumulation and volume growth",
            "views": 1200,
            "forwards": 15,
            "demo": True,
        },
        {
            "channel": "example_trading_alpha",
            "message_id": 2,
            "created_at": now.isoformat(timespec="seconds"),
            "text": "TON/USDT is moving, but wait for retest",
            "views": 900,
            "forwards": 8,
            "demo": True,
        },
        {
            "channel": "example_crypto_news",
            "message_id": 3,
            "created_at": now.isoformat(timespec="seconds"),
            "text": "Urgent buy now 100x moon guaranteed pump",
            "views": 500,
            "forwards": 50,
            "demo": True,
        },
    ]


def print_collector_status(status: Dict[str, Any]) -> None:
    print("TELEGRAM SOCIAL COLLECTOR")
    print("=========================")
    print("Mode: analytical only")
    print("Orders enabled:", status["orders_enabled"])
    print("Ready:", status["ready"])
    print("Telethon installed:", status["telethon_installed"])
    print("Credentials ready:", status["credentials_ready"])
    print("TELEGRAM_API_ID exists:", status["telegram_api_id_exists"])
    print("TELEGRAM_API_HASH exists:", status["telegram_api_hash_exists"])
    print("Session name:", status["session_name"])

    if status["reasons"]:
        print("Reasons:", ", ".join(status["reasons"]))
    else:
        print("Reasons: none")

    print()

    if status["ready"]:
        print("[OK] Telegram collector can be connected in a future step.")
    else:
        print("[SAFE] Telegram collector is not connected.")
        print("[SAFE] Demo mode can be used until Telegram Client API credentials are configured.")
        print()
        print("Required .env fields for real Telegram Client API:")
        print("TELEGRAM_API_ID=")
        print("TELEGRAM_API_HASH=")
        print("TELEGRAM_SESSION_NAME=crypto_scanner_session")


def main() -> None:
    status = get_collector_status()
    print_collector_status(status)

    print()
    print("DEMO MESSAGES")
    print("=============")

    demo_messages = build_demo_collector_messages()

    for message in demo_messages:
        print(
            "#" + str(message["message_id"]),
            message["channel"],
            message["created_at"],
            "-",
            message["text"],
        )

    print()
    print("DISCLAIMER")
    print("==========")
    print("Telegram/social signal is not a trading entry.")
    print("This collector is analytical only.")
    print("No orders are created.")
    print("Only public channels should be used in real mode.")


if __name__ == "__main__":
    main()
