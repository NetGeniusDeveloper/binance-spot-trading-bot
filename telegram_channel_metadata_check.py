import asyncio
from typing import Any, Dict, List

from credentials import (
    TELEGRAM_API_HASH,
    TELEGRAM_API_ID,
    TELEGRAM_SESSION_NAME,
)
from scanner_channels import get_enabled_channels
from scanner_real_channels import REAL_CHANNELS
from telegram_connection_test import run_connection_test_async


def build_not_ready_result(connection_result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "analytical_only": True,
        "orders_enabled": False,
        "trading_enabled": False,
        "telegram_connect_attempted": connection_result.get("telegram_connect_attempted", False),
        "telegram_messages_read": False,
        "telegram_channel_metadata_read": False,
        "telegram_channels_read": False,
        "safe_to_continue": False,
        "channels_checked": 0,
        "channels_ok": 0,
        "channels_failed": 0,
        "metadata": [],
        "blockers": connection_result.get("blockers", []),
        "warnings": connection_result.get("warnings", []),
        "reason": "connection_not_safe_to_continue",
    }


async def run_channel_metadata_check_async() -> Dict[str, Any]:
    """
    Safe Telegram public channel metadata check.

    Safety rules:
    - does not read messages;
    - does not iterate channel history;
    - does not start scanner;
    - does not start trading bot;
    - does not create orders;
    - reads only public channel entity metadata for configured channels.
    """
    connection_result = await run_connection_test_async()

    if not connection_result.get("safe_to_continue"):
        return build_not_ready_result(connection_result)

    real_channels = get_enabled_channels(REAL_CHANNELS)

    result: Dict[str, Any] = {
        "analytical_only": True,
        "orders_enabled": False,
        "trading_enabled": False,
        "telegram_connect_attempted": True,
        "telegram_messages_read": False,
        "telegram_channel_metadata_read": False,
        "telegram_channels_read": False,
        "safe_to_continue": True,
        "channels_checked": 0,
        "channels_ok": 0,
        "channels_failed": 0,
        "metadata": [],
        "blockers": [],
        "warnings": connection_result.get("warnings", []),
    }

    if not real_channels:
        result["warnings"].append("no_real_channels_configured")
        return result

    from telethon import TelegramClient

    async with TelegramClient(
        TELEGRAM_SESSION_NAME,
        TELEGRAM_API_ID,
        TELEGRAM_API_HASH,
    ) as client:
        for channel in real_channels:
            username = str(channel.get("username", "")).strip().lstrip("@")

            if not username:
                result["channels_failed"] += 1
                result["metadata"].append({
                    "username": username,
                    "ok": False,
                    "error": "empty_username",
                })
                continue

            result["channels_checked"] += 1

            try:
                entity = await client.get_entity(username)

                item = {
                    "username": username,
                    "ok": True,
                    "id": getattr(entity, "id", None),
                    "title": getattr(entity, "title", None),
                    "verified": bool(getattr(entity, "verified", False)),
                    "scam": bool(getattr(entity, "scam", False)),
                    "fake": bool(getattr(entity, "fake", False)),
                    "participants_count": getattr(entity, "participants_count", None),
                    "configured_weight": channel.get("weight"),
                    "configured_authority_score": channel.get("authority_score"),
                }

                result["metadata"].append(item)
                result["channels_ok"] += 1
                result["telegram_channel_metadata_read"] = True

            except Exception as ex:
                result["channels_failed"] += 1
                result["metadata"].append({
                    "username": username,
                    "ok": False,
                    "error": str(ex),
                    "configured_weight": channel.get("weight"),
                    "configured_authority_score": channel.get("authority_score"),
                })

    return result


def run_channel_metadata_check() -> Dict[str, Any]:
    return asyncio.run(run_channel_metadata_check_async())


def print_channel_metadata_result(result: Dict[str, Any]) -> None:
    print("TELEGRAM CHANNEL METADATA CHECK")
    print("===============================")
    print("Mode: analytical only")
    print("Orders enabled:", result["orders_enabled"])
    print("Trading enabled:", result["trading_enabled"])
    print("Telegram connect attempted:", result["telegram_connect_attempted"])
    print("Telegram messages read:", result["telegram_messages_read"])
    print("Telegram channel metadata read:", result["telegram_channel_metadata_read"])
    print("Telegram channels read:", result["telegram_channels_read"])
    print()

    print("SUMMARY")
    print("=======")
    print("Safe to continue:", result["safe_to_continue"])
    print("Channels checked:", result["channels_checked"])
    print("Channels OK:", result["channels_ok"])
    print("Channels failed:", result["channels_failed"])

    if result.get("blockers"):
        print("Blockers:", ", ".join(str(item) for item in result["blockers"]))
    else:
        print("Blockers: none")

    if result.get("warnings"):
        print("Warnings:", ", ".join(str(item) for item in result["warnings"]))
    else:
        print("Warnings: none")

    print()
    print("CHANNEL METADATA")
    print("================")

    metadata = result.get("metadata", [])

    if not metadata:
        print("No channel metadata.")
    else:
        for item in metadata:
            if item.get("ok"):
                print(
                    str(item.get("username")).ljust(28),
                    "ok=True",
                    "title=" + str(item.get("title")),
                    "verified=" + str(item.get("verified")),
                    "scam=" + str(item.get("scam")),
                    "fake=" + str(item.get("fake")),
                    "participants=" + str(item.get("participants_count")),
                    "weight=" + str(item.get("configured_weight")),
                    "authority=" + str(item.get("configured_authority_score")),
                )
            else:
                print(
                    str(item.get("username")).ljust(28),
                    "ok=False",
                    "error=" + str(item.get("error")),
                )

    print()
    print("SAFETY")
    print("======")
    print("[OK] This check did not read Telegram messages.")
    print("[OK] This check did not iterate channel history.")
    print("[OK] This check did not create orders.")
    print("[OK] This check did not start trading bot.")
    print("[OK] This check did not start Binance market scanner.")

    print()
    print("NEXT STEP")
    print("=========")

    if result.get("channels_ok", 0) <= 0:
        print("Add one public channel to scanner_real_channels.py, then rerun this check.")
        return

    print("Channel metadata check passed.")
    print("Next safe step: read a very small limited batch of messages from configured public channels.")


def main() -> None:
    result = run_channel_metadata_check()
    print_channel_metadata_result(result)


if __name__ == "__main__":
    main()
