import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from credentials import (
    TELEGRAM_API_HASH,
    TELEGRAM_API_ID,
    TELEGRAM_SESSION_NAME,
)
from scanner_channels import get_enabled_channels
from scanner_real_channels import REAL_CHANNELS
from telegram_connection_test import run_connection_test_async


REPORTS_DIR = Path("reports")
OUTPUT_PATH = REPORTS_DIR / "telegram_real_messages_preview.json"

DEFAULT_LIMIT_PER_CHANNEL = 5
MAX_TEXT_PREVIEW_LENGTH = 500
DEFAULT_MAX_MESSAGE_AGE_HOURS = 48


def truncate_text(text: str, max_length: int = MAX_TEXT_PREVIEW_LENGTH) -> str:
    clean_text = " ".join(str(text).split())

    if len(clean_text) <= max_length:
        return clean_text

    return clean_text[:max_length].rstrip() + "..."


def get_message_created_at(message: Any) -> datetime:
    message_date = getattr(message, "date", None)

    if message_date is None:
        return datetime.now(UTC).replace(tzinfo=None)

    return message_date.replace(tzinfo=None)


def is_message_fresh(
    message: Any,
    now: datetime,
    max_age_hours: int = DEFAULT_MAX_MESSAGE_AGE_HOURS,
) -> bool:
    created_at = get_message_created_at(message)
    max_age = timedelta(hours=int(max_age_hours))

    return created_at >= now - max_age


def build_not_ready_payload(connection_result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source": "telegram_real_messages_preview",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analytical_only": True,
        "orders_enabled": False,
        "trading_enabled": False,
        "binance_scanner_started": False,
        "telegram_connect_attempted": connection_result.get("telegram_connect_attempted", False),
        "telegram_messages_read": False,
        "telegram_channels_read": False,
        "safe_to_continue": False,
        "channels_requested": 0,
        "channels_ok": 0,
        "channels_failed": 0,
        "messages_collected": 0,
        "limit_per_channel": DEFAULT_LIMIT_PER_CHANNEL,
        "max_message_age_hours": DEFAULT_MAX_MESSAGE_AGE_HOURS,
        "skipped_old_messages": 0,
        "skipped_empty_messages": 0,
        "blockers": connection_result.get("blockers", []),
        "warnings": connection_result.get("warnings", []),
        "messages": [],
        "reason": "connection_not_safe_to_continue",
        "disclaimer": (
            "Telegram/social data is analytical only. "
            "This preview does not create orders and does not start trading."
        ),
    }


def build_empty_channels_payload(connection_result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source": "telegram_real_messages_preview",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analytical_only": True,
        "orders_enabled": False,
        "trading_enabled": False,
        "binance_scanner_started": False,
        "telegram_connect_attempted": connection_result.get("telegram_connect_attempted", False),
        "telegram_messages_read": False,
        "telegram_channels_read": False,
        "safe_to_continue": True,
        "channels_requested": 0,
        "channels_ok": 0,
        "channels_failed": 0,
        "messages_collected": 0,
        "limit_per_channel": DEFAULT_LIMIT_PER_CHANNEL,
        "max_message_age_hours": DEFAULT_MAX_MESSAGE_AGE_HOURS,
        "skipped_old_messages": 0,
        "skipped_empty_messages": 0,
        "blockers": [],
        "warnings": ["no_real_channels_configured"],
        "messages": [],
        "reason": "no_real_channels_configured",
        "disclaimer": (
            "Telegram/social data is analytical only. "
            "This preview does not create orders and does not start trading."
        ),
    }


def build_message_item(channel: Dict[str, Any], message: Any) -> Dict[str, Any]:
    message_date = getattr(message, "date", None)

    if message_date is None:
        created_at = datetime.now()
    else:
        created_at = message_date.replace(tzinfo=None)

    raw_text = getattr(message, "message", "") or ""

    return {
        "channel": channel["username"],
        "channel_title": channel.get("title"),
        "message_id": int(getattr(message, "id", 0) or 0),
        "created_at": created_at.isoformat(timespec="seconds"),
        "text": str(raw_text),
        "text_preview": truncate_text(str(raw_text)),
        "views": int(getattr(message, "views", 0) or 0),
        "forwards": int(getattr(message, "forwards", 0) or 0),
        "channel_weight": float(channel.get("weight", 1.0)),
        "authority_score": int(channel.get("authority_score", 50)),
        "demo": False,
    }


