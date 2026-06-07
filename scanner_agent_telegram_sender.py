import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from credentials import (
    SCANNER_TELEGRAM_SEND_ENABLED,
    TELEGRAM_ALERT_CHAT_ID,
    TELEGRAM_API_KEY,
)


INPUT_PATH = Path("reports") / "scanner_agent_telegram_message_preview.txt"
DECISION_PATH = Path("reports") / "scanner_agent_decision.json"
OUTPUT_PATH = Path("reports") / "scanner_agent_telegram_sender_result.json"

MAX_TELEGRAM_MESSAGE_LENGTH = 4096


def mask_secret(value: Any, visible: int = 4) -> str:
    text = str(value or "").strip()

    if not text:
        return ""

    if len(text) <= visible * 2:
        return "***"

    return text[:visible] + "***" + text[-visible:]


def load_message_text(path: Path = INPUT_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {
            "ok": False,
            "text": "",
            "error": f"Telegram preview message file not found: {path}",
            "blockers": ["telegram_preview_message_file_not_found"],
            "warnings": [],
        }

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as ex:
        return {
            "ok": False,
            "text": "",
            "error": f"Cannot read Telegram preview message file: {ex}",
            "blockers": ["telegram_preview_message_file_read_error"],
            "warnings": [],
        }

    if not text.strip():
        return {
            "ok": False,
            "text": "",
            "error": "Telegram preview message file is empty.",
            "blockers": ["telegram_preview_message_file_empty"],
            "warnings": [],
        }

    return {
        "ok": True,
        "text": text,
        "error": None,
        "blockers": [],
        "warnings": [],
    }


def load_decision_status(path: Path = DECISION_PATH) -> Dict[str, Any]:
    """
    Read scanner_agent_decision.json before any Telegram sending.

    This prevents sending an empty notification when the latest scanner run
    produced zero analytical decisions.
    """
    if not path.exists():
        return {
            "ok": False,
            "total_decisions": 0,
            "summary_by_decision": {},
            "error": f"Decision file not found: {path}",
            "blockers": ["decision_file_not_found"],
            "warnings": [],
        }

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as ex:
        return {
            "ok": False,
            "total_decisions": 0,
            "summary_by_decision": {},
            "error": f"Invalid decision JSON: {ex}",
            "blockers": ["invalid_decision_json"],
            "warnings": [],
        }
    except OSError as ex:
        return {
            "ok": False,
            "total_decisions": 0,
            "summary_by_decision": {},
            "error": f"Cannot read decision JSON: {ex}",
            "blockers": ["decision_file_read_error"],
            "warnings": [],
        }

    decisions = payload.get("decisions", [])

    if not isinstance(decisions, list):
        decisions = []

    total_decisions = int(payload.get("total_decisions") or len(decisions) or 0)
    summary_by_decision = payload.get("summary_by_decision", {})

    if not isinstance(summary_by_decision, dict):
        summary_by_decision = {}

    return {
        "ok": True,
        "total_decisions": total_decisions,
        "summary_by_decision": summary_by_decision,
        "input_created_at": payload.get("created_at"),
        "safe_to_continue": bool(payload.get("safe_to_continue", False)),
        "error": payload.get("error"),
        "blockers": list(payload.get("blockers", [])),
        "warnings": list(payload.get("warnings", [])),
    }


def validate_sender_inputs(
    message_result: Dict[str, Any],
    decision_status: Dict[str, Any],
) -> Dict[str, Any]:
    blockers = list(message_result.get("blockers", []))
    warnings = list(message_result.get("warnings", []))

    decision_blockers = decision_status.get("blockers", [])
    decision_warnings = decision_status.get("warnings", [])

    if isinstance(decision_blockers, list):
        blockers.extend(str(item) for item in decision_blockers if str(item).strip())

    if isinstance(decision_warnings, list):
        warnings.extend(str(item) for item in decision_warnings if str(item).strip())

    telegram_token_configured = bool(str(TELEGRAM_API_KEY or "").strip())
    telegram_chat_configured = bool(str(TELEGRAM_ALERT_CHAT_ID or "").strip())

    if not telegram_token_configured:
        blockers.append("telegram_api_key_not_configured")

    if not telegram_chat_configured:
        blockers.append("telegram_alert_chat_id_not_configured")

    if not decision_status.get("ok"):
        blockers.append("decision_status_not_ready")

    total_decisions = int(decision_status.get("total_decisions") or 0)

    if total_decisions <= 0:
        blockers.append("no_decisions_to_send")

    text = str(message_result.get("text", ""))
    text_length = len(text)

    if text_length > MAX_TELEGRAM_MESSAGE_LENGTH:
        blockers.append("message_is_longer_than_telegram_limit")

    if "Автоордера отключены" not in text and "Orders: disabled" not in text:
        warnings.append("message_does_not_contain_clear_orders_disabled_text")

    if "не торговый сигнал" not in text and "not a trading entry" not in text:
        warnings.append("message_does_not_contain_clear_not_trading_signal_text")

    return {
        "telegram_token_configured": telegram_token_configured,
        "telegram_chat_configured": telegram_chat_configured,
        "telegram_api_key_masked": mask_secret(TELEGRAM_API_KEY),
        "telegram_alert_chat_id_masked": mask_secret(TELEGRAM_ALERT_CHAT_ID),
        "scanner_telegram_send_enabled": bool(SCANNER_TELEGRAM_SEND_ENABLED),
        "message_length": text_length,
        "telegram_limit": MAX_TELEGRAM_MESSAGE_LENGTH,
        "message_within_telegram_limit": text_length <= MAX_TELEGRAM_MESSAGE_LENGTH,
        "total_decisions": total_decisions,
        "summary_by_decision": decision_status.get("summary_by_decision", {}),
        "decision_input_created_at": decision_status.get("input_created_at"),
        "decision_safe_to_continue": bool(decision_status.get("safe_to_continue")),
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }


def build_base_payload(
    message_result: Dict[str, Any],
    decision_status: Dict[str, Any],
    validation: Dict[str, Any],
) -> Dict[str, Any]:
    safe_to_continue = bool(message_result.get("ok")) and not validation["blockers"]

    return {
        "source": "scanner_agent_telegram_sender",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analytical_only": True,
        "dry_run": False,
        "telegram_send_enabled": validation["scanner_telegram_send_enabled"],
        "telegram_api_used": False,
        "telegram_message_sent": False,
        "orders_enabled": False,
        "trading_enabled": False,
        "binance_api_used": False,
        "binance_orders_created": False,
        "input_file": str(INPUT_PATH),
        "decision_file": str(DECISION_PATH),
        "output_file": str(OUTPUT_PATH),
        "safe_to_continue": safe_to_continue,
        "telegram_token_configured": validation["telegram_token_configured"],
        "telegram_chat_configured": validation["telegram_chat_configured"],
        "telegram_api_key_masked": validation["telegram_api_key_masked"],
        "telegram_alert_chat_id_masked": validation["telegram_alert_chat_id_masked"],
        "message_length": validation["message_length"],
        "telegram_limit": validation["telegram_limit"],
        "message_within_telegram_limit": validation["message_within_telegram_limit"],
        "total_decisions": validation["total_decisions"],
        "summary_by_decision": validation["summary_by_decision"],
        "decision_input_created_at": validation["decision_input_created_at"],
        "decision_safe_to_continue": validation["decision_safe_to_continue"],
        "message_preview": str(message_result.get("text", ""))[:1000],
        "blockers": validation["blockers"],
        "warnings": validation["warnings"],
        "error": message_result.get("error") or decision_status.get("error"),
        "send_attempted": False,
        "send_result": None,
        "disclaimer": (
            "This sender is for analytical scanner notifications only. "
            "It does not create orders, does not start trading, and does not call Binance API. "
            "Telegram sending is disabled unless SCANNER_TELEGRAM_SEND_ENABLED=true. "
            "If total_decisions is 0, Telegram sending is blocked."
        ),
    }


def build_delivery_message_text(text: str) -> str:
    """
    Convert local preview text into real Telegram delivery text.

    Preview file stays safe and says that sending is disabled.
    Only this sender, after all checks and SCANNER_TELEGRAM_SEND_ENABLED=true,
    changes the delivery line before sending.
    """
    delivery_text = str(text)

    delivery_text = delivery_text.replace(
        "Telegram send: отключён",
        "Доставка: Telegram, сообщение отправляется по разрешению SCANNER_TELEGRAM_SEND_ENABLED=true",
    )

    delivery_text = delivery_text.replace(
        "Доставка: preview, сообщение не отправлено",
        "Доставка: Telegram, сообщение отправляется по разрешению SCANNER_TELEGRAM_SEND_ENABLED=true",
    )

    return delivery_text


def send_telegram_message(text: str) -> Dict[str, Any]:
    try:
        import telegram
    except Exception as ex:
        return {
            "ok": False,
            "error": "Cannot import telegram package: " + str(ex),
            "exception_type": type(ex).__name__,
        }

    try:
        bot = telegram.Bot(token=TELEGRAM_API_KEY)
        result = bot.send_message(
            chat_id=TELEGRAM_ALERT_CHAT_ID,
            text=text,
            disable_web_page_preview=True,
        )

        return {
            "ok": True,
            "message_id": getattr(result, "message_id", None),
            "chat_id_masked": mask_secret(TELEGRAM_ALERT_CHAT_ID),
        }

    except Exception as ex:
        return {
            "ok": False,
            "error": str(ex),
            "exception_type": type(ex).__name__,
        }


def build_sender_payload() -> Dict[str, Any]:
    message_result = load_message_text()
    decision_status = load_decision_status()
    validation = validate_sender_inputs(message_result, decision_status)
    payload = build_base_payload(message_result, decision_status, validation)

    if not payload["safe_to_continue"]:
        payload["warnings"].append("send_not_attempted_because_inputs_are_not_safe")
        payload["warnings"] = sorted(set(payload["warnings"]))
        return payload

    if payload["total_decisions"] <= 0:
        payload["blockers"].append("no_decisions_to_send")
        payload["warnings"].append("send_not_attempted_because_no_decisions")
        payload["blockers"] = sorted(set(payload["blockers"]))
        payload["warnings"] = sorted(set(payload["warnings"]))
        payload["safe_to_continue"] = False
        return payload

    if not payload["telegram_send_enabled"]:
        payload["warnings"].append("send_not_attempted_because_scanner_telegram_send_enabled_is_false")
        payload["warnings"] = sorted(set(payload["warnings"]))
        return payload

    text = build_delivery_message_text(str(message_result.get("text", "")))

    payload["message_length"] = len(text)
    payload["message_within_telegram_limit"] = len(text) <= MAX_TELEGRAM_MESSAGE_LENGTH
    payload["message_preview"] = text[:1000]

    if len(text) > MAX_TELEGRAM_MESSAGE_LENGTH:
        payload["blockers"].append("delivery_message_is_longer_than_telegram_limit")
        payload["warnings"].append("send_not_attempted_because_delivery_message_is_too_long")
        payload["blockers"] = sorted(set(payload["blockers"]))
        payload["warnings"] = sorted(set(payload["warnings"]))
        payload["safe_to_continue"] = False
        return payload

    payload["send_attempted"] = True
    payload["telegram_api_used"] = True

    send_result = send_telegram_message(text)

    payload["send_result"] = send_result
    payload["telegram_message_sent"] = bool(send_result.get("ok"))

    if not send_result.get("ok"):
        payload["blockers"].append("telegram_send_failed")
        payload["blockers"] = sorted(set(payload["blockers"]))
        payload["error"] = send_result.get("error")

    return payload


def save_sender_payload(payload: Dict[str, Any], path: Path = OUTPUT_PATH) -> Path:
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


def print_sender_summary(payload: Dict[str, Any], output_path: Path) -> None:
    print("SCANNER AGENT TELEGRAM SENDER")
    print("=============================")
    print("Mode: analytical only")
    print("Telegram send enabled:", payload["telegram_send_enabled"])
    print("Telegram API used:", payload["telegram_api_used"])
    print("Telegram message sent:", payload["telegram_message_sent"])
    print("Orders enabled:", payload["orders_enabled"])
    print("Trading enabled:", payload["trading_enabled"])
    print("Binance API used:", payload["binance_api_used"])
    print("Input file:", payload["input_file"])
    print("Decision file:", payload["decision_file"])
    print("Output file:", output_path)
    print()

    print("SUMMARY")
    print("=======")
    print("Safe to continue:", payload["safe_to_continue"])
    print("Send attempted:", payload["send_attempted"])
    print("Telegram token configured:", payload["telegram_token_configured"])
    print("Telegram chat configured:", payload["telegram_chat_configured"])
    print("Telegram API key masked:", payload["telegram_api_key_masked"] or "not configured")
    print("Telegram alert chat id masked:", payload["telegram_alert_chat_id_masked"] or "not configured")
    print("Total decisions:", payload["total_decisions"])
    print("Summary by decision:", payload["summary_by_decision"])
    print("Decision safe to continue:", payload["decision_safe_to_continue"])
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

    if payload.get("send_result") is not None:
        print("Send result:", payload["send_result"])

    print()
    print("SAFETY")
    print("======")
    print("[OK] This sender did not create orders.")
    print("[OK] This sender did not start trading bot.")
    print("[OK] This sender did not call Binance API.")
    print("[OK] This sender reads only local Telegram preview text.")
    print("[OK] This sender checks scanner_agent_decision.json before sending.")

    if payload["telegram_message_sent"]:
        print("[OK] Telegram message was sent as an analytical notification only.")
    else:
        print("[OK] Telegram message was not sent.")

    print()
    print("NEXT STEP")
    print("=========")

    if payload["telegram_message_sent"]:
        print("Check Telegram chat and verify the notification text.")
        print("Keep order execution disabled.")
        return

    if payload["total_decisions"] <= 0:
        print("No analytical decisions found.")
        print("Telegram sending was blocked to avoid sending an empty notification.")
        print("Rerun the full scanner later when market/social conditions produce decisions.")
        return

    if not payload["telegram_send_enabled"]:
        print("Telegram sending is still disabled.")
        print("To enable later, set SCANNER_TELEGRAM_SEND_ENABLED=true in .env and rerun.")
        return

    print("Fix blockers or Telegram configuration, then rerun.")


def main() -> None:
    payload = build_sender_payload()
    output_path = save_sender_payload(payload)
    print_sender_summary(payload, output_path)


if __name__ == "__main__":
    main()
