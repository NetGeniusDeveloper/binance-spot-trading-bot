import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from credentials import (
    SCANNER_TELEGRAM_MANUAL_CONFIRM,
    SCANNER_TELEGRAM_SEND_ENABLED,
    TELEGRAM_ALERT_CHAT_ID,
    TELEGRAM_API_KEY,
)


INPUT_PATH = Path("reports") / "scanner_agent_telegram_message_preview.txt"
OUTPUT_PATH = Path("reports") / "scanner_agent_telegram_sender_dry_run.json"

MAX_TELEGRAM_MESSAGE_LENGTH = 4096


def mask_secret(value: Any, visible: int = 4) -> str:
    text = str(value or "").strip()

    if not text:
        return ""

    if len(text) <= visible * 2:
        return "***"

    return text[:visible] + "***" + text[-visible:]


def load_preview_text(path: Path = INPUT_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {
            "ok": False,
            "text": "",
            "error": f"Preview message file not found: {path}",
            "blockers": ["preview_message_file_not_found"],
            "warnings": [],
        }

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as ex:
        return {
            "ok": False,
            "text": "",
            "error": f"Cannot read preview message file: {ex}",
            "blockers": ["preview_message_file_read_error"],
            "warnings": [],
        }

    if not text.strip():
        return {
            "ok": False,
            "text": "",
            "error": "Preview message file is empty.",
            "blockers": ["preview_message_file_empty"],
            "warnings": [],
        }

    return {
        "ok": True,
        "text": text,
        "error": None,
        "blockers": [],
        "warnings": [],
    }


def validate_dry_run_inputs(preview_result: Dict[str, Any]) -> Dict[str, Any]:
    blockers = list(preview_result.get("blockers", []))
    warnings = list(preview_result.get("warnings", []))

    telegram_token_configured = bool(str(TELEGRAM_API_KEY or "").strip())
    telegram_chat_configured = bool(str(TELEGRAM_ALERT_CHAT_ID or "").strip())
    scanner_telegram_send_enabled = bool(SCANNER_TELEGRAM_SEND_ENABLED)
    scanner_telegram_manual_confirm = bool(SCANNER_TELEGRAM_MANUAL_CONFIRM)

    if not telegram_token_configured:
        warnings.append("telegram_api_key_not_configured")

    if not telegram_chat_configured:
        warnings.append("telegram_alert_chat_id_not_configured")

    if not scanner_telegram_send_enabled:
        warnings.append("scanner_telegram_send_enabled_is_false")

    if not scanner_telegram_manual_confirm:
        warnings.append("scanner_telegram_manual_confirm_is_false")

    text = str(preview_result.get("text", ""))
    text_length = len(text)

    if text_length > MAX_TELEGRAM_MESSAGE_LENGTH:
        warnings.append("message_is_longer_than_telegram_limit")

    return {
        "telegram_token_configured": telegram_token_configured,
        "telegram_chat_configured": telegram_chat_configured,
        "scanner_telegram_send_enabled": scanner_telegram_send_enabled,
        "scanner_telegram_manual_confirm": scanner_telegram_manual_confirm,
        "telegram_api_key_masked": mask_secret(TELEGRAM_API_KEY),
        "telegram_alert_chat_id_masked": mask_secret(TELEGRAM_ALERT_CHAT_ID),
        "message_length": text_length,
        "telegram_limit": MAX_TELEGRAM_MESSAGE_LENGTH,
        "message_within_telegram_limit": text_length <= MAX_TELEGRAM_MESSAGE_LENGTH,
        "blockers": blockers,
        "warnings": sorted(set(warnings)),
    }


def build_dry_run_payload() -> Dict[str, Any]:
    preview_result = load_preview_text()
    validation = validate_dry_run_inputs(preview_result)

    safe_to_continue = bool(preview_result.get("ok")) and not validation["blockers"]

    would_send_if_enabled = (
        safe_to_continue
        and validation["telegram_token_configured"]
        and validation["telegram_chat_configured"]
        and validation["message_within_telegram_limit"]
    )

    ready_for_real_sender_now = (
        would_send_if_enabled
        and validation["scanner_telegram_send_enabled"]
        and validation["scanner_telegram_manual_confirm"]
    )

    return {
        "source": "scanner_agent_telegram_sender_dry_run",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analytical_only": True,
        "dry_run": True,
        "telegram_send_enabled": False,
        "scanner_telegram_send_enabled": validation["scanner_telegram_send_enabled"],
        "scanner_telegram_manual_confirm": validation["scanner_telegram_manual_confirm"],
        "telegram_api_used": False,
        "telegram_message_sent": False,
        "orders_enabled": False,
        "trading_enabled": False,
        "binance_api_used": False,
        "binance_orders_created": False,
        "input_file": str(INPUT_PATH),
        "output_file": str(OUTPUT_PATH),
        "safe_to_continue": safe_to_continue,
        "would_send_if_enabled": would_send_if_enabled,
        "ready_for_real_sender_now": ready_for_real_sender_now,
        "telegram_token_configured": validation["telegram_token_configured"],
        "telegram_chat_configured": validation["telegram_chat_configured"],
        "telegram_api_key_masked": validation["telegram_api_key_masked"],
        "telegram_alert_chat_id_masked": validation["telegram_alert_chat_id_masked"],
        "message_length": validation["message_length"],
        "telegram_limit": validation["telegram_limit"],
        "message_within_telegram_limit": validation["message_within_telegram_limit"],
        "message_preview": str(preview_result.get("text", ""))[:1000],
        "blockers": validation["blockers"],
        "warnings": validation["warnings"],
        "error": preview_result.get("error"),
        "disclaimer": (
            "This is a dry-run Telegram sender check. "
            "It does not send Telegram messages, does not create orders, "
            "does not start trading, and does not call Binance API. "
            "Real Telegram sending requires SCANNER_TELEGRAM_SEND_ENABLED=true "
            "and SCANNER_TELEGRAM_MANUAL_CONFIRM=true."
        ),
    }


def save_dry_run_payload(payload: Dict[str, Any], path: Path = OUTPUT_PATH) -> Path:
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


def print_dry_run_summary(payload: Dict[str, Any], output_path: Path) -> None:
    print("SCANNER AGENT TELEGRAM SENDER DRY RUN")
    print("=====================================")
    print("Mode: analytical only")
    print("Dry run:", payload["dry_run"])
    print("Telegram send enabled:", payload["telegram_send_enabled"])
    print("Scanner Telegram send enabled:", payload["scanner_telegram_send_enabled"])
    print("Scanner Telegram manual confirm:", payload["scanner_telegram_manual_confirm"])
    print("Telegram API used:", payload["telegram_api_used"])
    print("Telegram message sent:", payload["telegram_message_sent"])
    print("Orders enabled:", payload["orders_enabled"])
    print("Trading enabled:", payload["trading_enabled"])
    print("Binance API used:", payload["binance_api_used"])
    print("Input file:", payload["input_file"])
    print("Output file:", output_path)
    print()

    print("SUMMARY")
    print("=======")
    print("Safe to continue:", payload["safe_to_continue"])
    print("Would send if real sender was enabled:", payload["would_send_if_enabled"])
    print("Ready for real sender now:", payload["ready_for_real_sender_now"])
    print("Telegram token configured:", payload["telegram_token_configured"])
    print("Telegram chat configured:", payload["telegram_chat_configured"])
    print("Telegram API key masked:", payload["telegram_api_key_masked"] or "not configured")
    print("Telegram alert chat id masked:", payload["telegram_alert_chat_id_masked"] or "not configured")
    print("Message length:", payload["message_length"])
    print("Telegram limit:", payload["telegram_limit"])
    print("Message within Telegram limit:", payload["message_within_telegram_limit"])

    if payload.get("blockers"):
        print("Blockers:", ", ".join(str(item) for item in payload["blockers"]))
    else:
        print("Blockers: none")

    if payload.get("warnings"):
        print("Warnings:", ", ".join(str(item) for item in payload["warnings"]))
    else:
        print("Warnings: none")

    if payload.get("error"):
        print("Error:", payload["error"])

    print()
    print("MESSAGE PREVIEW")
    print("===============")

    message_preview = payload.get("message_preview", "")

    if message_preview:
        print(message_preview)
    else:
        print("No message preview.")

    print()
    print("SAFETY")
    print("======")
    print("[OK] This dry run did not send Telegram messages.")
    print("[OK] This dry run did not create orders.")
    print("[OK] This dry run did not start trading bot.")
    print("[OK] This dry run did not call Binance API.")
    print("[OK] This dry run only checks local text and configuration.")
    print("[OK] Real sender requires two manual flags.")

    print()
    print("NEXT STEP")
    print("=========")

    if not payload["safe_to_continue"]:
        print("Fix blockers first, then rerun this dry-run sender.")
        return

    if not payload["telegram_token_configured"] or not payload["telegram_chat_configured"]:
        print("Add TELEGRAM_API_KEY and TELEGRAM_ALERT_CHAT_ID to .env before real delivery.")
        return

    if not payload["scanner_telegram_send_enabled"] or not payload["scanner_telegram_manual_confirm"]:
        print("Dry run is complete and safe.")
        print("Real delivery still requires both SCANNER_TELEGRAM_SEND_ENABLED=true and SCANNER_TELEGRAM_MANUAL_CONFIRM=true.")
        return

    print("Dry run is ready for controlled real sender.")
    print("Keep order execution disabled.")


def main() -> None:
    payload = build_dry_run_payload()
    output_path = save_dry_run_payload(payload)
    print_dry_run_summary(payload, output_path)


if __name__ == "__main__":
    main()
