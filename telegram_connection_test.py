import asyncio
from typing import Any, Dict

from credentials import (
    TELEGRAM_API_HASH,
    TELEGRAM_API_ID,
    TELEGRAM_SESSION_NAME,
)
from telegram_real_mode_check import check_telegram_real_mode


def build_not_ready_result(readiness: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "analytical_only": True,
        "orders_enabled": False,
        "trading_enabled": False,
        "telegram_connect_attempted": False,
        "telegram_messages_read": False,
        "telegram_channels_read": False,
        "connected": False,
        "authorized": False,
        "safe_to_continue": False,
        "reason": "not_ready_for_credentials_test",
        "blockers": readiness.get("blockers", []),
        "warnings": readiness.get("warnings", []),
    }


async def run_connection_test_async() -> Dict[str, Any]:
    """
    Safe Telegram connection/auth test.

    Safety rules:
    - does not read channels;
    - does not read messages;
    - does not start scanner;
    - does not start trading bot;
    - does not create orders.

    Note:
    On first successful real Telegram login Telethon may create a local
    session file. Session files must stay ignored by Git.
    """
    readiness = check_telegram_real_mode()

    if not readiness.get("ready_for_credentials_test"):
        return build_not_ready_result(readiness)

    from telethon import TelegramClient

    result: Dict[str, Any] = {
        "analytical_only": True,
        "orders_enabled": False,
        "trading_enabled": False,
        "telegram_connect_attempted": True,
        "telegram_messages_read": False,
        "telegram_channels_read": False,
        "connected": False,
        "authorized": False,
        "safe_to_continue": False,
        "session_name": TELEGRAM_SESSION_NAME,
        "blockers": [],
        "warnings": readiness.get("warnings", []),
        "user_id": None,
        "username": None,
        "first_name": None,
    }

    try:
        async with TelegramClient(
            TELEGRAM_SESSION_NAME,
            TELEGRAM_API_ID,
            TELEGRAM_API_HASH,
        ) as client:
            result["connected"] = client.is_connected()

            authorized = await client.is_user_authorized()
            result["authorized"] = bool(authorized)

            if authorized:
                me = await client.get_me()

                result["user_id"] = getattr(me, "id", None)
                result["username"] = getattr(me, "username", None)
                result["first_name"] = getattr(me, "first_name", None)
                result["safe_to_continue"] = True
            else:
                result["blockers"].append("telegram_session_not_authorized")
                result["safe_to_continue"] = False

    except Exception as ex:
        result["connected"] = False
        result["authorized"] = False
        result["safe_to_continue"] = False
        result["blockers"].append("telegram_connection_error")
        result["error"] = str(ex)

    return result


def run_connection_test() -> Dict[str, Any]:
    return asyncio.run(run_connection_test_async())


def print_connection_result(result: Dict[str, Any]) -> None:
    print("TELEGRAM CONNECTION TEST")
    print("========================")
    print("Mode: analytical only")
    print("Orders enabled:", result["orders_enabled"])
    print("Trading enabled:", result["trading_enabled"])
    print("Telegram connect attempted:", result["telegram_connect_attempted"])
    print("Telegram messages read:", result["telegram_messages_read"])
    print("Telegram channels read:", result["telegram_channels_read"])
    print()

    print("CONNECTION")
    print("==========")
    print("Connected:", result["connected"])
    print("Authorized:", result["authorized"])
    print("Session name:", result.get("session_name"))
    print("Safe to continue:", result["safe_to_continue"])

    if result.get("user_id"):
        print("User id:", result.get("user_id"))

    if result.get("username"):
        print("Username:", result.get("username"))

    if result.get("first_name"):
        print("First name:", result.get("first_name"))

    if result.get("blockers"):
        print("Blockers:", ", ".join(str(item) for item in result["blockers"]))
    else:
        print("Blockers: none")

    if result.get("warnings"):
        print("Warnings:", ", ".join(str(item) for item in result["warnings"]))
    else:
        print("Warnings: none")

    if result.get("error"):
        print("Error:", result["error"])

    print()
    print("SAFETY")
    print("======")
    print("[OK] This test did not read Telegram channels.")
    print("[OK] This test did not read Telegram messages.")
    print("[OK] This test did not create orders.")
    print("[OK] This test did not start trading bot.")
    print("[OK] This test did not start Binance market scanner.")

    print()
    print("NEXT STEP")
    print("=========")

    if not result["telegram_connect_attempted"]:
        print("Add TELEGRAM_API_ID and TELEGRAM_API_HASH to .env first.")
        return

    if not result["authorized"]:
        print("Authorize the Telegram session when you are ready.")
        print("After authorization, rerun this test.")
        return

    print("Telegram session is authorized.")
    print("Next safe step: test reading only channel metadata, not messages.")


def main() -> None:
    result = run_connection_test()
    print_connection_result(result)


if __name__ == "__main__":
    main()
