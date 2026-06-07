from typing import Any, Dict, List


# Real public Telegram channels for analytical social scanner.
#
# Add only public channels that you are allowed to read.
#
# Safety:
# - analytical only;
# - no orders;
# - no trading bot launch;
# - no private-channel bypassing.
#
# Notes:
# - Channels below were selected by telegram_channel_selection_export.py
#   after manual review of reports/telegram_channel_selection_export.txt.
# - watcherGuru is not enabled yet because discovery classified it as watch_candidate.


REAL_CHANNELS: List[Dict[str, Any]] = [
    {
        "username": "test_binance_channell",
        "title": "Test Binance Channel",
        "enabled": True,
        "weight": 1.0,
        "authority_score": 60,
    },
    {
        "username": "binance_announcements",
        "title": "Binance Announcements",
        "enabled": True,
        "weight": 1.5,
        "authority_score": 90,
    },
    {
        "username": "whale_alert",
        "title": "Whale Alert",
        "enabled": True,
        "weight": 1.3,
        "authority_score": 80,
    },
    {
        "username": "cointelegraph",
        "title": "Cointelegraph",
        "enabled": True,
        "weight": 1.15,
        "authority_score": 70,
    },
]
