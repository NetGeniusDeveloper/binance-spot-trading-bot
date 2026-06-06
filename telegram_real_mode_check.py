import importlib.util
from typing import Any, Dict, List

from credentials import (
    TELEGRAM_API_HASH,
    TELEGRAM_API_ID,
    TELEGRAM_SESSION_NAME,
)
from scanner_channels import get_enabled_channels
from scanner_real_channels import REAL_CHANNELS


def is_telethon_installed() -> bool:
    return importlib.util.find_spec("telethon") is not None


def check_telegram_real_mode() -> Dict[str, Any]:
    """
    Safe readiness check for real Telegram collector mode.

    This file does not connect to Telegram.
    It does not read channels.
    It does not start Binance scanner.
    It does not create orders.
    """
    telethon_installed = is_telethon_installed()
    api_id_ready = TELEGRAM_API_ID is not None
    api_hash_ready = bool(TELEGRAM_API_HASH)
    session_name_ready = bool(TELEGRAM_SESSION_NAME)

    enabled_real_channels = get_enabled_channels(REAL_CHANNELS)
    real_channels_ready = len(enabled_real_channels) > 0

    blockers: List[str] = []
    warnings: List[str] = []

    if not telethon_installed:
        blockers.append("telethon_not_installed")

    if not api_id_ready:
        blockers.append("telegram_api_id_missing_or_invalid")

    if not api_hash_ready:
        blockers.append("telegram_api_hash_missing")

    if not session_name_ready:
        blockers.append("telegram_session_name_missing")

    if not real_channels_ready:
        warnings.append("no_real_channels_configured")

    ready_for_real_connection_test = (
        telethon_installed
        and api_id_ready
        and api_hash_ready
        and session_name_ready
        and real_channels_ready
    )

    ready_for_credentials_test = (
        telethon_installed
        and api_id_ready
        and api_hash_ready
        and session_name_ready
    )

    return {
        "analytical_only": True,
        "orders_enabled": False,
        "trading_enabled": False,
        "telegram_connect_attempted": False,
        "telegram_messages_read": False,
        "telethon_installed": telethon_installed,
        "telegram_api_id_ready": api_id_ready,
        "telegram_api_hash_ready": api_hash_ready,
        "telegram_session_name_ready": session_name_ready,
        "telegram_session_name": TELEGRAM_SESSION_NAME,
        "real_channels_count": len(enabled_real_channels),
        "real_channels_ready": real_channels_ready,
        "ready_for_credentials_test": ready_for_credentials_test,
        "ready_for_real_connection_test": ready_for_real_connection_test,
        "blockers": blockers,
        "warnings": warnings,
        "real_channels": enabled_real_channels,
    }


def print_real_channels(channels: List[Dict[str, Any]]) -> None:
    print()
    print("REAL CHANNELS")
    print("=============")

    if not channels:
        print("No enabled real Telegram channels configured.")
        print("[SAFE] Real collector will not request Telegram channels.")
        return

    for channel in channels:
        print(
            channel["username"],
            "title=" + channel["title"],
            "weight=" + str(channel["weight"]),
            "authority=" + str(channel["authority_score"]),
        )


def print_check_result(result: Dict[str, Any]) -> None:
    print("TELEGRAM REAL MODE CHECK")
    print("========================")
    print("Mode: analytical only")
    print("Orders enabled:", result["orders_enabled"])
    print("Trading enabled:", result["trading_enabled"])
    print("Telegram connect attempted:", result["telegram_connect_attempted"])
    print("Telegram messages read:", result["telegram_messages_read"])
    print()

    print("DEPENDENCIES")
    print("============")
    print("Telethon installed:", result["telethon_installed"])
    print()

    print("CREDENTIALS")
    print("===========")
    print("TELEGRAM_API_ID ready:", result["telegram_api_id_ready"])
    print("TELEGRAM_API_HASH ready:", result["telegram_api_hash_ready"])
    print("TELEGRAM_SESSION_NAME ready:", result["telegram_session_name_ready"])
    print("Session name:", result["telegram_session_name"])
    print()

    print("READINESS")
    print("=========")
    print("Ready for credentials test:", result["ready_for_credentials_test"])
    print("Ready for real connection test:", result["ready_for_real_connection_test"])
    print("Real channels count:", result["real_channels_count"])

    if result["blockers"]:
        print("Blockers:", ", ".join(result["blockers"]))
    else:
        print("Blockers: none")

    if result["warnings"]:
        print("Warnings:", ", ".join(result["warnings"]))
    else:
        print("Warnings: none")

    print_real_channels(result["real_channels"])

    print()
    print("SAFETY")
    print("======")
    print("[OK] This check did not connect to Telegram.")
    print("[OK] This check did not read Telegram messages.")
    print("[OK] This check did not create orders.")
    print("[OK] This check did not start trading bot.")
    print("[OK] This check did not start Binance market scanner.")

    print()
    print("NEXT STEP")
    print("=========")

    if not result["ready_for_credentials_test"]:
        print("Add TELEGRAM_API_ID and TELEGRAM_API_HASH to .env before real Telegram tests.")
        return

    if not result["real_channels_ready"]:
        print("Credentials can be tested later, but real channels are not configured yet.")
        print("Add public channels to scanner_real_channels.py when ready.")
        return

    print("Ready for a separate safe connection-only test in the next step.")


def main() -> None:
    result = check_telegram_real_mode()
    print_check_result(result)


if __name__ == "__main__":
    main()
