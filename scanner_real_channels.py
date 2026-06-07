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
# Channel username is taken from:
# https://t.me/test_binance_channell

REAL_CHANNELS: List[Dict[str, Any]] = [
    {
        "username": "test_binance_channell",
        "title": "Test Binance Channel",
        "enabled": True,
        "weight": 1.0,
        "authority_score": 60,
    },
]
