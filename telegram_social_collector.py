import importlib.util
from datetime import datetime, timedelta
from typing import Any, Dict, List

from credentials import (
    TELEGRAM_API_HASH,
    TELEGRAM_API_ID,
    TELEGRAM_SESSION_NAME,
)


DEFAULT_DEMO_CHANNELS = [
    {
        "username": "crypto_news_alpha",
        "title": "Crypto News Alpha",
        "enabled": True,
        "weight": 1.5,
        "authority_score": 80,
    },
    {
        "username": "market_watch",
        "title": "Market Watch",
        "enabled": True,
        "weight": 1.2,
        "authority_score": 70,
    },
    {
        "username": "trading_notes",
        "title": "Trading Notes",
        "enabled": True,
        "weight": 1.1,
        "authority_score": 65,
    },
    {
        "username": "old_news",
        "title": "Old News",
        "enabled": True,
        "weight": 1.0,
        "authority_score": 50,
    },
    {
        "username": "low_quality_pump",
        "title": "Low Quality Pump",
        "enabled": True,
        "weight": 0.2,
        "authority_score": 10,
    },
    {
        "username": "altcoin_watch",
        "title": "Altcoin Watch",
        "enabled": True,
        "weight": 1.0,
        "authority_score": 55,
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


def get_demo_channel_weight(channel_username: str) -> float:
    for channel in DEFAULT_DEMO_CHANNELS:
        if channel["username"] == channel_username:
            return float(channel.get("weight", 1.0))

    return 1.0


def build_demo_message(
    message_id: int,
    channel: str,
    text: str,
    created_at: datetime,
    views: int = 0,
    forwards: int = 0,
) -> Dict[str, Any]:
    return {
        "channel": channel,
        "message_id": message_id,
        "created_at": created_at.isoformat(timespec="seconds"),
        "text": text,
        "views": views,
        "forwards": forwards,
        "channel_weight": get_demo_channel_weight(channel),
        "demo": True,
    }


def build_demo_collector_messages(now: datetime | None = None) -> List[Dict[str, Any]]:
    """
    Build demo Telegram-like messages.

    This is used when real Telegram Client API credentials are not configured.
    It is the safe demo source for social_signal_engine.py.
    """
    if now is None:
        now = datetime.now()

    return [
        build_demo_message(
            message_id=1,
            channel="crypto_news_alpha",
            text="$TON volume is rising after ecosystem update",
            created_at=now - timedelta(minutes=3),
            views=1200,
            forwards=15,
        ),
        build_demo_message(
            message_id=2,
            channel="market_watch",
            text="TON/USDT showing strong mentions today",
            created_at=now - timedelta(minutes=7),
            views=900,
            forwards=8,
        ),
        build_demo_message(
            message_id=3,
            channel="trading_notes",
            text="#TON breakout discussion is growing",
            created_at=now - timedelta(minutes=12),
            views=750,
            forwards=6,
        ),
        build_demo_message(
            message_id=4,
            channel="old_news",
            text="Toncoin was quiet earlier",
            created_at=now - timedelta(minutes=45),
            views=400,
            forwards=2,
        ),
        build_demo_message(
            message_id=5,
            channel="crypto_news_alpha",
            text="Bitcoin and Ethereum are still under pressure",
            created_at=now - timedelta(minutes=10),
            views=1800,
            forwards=20,
        ),
        build_demo_message(
            message_id=6,
            channel="low_quality_pump",
            text="urgent 100x moon guaranteed buy now",
            created_at=now - timedelta(minutes=5),
            views=500,
            forwards=50,
        ),
        build_demo_message(
            message_id=7,
            channel="altcoin_watch",
            text="LINKUSDT volume is rising slowly",
            created_at=now - timedelta(hours=2),
            views=600,
            forwards=3,
        ),
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
            "weight=" + str(message["channel_weight"]),
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
