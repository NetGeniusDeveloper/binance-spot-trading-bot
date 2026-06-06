import asyncio
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


# Real public channels can be added later.
# Keep this list empty by default to avoid accidental Telegram requests.
DEFAULT_REAL_CHANNELS: List[Dict[str, Any]] = []


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


def get_channel_weight(channel_username: str, channels: List[Dict[str, Any]]) -> float:
    for channel in channels:
        if channel.get("username") == channel_username:
            return float(channel.get("weight", 1.0))

    return 1.0


def get_demo_channel_weight(channel_username: str) -> float:
    return get_channel_weight(channel_username, DEFAULT_DEMO_CHANNELS)


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


def normalize_real_channel(channel: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "username": str(channel.get("username", "")).strip().lstrip("@"),
        "title": str(channel.get("title", "")),
        "enabled": bool(channel.get("enabled", True)),
        "weight": float(channel.get("weight", 1.0)),
        "authority_score": int(channel.get("authority_score", 50)),
    }


def build_real_message(
    channel: Dict[str, Any],
    message: Any,
) -> Dict[str, Any]:
    message_date = getattr(message, "date", None)

    if message_date is None:
        created_at = datetime.now()
    else:
        created_at = message_date.replace(tzinfo=None)

    text = getattr(message, "message", "") or ""
    views = getattr(message, "views", 0) or 0
    forwards = getattr(message, "forwards", 0) or 0

    return {
        "channel": channel["username"],
        "message_id": int(getattr(message, "id", 0) or 0),
        "created_at": created_at.isoformat(timespec="seconds"),
        "text": str(text),
        "views": int(views),
        "forwards": int(forwards),
        "channel_weight": float(channel.get("weight", 1.0)),
        "demo": False,
    }


async def collect_public_channel_messages(
    channels: List[Dict[str, Any]] | None = None,
    limit_per_channel: int = 50,
) -> List[Dict[str, Any]]:
    """
    Collect recent messages from public Telegram channels through Telethon.

    Safety rules:
    - analytical only;
    - no orders;
    - no private-channel bypassing;
    - disabled channels are skipped;
    - unavailable channels are skipped with a warning;
    - if Telethon or credentials are missing, returns an empty list.
    """
    status = get_collector_status()

    if not status["ready"]:
        print("[SAFE] Telegram collector is not ready:", ", ".join(status["reasons"]) or "unknown")
        return []

    if channels is None:
        channels = DEFAULT_REAL_CHANNELS

    normalized_channels = [
        normalize_real_channel(channel)
        for channel in channels
        if bool(channel.get("enabled", True))
    ]

    if not normalized_channels:
        print("[SAFE] No real Telegram channels configured.")
        return []

    from telethon import TelegramClient

    messages: List[Dict[str, Any]] = []

    async with TelegramClient(
        TELEGRAM_SESSION_NAME,
        TELEGRAM_API_ID,
        TELEGRAM_API_HASH,
    ) as client:
        for channel in normalized_channels:
            username = channel["username"]

            if not username:
                continue

            try:
                async for message in client.iter_messages(
                    username,
                    limit=int(limit_per_channel),
                ):
                    text = getattr(message, "message", "") or ""

                    if not text.strip():
                        continue

                    messages.append(build_real_message(channel, message))

            except Exception as ex:
                print("[WARN] Skip channel", username + ":", ex)

    return messages


def collect_public_channel_messages_sync(
    channels: List[Dict[str, Any]] | None = None,
    limit_per_channel: int = 50,
) -> List[Dict[str, Any]]:
    return asyncio.run(
        collect_public_channel_messages(
            channels=channels,
            limit_per_channel=limit_per_channel,
        )
    )


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
        print("[OK] Telegram collector can be connected.")
        print("[SAFE] It will still collect analytics only and will not create orders.")
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
    print("REAL MODE CHECK")
    print("===============")

    if status["ready"]:
        print("[OK] Real mode credentials are configured.")
        print("[SAFE] Add public channels to DEFAULT_REAL_CHANNELS or a future config file.")
    else:
        print("[SAFE] Real mode is not active.")

    print()
    print("DISCLAIMER")
    print("==========")
    print("Telegram/social signal is not a trading entry.")
    print("This collector is analytical only.")
    print("No orders are created.")
    print("Only public channels should be used in real mode.")


if __name__ == "__main__":
    main()
