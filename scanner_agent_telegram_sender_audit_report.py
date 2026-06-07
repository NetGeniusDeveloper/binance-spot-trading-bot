import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


REPORTS_DIR = Path("reports")

SENDER_RESULT_PATH = REPORTS_DIR / "scanner_agent_telegram_sender_result.json"
DRY_RUN_PATH = REPORTS_DIR / "scanner_agent_telegram_sender_dry_run.json"
DECISION_PATH = REPORTS_DIR / "scanner_agent_decision.json"
DELIVERY_TEXT_PATH = REPORTS_DIR / "scanner_agent_telegram_delivery_text.txt"
PREVIEW_TEXT_PATH = REPORTS_DIR / "scanner_agent_telegram_message_preview.txt"

OUTPUT_JSON_PATH = REPORTS_DIR / "scanner_agent_telegram_sender_audit_report.json"
OUTPUT_TXT_PATH = REPORTS_DIR / "scanner_agent_telegram_sender_audit_report.txt"


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {
            "ok": False,
            "path": str(path),
            "error": f"File not found: {path}",
            "data": {},
        }

    try:
        return {
            "ok": True,
            "path": str(path),
            "error": None,
            "data": json.loads(path.read_text(encoding="utf-8")),
        }
    except json.JSONDecodeError as ex:
        return {
            "ok": False,
            "path": str(path),
            "error": f"Invalid JSON: {ex}",
            "data": {},
        }
    except OSError as ex:
        return {
            "ok": False,
            "path": str(path),
            "error": f"Cannot read file: {ex}",
            "data": {},
        }