async def run_real_messages_preview_async(
    limit_per_channel: int = DEFAULT_LIMIT_PER_CHANNEL,
) -> Dict[str, Any]:
    """
    Safe preview reader for real public Telegram channels.

    Safety rules:
    - reads only channels from scanner_real_channels.py;
    - reads only a small limited batch;
    - does not start trading bot;
    - does not start Binance scanner;
    - does not create orders;
    - saves messages for analytical AI processing only.
    """
    connection_result = await run_connection_test_async()

    if not connection_result.get("safe_to_continue"):
        return build_not_ready_payload(connection_result)

    real_channels = get_enabled_channels(REAL_CHANNELS)

    if not real_channels:
        return build_empty_channels_payload(connection_result)

    from telethon import TelegramClient

    payload: Dict[str, Any] = {
        "source": "telegram_real_messages_preview",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analytical_only": True,
        "orders_enabled": False,
        "trading_enabled": False,
        "binance_scanner_started": False,
        "telegram_connect_attempted": True,
        "telegram_messages_read": False,
        "telegram_channels_read": False,
        "safe_to_continue": True,
        "channels_requested": len(real_channels),
        "channels_ok": 0,
        "channels_failed": 0,
        "messages_collected": 0,
        "limit_per_channel": int(limit_per_channel),
        "max_message_age_hours": DEFAULT_MAX_MESSAGE_AGE_HOURS,
        "skipped_old_messages": 0,
        "skipped_empty_messages": 0,
        "blockers": [],
        "warnings": connection_result.get("warnings", []),
        "messages": [],
        "channel_errors": [],
        "disclaimer": (
            "Telegram/social data is analytical only. "
            "This preview does not create orders and does not start trading."
        ),
    }

    now = datetime.now(UTC).replace(tzinfo=None)

    async with TelegramClient(
        TELEGRAM_SESSION_NAME,
        TELEGRAM_API_ID,
        TELEGRAM_API_HASH,
    ) as client:
        for channel in real_channels:
            username = str(channel.get("username", "")).strip().lstrip("@")

            if not username:
                payload["channels_failed"] += 1
                payload["channel_errors"].append({
                    "username": username,
                    "error": "empty_username",
                })
                continue

            try:
                channel_message_count = 0

                async for message in client.iter_messages(
                    username,
                    limit=int(limit_per_channel),
                ):
                    text = getattr(message, "message", "") or ""

                    if not str(text).strip():
                        payload["skipped_empty_messages"] += 1
                        continue

                    if not is_message_fresh(
                        message,
                        now=now,
                        max_age_hours=DEFAULT_MAX_MESSAGE_AGE_HOURS,
                    ):
                        payload["skipped_old_messages"] += 1
                        continue

                    payload["messages"].append(build_message_item(channel, message))
                    channel_message_count += 1

                payload["channels_ok"] += 1

                if channel_message_count > 0:
                    payload["telegram_messages_read"] = True
                    payload["telegram_channels_read"] = True

            except Exception as ex:
                payload["channels_failed"] += 1
                payload["channel_errors"].append({
                    "username": username,
                    "error": str(ex),
                })

    payload["messages_collected"] = len(payload["messages"])

    return payload


def run_real_messages_preview(
    limit_per_channel: int = DEFAULT_LIMIT_PER_CHANNEL,
) -> Dict[str, Any]:
    return asyncio.run(
        run_real_messages_preview_async(
            limit_per_channel=limit_per_channel,
        )
    )


def save_preview_payload(payload: Dict[str, Any]) -> Path:
    REPORTS_DIR.mkdir(exist_ok=True)

    OUTPUT_PATH.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    return OUTPUT_PATH


def print_preview_summary(payload: Dict[str, Any], output_path: Path) -> None:
    print("TELEGRAM REAL MESSAGES PREVIEW")
    print("==============================")
    print("Mode: analytical only")
    print("Orders enabled:", payload.get("orders_enabled"))
    print("Trading enabled:", payload.get("trading_enabled"))
    print("Binance scanner started:", payload.get("binance_scanner_started"))
    print("Telegram connect attempted:", payload.get("telegram_connect_attempted"))
    print("Telegram messages read:", payload.get("telegram_messages_read"))
    print("Telegram channels read:", payload.get("telegram_channels_read"))
    print("Output file:", output_path)
    print()

    print("SUMMARY")
    print("=======")
    print("Safe to continue:", payload.get("safe_to_continue"))
    print("Channels requested:", payload.get("channels_requested"))
    print("Channels OK:", payload.get("channels_ok"))
    print("Channels failed:", payload.get("channels_failed"))
    print("Messages collected:", payload.get("messages_collected"))
    print("Limit per channel:", payload.get("limit_per_channel"))
    print("Max message age hours:", payload.get("max_message_age_hours"))
    print("Skipped old messages:", payload.get("skipped_old_messages"))
    print("Skipped empty messages:", payload.get("skipped_empty_messages"))

    if payload.get("blockers"):
        print("Blockers:", ", ".join(str(item) for item in payload["blockers"]))
    else:
        print("Blockers: none")

    if payload.get("warnings"):
        print("Warnings:", ", ".join(str(item) for item in payload["warnings"]))
    else:
        print("Warnings: none")

    print()
    print("MESSAGES PREVIEW")
    print("================")

    messages = payload.get("messages", [])

    if not messages:
        print("No messages collected.")
    else:
        for index, message in enumerate(messages[:20], start=1):
            print(
                "#" + str(index),
                str(message.get("channel")).ljust(25),
                str(message.get("created_at")),
                "views=" + str(message.get("views")),
                "forwards=" + str(message.get("forwards")),
                "-",
                message.get("text_preview"),
            )

    if payload.get("channel_errors"):
        print()
        print("CHANNEL ERRORS")
        print("==============")

        for error in payload["channel_errors"]:
            print(
                str(error.get("username")).ljust(25),
                "error=" + str(error.get("error")),
            )

    print()
    print("SAFETY")
    print("======")
    print("[OK] This preview did not create orders.")
    print("[OK] This preview did not start trading bot.")
    print("[OK] This preview did not start Binance market scanner.")
    print("[OK] This preview only reads limited public Telegram messages from configured channels.")

    print()
    print("NEXT STEP")
    print("=========")

    if payload.get("messages_collected", 0) <= 0:
        print("Add one public channel to scanner_real_channels.py, then rerun this preview.")
        return

    print("Messages preview collected.")
    print("Next safe step: pass this JSON into social_signal_engine.py and AI classification.")


def main() -> None:
    payload = run_real_messages_preview()
    output_path = save_preview_payload(payload)
    print_preview_summary(payload, output_path)


if __name__ == "__main__":
    main()
