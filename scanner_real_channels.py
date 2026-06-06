from typing import Any, Dict, List


# Real public Telegram channels for analytical social scanner.
#
# Keep this list empty by default to avoid accidental Telegram requests.
# Add only public channels that you are allowed to read.
#
# Safety:
# - analytical only;
# - no orders;
# - no trading bot launch;
# - no private-channel bypassing.
#
# Example:
# REAL_CHANNELS = [
#     {
#         "username": "some_public_channel",
#         "title": "Some Public Channel",
#         "enabled": True,
#         "weight": 1.0,
#         "authority_score": 70,
#     },
# ]

REAL_CHANNELS: List[Dict[str, Any]] = []
