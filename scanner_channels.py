from typing import Any, Dict, List

from scanner_real_channels import REAL_CHANNELS


# Demo channels are safe local examples.
# They do not connect to Telegram and are used for testing the scanner pipeline.
DEMO_CHANNELS: List[Dict[str, Any]] = [
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


def normalize_channel(channel: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "username": str(channel.get("username", "")).strip().lstrip("@"),
        "title": str(channel.get("title", "")),
        "enabled": bool(channel.get("enabled", True)),
        "weight": float(channel.get("weight", 1.0)),
        "authority_score": int(channel.get("authority_score", 50)),
    }


def get_enabled_channels(channels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        normalize_channel(channel)
        for channel in channels
        if bool(channel.get("enabled", True))
    ]


def get_channel_weight(channel_username: str, channels: List[Dict[str, Any]]) -> float:
    normalized_username = str(channel_username).strip().lstrip("@")

    for channel in channels:
        normalized_channel = normalize_channel(channel)

        if normalized_channel["username"] == normalized_username:
            return float(normalized_channel.get("weight", 1.0))

    return 1.0


def print_channel_list(title: str, channels: List[Dict[str, Any]]) -> None:
    print()
    print(title)
    print("=" * len(title))

    enabled_channels = get_enabled_channels(channels)

    if not enabled_channels:
        if title == "REAL CHANNELS":
            print("No real Telegram channels configured.")
            print("[SAFE] Real collector will not request Telegram channels.")
        else:
            print("No channels configured.")
        return

    for channel in enabled_channels:
        print(
            channel["username"],
            "title=" + channel["title"],
            "weight=" + str(channel["weight"]),
            "authority=" + str(channel["authority_score"]),
        )


def print_channels_report() -> None:
    demo_channels = get_enabled_channels(DEMO_CHANNELS)
    real_channels = get_enabled_channels(REAL_CHANNELS)

    print("SCANNER CHANNELS")
    print("================")
    print("Demo channels:", len(demo_channels))
    print("Real channels:", len(real_channels))
    print("Real config file: scanner_real_channels.py")

    print_channel_list("DEMO CHANNELS", DEMO_CHANNELS)
    print_channel_list("REAL CHANNELS", REAL_CHANNELS)


if __name__ == "__main__":
    print_channels_report()