def load_text_status(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {
            "ok": False,
            "path": str(path),
            "exists": False,
            "length": 0,
            "error": f"File not found: {path}",
            "has_delivery_notice": False,
            "has_preview_notice": False,
            "has_orders_disabled_notice": False,
            "has_not_trading_signal_notice": False,
        }

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as ex:
        return {
            "ok": False,
            "path": str(path),
            "exists": True,
            "length": 0,
            "error": f"Cannot read file: {ex}",
            "has_delivery_notice": False,
            "has_preview_notice": False,
            "has_orders_disabled_notice": False,
            "has_not_trading_signal_notice": False,
        }

    return {
        "ok": True,
        "path": str(path),
        "exists": True,
        "length": len(text),
        "error": None,
        "has_delivery_notice": "Telegram: отправлено как аналитическое уведомление" in text,
        "has_preview_notice": "Telegram: preview, сообщение не отправлено" in text,
        "has_orders_disabled_notice": "Автоордера отключены" in text or "Orders: disabled" in text,
        "has_not_trading_signal_notice": "не торговый сигнал" in text or "not a trading entry" in text,
    }


def as_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    return []


def bool_value(value: Any) -> bool:
    return bool(value)


def build_audit_payload() -> Dict[str, Any]:
    sender_file = load_json(SENDER_RESULT_PATH)
    dry_run_file = load_json(DRY_RUN_PATH)
    decision_file = load_json(DECISION_PATH)

    sender_data = as_dict(sender_file.get("data"))
    dry_run_data = as_dict(dry_run_file.get("data"))
    decision_data = as_dict(decision_file.get("data"))

    delivery_text_status = load_text_status(DELIVERY_TEXT_PATH)
    preview_text_status = load_text_status(PREVIEW_TEXT_PATH)

    send_result = as_dict(sender_data.get("send_result"))
    decisions = as_list(decision_data.get("decisions"))

    total_decisions = int(sender_data.get("total_decisions") or decision_data.get("total_decisions") or len(decisions) or 0)

    telegram_message_sent = bool_value(sender_data.get("telegram_message_sent"))
    telegram_api_used = bool_value(sender_data.get("telegram_api_used"))
    send_attempted = bool_value(sender_data.get("send_attempted"))

    message_id = send_result.get("message_id")
    message_length = int(sender_data.get("message_length") or 0)
    telegram_limit = int(sender_data.get("telegram_limit") or 4096)
    message_within_limit = bool_value(sender_data.get("message_within_telegram_limit"))

    blockers: List[str] = []
    warnings: List[str] = []

    for loaded_file in [sender_file, dry_run_file, decision_file]:
        if not loaded_file.get("ok"):
            warnings.append(str(loaded_file.get("error")))

    for source_data in [sender_data, dry_run_data, decision_data]:
        for blocker in as_list(source_data.get("blockers")):
            if str(blocker).strip():
                blockers.append(str(blocker))

        for warning in as_list(source_data.get("warnings")):
            if str(warning).strip():
                warnings.append(str(warning))

    if total_decisions <= 0:
        blockers.append("no_decisions_found_for_audit")

    if telegram_message_sent and not message_id:
        warnings.append("telegram_message_sent_but_message_id_missing")

    if telegram_message_sent and not telegram_api_used:
        warnings.append("telegram_message_sent_but_api_usage_not_reported")

    if send_attempted and not telegram_message_sent:
        blockers.append("send_attempted_but_message_not_sent")

    if not message_within_limit:
        blockers.append("message_not_within_telegram_limit")

    if message_length > telegram_limit:
        blockers.append("message_length_exceeds_telegram_limit")

    if not delivery_text_status["ok"]:
        warnings.append("delivery_text_file_not_ready")

    if delivery_text_status["ok"] and delivery_text_status["has_preview_notice"]:
        warnings.append("delivery_text_still_contains_preview_notice")

    if delivery_text_status["ok"] and not delivery_text_status["has_delivery_notice"]:
        warnings.append("delivery_text_missing_final_delivery_notice")

    if delivery_text_status["ok"] and not delivery_text_status["has_orders_disabled_notice"]:
        warnings.append("delivery_text_missing_orders_disabled_notice")

    if delivery_text_status["ok"] and not delivery_text_status["has_not_trading_signal_notice"]:
        warnings.append("delivery_text_missing_not_trading_signal_notice")

    safety_ok = (
        bool_value(sender_data.get("analytical_only", True))
        and not bool_value(sender_data.get("orders_enabled"))
        and not bool_value(sender_data.get("trading_enabled"))
        and not bool_value(sender_data.get("binance_api_used"))
        and not bool_value(sender_data.get("binance_orders_created"))
        and message_within_limit
        and total_decisions > 0
        and not blockers
    )

    if telegram_message_sent:
        audit_status = "sent_verified" if safety_ok else "sent_with_audit_warnings"
    elif send_attempted:
        audit_status = "send_attempt_failed"
    elif total_decisions <= 0:
        audit_status = "no_decisions"
    else:
        audit_status = "not_sent"

    return {
        "source": "scanner_agent_telegram_sender_audit_report",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "audit_status": audit_status,
        "safety_ok": safety_ok,
        "analytical_only": True,
        "orders_enabled": False,
        "trading_enabled": False,
        "binance_api_used": False,
        "binance_orders_created": False,
        "files": {
            "sender_result": {
                "path": str(SENDER_RESULT_PATH),
                "ok": sender_file.get("ok"),
                "error": sender_file.get("error"),
            },
            "sender_dry_run": {
                "path": str(DRY_RUN_PATH),
                "ok": dry_run_file.get("ok"),
                "error": dry_run_file.get("error"),
            },
            "decision": {
                "path": str(DECISION_PATH),
                "ok": decision_file.get("ok"),
                "error": decision_file.get("error"),
            },
            "delivery_text": delivery_text_status,
            "preview_text": preview_text_status,
        },
        "telegram": {
            "telegram_send_enabled": bool_value(sender_data.get("telegram_send_enabled")),
            "telegram_manual_confirm": bool_value(sender_data.get("telegram_manual_confirm")),
            "telegram_api_used": telegram_api_used,
            "telegram_message_sent": telegram_message_sent,
            "send_attempted": send_attempted,
            "message_id": message_id,
            "chat_id_masked": send_result.get("chat_id_masked") or sender_data.get("telegram_alert_chat_id_masked"),
            "message_length": message_length,
            "telegram_limit": telegram_limit,
            "message_within_telegram_limit": message_within_limit,
        },
        "decisions": {
            "total_decisions": total_decisions,
            "summary_by_decision": sender_data.get("summary_by_decision") or decision_data.get("summary_by_decision", {}),
            "decision_safe_to_continue": bool_value(sender_data.get("decision_safe_to_continue") or decision_data.get("safe_to_continue")),
        },
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "disclaimer": (
            "This audit report only reads local analytical report files. "
            "It does not send Telegram messages, does not create orders, "
            "does not start trading, and does not call Binance API."
        ),
    }


def save_json(payload: Dict[str, Any], path: Path = OUTPUT_JSON_PATH) -> Path:
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def build_text_report(payload: Dict[str, Any]) -> str:
    telegram = payload.get("telegram", {})
    decisions = payload.get("decisions", {})
    files = payload.get("files", {})

    delivery_text = files.get("delivery_text", {})
    preview_text = files.get("preview_text", {})

    lines: List[str] = []

    lines.append("SCANNER AGENT TELEGRAM SENDER AUDIT REPORT")
    lines.append("==========================================")
    lines.append(f"Created at: {payload.get('created_at')}")
    lines.append("")
    lines.append(f"Audit status: {payload.get('audit_status')}")
    lines.append(f"Safety OK: {payload.get('safety_ok')}")
    lines.append("Mode: analytical only")
    lines.append("Orders enabled: False")
    lines.append("Trading enabled: False")
    lines.append("Binance API used: False")
    lines.append("Binance orders created: False")
    lines.append("")

    lines.append("TELEGRAM")
    lines.append("========")
    lines.append(f"Telegram send enabled: {telegram.get('telegram_send_enabled')}")
    lines.append(f"Telegram manual confirm: {telegram.get('telegram_manual_confirm')}")
    lines.append(f"Telegram API used: {telegram.get('telegram_api_used')}")
    lines.append(f"Telegram message sent: {telegram.get('telegram_message_sent')}")
    lines.append(f"Send attempted: {telegram.get('send_attempted')}")
    lines.append(f"Message ID: {telegram.get('message_id')}")
    lines.append(f"Chat ID masked: {telegram.get('chat_id_masked')}")
    lines.append(f"Message length: {telegram.get('message_length')}")
    lines.append(f"Telegram limit: {telegram.get('telegram_limit')}")
    lines.append(f"Message within Telegram limit: {telegram.get('message_within_telegram_limit')}")
    lines.append("")

    lines.append("DECISIONS")
    lines.append("=========")
    lines.append(f"Total decisions: {decisions.get('total_decisions')}")
    lines.append(f"Summary by decision: {decisions.get('summary_by_decision')}")
    lines.append(f"Decision safe to continue: {decisions.get('decision_safe_to_continue')}")
    lines.append("")

    lines.append("TEXT FILES")
    lines.append("==========")
    lines.append(f"Delivery text exists: {delivery_text.get('exists')}")
    lines.append(f"Delivery text path: {delivery_text.get('path')}")
    lines.append(f"Delivery text length: {delivery_text.get('length')}")
    lines.append(f"Delivery notice present: {delivery_text.get('has_delivery_notice')}")
    lines.append(f"Preview notice still present in delivery text: {delivery_text.get('has_preview_notice')}")
    lines.append(f"Orders disabled notice present: {delivery_text.get('has_orders_disabled_notice')}")
    lines.append(f"Not trading signal notice present: {delivery_text.get('has_not_trading_signal_notice')}")
    lines.append(f"Preview text exists: {preview_text.get('exists')}")
    lines.append(f"Preview text path: {preview_text.get('path')}")
    lines.append("")

    lines.append("BLOCKERS")
    lines.append("========")
    blockers = payload.get("blockers", [])

    if blockers:
        for blocker in blockers:
            lines.append(f"- {blocker}")
    else:
        lines.append("none")

    lines.append("")
    lines.append("WARNINGS")
    lines.append("========")
    warnings = payload.get("warnings", [])

    if warnings:
        for warning in warnings:
            lines.append(f"- {warning}")
    else:
        lines.append("none")

    lines.append("")
    lines.append("SAFETY")
    lines.append("======")
    lines.append("[OK] This audit did not send Telegram messages.")
    lines.append("[OK] This audit did not create orders.")
    lines.append("[OK] This audit did not start trading bot.")
    lines.append("[OK] This audit did not call Binance API.")
    lines.append("[OK] This audit only reads existing analytical files.")
    lines.append("")

    return "\n".join(lines)


def save_text(text: str, path: Path = OUTPUT_TXT_PATH) -> Path:
    path.parent.mkdir(exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def print_audit_summary(payload: Dict[str, Any], json_path: Path, txt_path: Path) -> None:
    telegram = payload.get("telegram", {})

    print("SCANNER AGENT TELEGRAM SENDER AUDIT REPORT")
    print("==========================================")
    print("Audit status:", payload.get("audit_status"))
    print("Safety OK:", payload.get("safety_ok"))
    print("Telegram message sent:", telegram.get("telegram_message_sent"))
    print("Telegram API used:", telegram.get("telegram_api_used"))
    print("Message ID:", telegram.get("message_id"))
    print("Message length:", telegram.get("message_length"))
    print("Message within Telegram limit:", telegram.get("message_within_telegram_limit"))
    print("JSON output:", json_path)
    print("TXT output:", txt_path)

    if payload.get("blockers"):
        print("Blockers:", ", ".join(str(item) for item in payload["blockers"]))
    else:
        print("Blockers: none")

    if payload.get("warnings"):
        print("Warnings:", ", ".join(str(item) for item in payload["warnings"]))
    else:
        print("Warnings: none")

    print()
    print("SAFETY")
    print("======")
    print("[OK] This audit did not send Telegram messages.")
    print("[OK] This audit did not create orders.")
    print("[OK] This audit did not start trading bot.")
    print("[OK] This audit did not call Binance API.")


def main() -> None:
    payload = build_audit_payload()
    json_path = save_json(payload)
    txt_path = save_text(build_text_report(payload))
    print_audit_summary(payload, json_path, txt_path)


if __name__ == "__main__":
    main()
