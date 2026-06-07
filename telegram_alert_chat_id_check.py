import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from credentials import (
    SCANNER_TELEGRAM_SEND_ENABLED,
    TELEGRAM_ALERT_CHAT_ID,
    TELEGRAM_API_KEY,
)


REPORTS_DIR = Path("reports")
OUTPUT_PATH = REPORTS_DIR / "telegram_alert_chat_id_check.json"


def mask_secret(value: Any, visible: int = 4) -> str:
    text = str(value or "").strip()

    if not text:
        return ""

    if len(text) <= visible * 2:
        return "***"

    return text[:visible] + "***" + text[-visible:]


def normalize_text(value: Any) -> str:
    return str(value or "").strip()


def looks_like_telegram_bot_token(value: Any) -> bool:
    text = normalize_text(value)

    if not text:
        return False

    if ":" not in text:
        return False

    left, right = text.split(":", 1)

    if not left.isdigit():
        return False

    if len(right) < 20:
        return False

    return True


def looks_like_chat_id(value: Any) -> bool:
    text = normalize_text(value)

    if not text:
        return False

    if text.startswith("@") and len(text) > 1:
        return True

    if text.startswith("-"):
        return text[1:].isdigit()

    return text.isdigit()


def build_check_payload() -> Dict[str, Any]:
    warnings: List[str] = []
    blockers: List[str] = []
    recommendations: List[str] = []

    telegram_api_key_text = normalize_text(TELEGRAM_API_KEY)
    telegram_alert_chat_id_text = normalize_text(TELEGRAM_ALERT_CHAT_ID)

    telegram_token_configured = bool(telegram_api_key_text)
    telegram_chat_configured = bool(telegram_alert_chat_id_text)

    telegram_token_format_ok = looks_like_telegram_bot_token(telegram_api_key_text)
    telegram_chat_id_format_ok = looks_like_chat_id(telegram_alert_chat_id_text)

    if not telegram_token_configured:
        warnings.append("telegram_api_key_not_configured")
        recommendations.append("Add TELEGRAM_API_KEY to .env before real Telegram delivery.")

    elif not telegram_token_format_ok:
        warnings.append("telegram_api_key_format_unusual")
        recommendations.append("Check TELEGRAM_API_KEY format. Expected Telegram Bot API token like 123456:ABC...")

    if not telegram_chat_configured:
        warnings.append("telegram_alert_chat_id_not_configured")
        recommendations.append("Add TELEGRAM_ALERT_CHAT_ID to .env before real Telegram delivery.")

    elif not telegram_chat_id_format_ok:
        warnings.append("telegram_alert_chat_id_format_unusual")
        recommendations.append("Check TELEGRAM_ALERT_CHAT_ID. It can be numeric, negative group id, or @channelname.")

    if SCANNER_TELEGRAM_SEND_ENABLED:
        warnings.append("scanner_telegram_send_enabled_is_true")
        recommendations.append(
            "SCANNER_TELEGRAM_SEND_ENABLED is true. Keep it false until you intentionally test real sending."
        )
    else:
        recommendations.append(
            "SCANNER_TELEGRAM_SEND_ENABLED is false. This is the safe default."
        )

    ready_for_real_sender = (
        telegram_token_configured
        and telegram_chat_configured
        and telegram_token_format_ok
        and telegram_chat_id_format_ok
    )

    if not ready_for_real_sender:
        recommendations.append(
            "Do not enable real Telegram sending yet. Fix warnings first and rerun this check."
        )
    else:
        recommendations.append(
            "Telegram config looks ready. Next safe step is still dry-run before any real send."
        )

    return {
        "source": "telegram_alert_chat_id_check",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analytical_only": True,
        "telegram_api_used": False,
        "telegram_message_sent": False,
        "orders_enabled": False,
        "trading_enabled": False,
        "binance_api_used": False,
        "input_source": ".env via credentials.py",
        "output_file": str(OUTPUT_PATH),
        "safe_to_continue": True,
        "ready_for_real_sender": ready_for_real_sender,
        "scanner_telegram_send_enabled": bool(SCANNER_TELEGRAM_SEND_ENABLED),
        "telegram_token_configured": telegram_token_configured,
        "telegram_chat_configured": telegram_chat_configured,
        "telegram_token_format_ok": telegram_token_format_ok,
        "telegram_chat_id_format_ok": telegram_chat_id_format_ok,
        "telegram_api_key_masked": mask_secret(TELEGRAM_API_KEY),
        "telegram_alert_chat_id_masked": mask_secret(TELEGRAM_ALERT_CHAT_ID),
        "blockers": blockers,
        "warnings": warnings,
        "recommendations": recommendations,
        "disclaimer": (
            "This check does not send Telegram messages, does not create orders, "
            "does not start trading, does not read Telegram, and does not call Binance API."
        ),
    }


def save_check_payload(payload: Dict[str, Any], path: Path = OUTPUT_PATH) -> Path:
    path.parent.mkdir(exist_ok=True)

    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    return path


def print_check_summary(payload: Dict[str, Any], output_path: Path) -> None:
    print("TELEGRAM ALERT CHAT ID CHECK")
    print("============================")
    print("Mode: analytical only")
    print("Telegram API used:", payload["telegram_api_used"])
    print("Telegram message sent:", payload["telegram_message_sent"])
    print("Orders enabled:", payload["orders_enabled"])
    print("Trading enabled:", payload["trading_enabled"])
    print("Binance API used:", payload["binance_api_used"])
    print("Output file:", output_path)
    print()

    print("SUMMARY")
    print("=======")
    print("Safe to continue:", payload["safe_to_continue"])
    print("Ready for real sender:", payload["ready_for_real_sender"])
    print("Scanner Telegram send enabled:", payload["scanner_telegram_send_enabled"])
    print("Telegram token configured:", payload["telegram_token_configured"])
    print("Telegram chat configured:", payload["telegram_chat_configured"])
    print("Telegram token format OK:", payload["telegram_token_format_ok"])
    print("Telegram chat id format OK:", payload["telegram_chat_id_format_ok"])
    print("Telegram API key masked:", payload["telegram_api_key_masked"] or "not configured")
    print("Telegram alert chat id masked:", payload["telegram_alert_chat_id_masked"] or "not configured")

    if payload.get("blockers"):
        print("Blockers:", ", ".join(str(item) for item in payload["blockers"]))
    else:
        print("Blockers: none")

    if payload.get("warnings"):
        print("Warnings:", ", ".join(str(item) for item in payload["warnings"]))
    else:
        print("Warnings: none")

    print()
    print("RECOMMENDATIONS")
    print("===============")

    for item in payload.get("recommendations", []):
        print("-", item)

    print()
    print("SAFETY")
    print("======")
    print("[OK] This check did not send Telegram messages.")
    print("[OK] This check did not create orders.")
    print("[OK] This check did not start trading bot.")
    print("[OK] This check did not call Binance API.")
    print("[OK] This check only inspected local environment values through credentials.py.")


def main() -> None:
    payload = build_check_payload()
    output_path = save_check_payload(payload)
    print_check_summary(payload, output_path)


if __name__ == "__main__":
    main()
