from typing import Any, Dict, List


# Real public Telegram channels for analytical social scanner.
#
# Generated recommendation preview.
# Review manually before replacing scanner_real_channels.py.
#
# Safety:
# - analytical only;
# - no orders;
# - no trading bot launch;
# - no private-channel bypassing.


REAL_CHANNELS: List[Dict[str, Any]] = [
    {
        "username": "test_binance_channell",
        "title": "Test Binance Channel",
        "enabled": True,
        "weight": 1.0,
        "authority_score": 60,
        # final_recommendation=keep
        # reason=channel_quality_is_good
    },
    {
        "username": "binance_announcements",
        "title": "Binance Announcements",
        "enabled": False,
        "weight": 0.3,
        "authority_score": 40,
        # final_recommendation=disable
        # reason=channel_quality_is_too_low_or_stale
    },
    {
        "username": "whale_alert",
        "title": "Whale Alert",
        "enabled": False,
        "weight": 0.3,
        "authority_score": 40,
        # final_recommendation=disable
        # reason=channel_has_no_usable_recent_messages_in_quality_report
    },
    {
        "username": "cointelegraph",
        "title": "Cointelegraph",
        "enabled": True,
        "weight": 0.9,
        "authority_score": 60,
        # final_recommendation=watch
        # reason=channel_is_useful_but_should_have_lower_weight
    },
]
