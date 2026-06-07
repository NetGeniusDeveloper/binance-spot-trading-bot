import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


REPORTS_DIR = Path("reports")

EXPORT_PATH = REPORTS_DIR / "scanner_agent_export.json"
DECISION_PATH = REPORTS_DIR / "scanner_agent_decision.json"
TELEGRAM_SENDER_DRY_RUN_PATH = REPORTS_DIR / "scanner_agent_telegram_sender_dry_run.json"
TELEGRAM_SENDER_RESULT_PATH = REPORTS_DIR / "scanner_agent_telegram_sender_result.json"
OUTPUT_PATH = REPORTS_DIR / "scanner_agent_pipeline_summary.json"
OUTPUT_TXT_PATH = REPORTS_DIR / "scanner_agent_pipeline_summary.txt"


def load_json_file(path: Path) -> Dict[str, Any]:
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


def as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value

    return []


def as_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value

    return {}


def bool_value(value: Any) -> bool:
    return bool(value)


def build_summary_payload() -> Dict[str, Any]:
    export_file = load_json_file(EXPORT_PATH)
    decision_file = load_json_file(DECISION_PATH)
    dry_run_file = load_json_file(TELEGRAM_SENDER_DRY_RUN_PATH)
    sender_file = load_json_file(TELEGRAM_SENDER_RESULT_PATH)

    export_data = as_dict(export_file.get("data"))
    decision_data = as_dict(decision_file.get("data"))
    dry_run_data = as_dict(dry_run_file.get("data"))
    sender_data = as_dict(sender_file.get("data"))

    candidates = as_list(export_data.get("candidates"))
    watchlist_candidates = as_list(export_data.get("watchlist_candidates"))
    decisions = as_list(decision_data.get("decisions"))

    blockers: List[str] = []
    warnings: List[str] = []

    for loaded_file in [export_file, decision_file, dry_run_file, sender_file]:
        if not loaded_file.get("ok"):
            warnings.append(str(loaded_file.get("error")))

    for source_data in [dry_run_data, sender_data]:
        source_blockers = source_data.get("blockers", [])
        source_warnings = source_data.get("warnings", [])

        if isinstance(source_blockers, list):
            blockers.extend(str(item) for item in source_blockers if str(item).strip())

        if isinstance(source_warnings, list):
            warnings.extend(str(item) for item in source_warnings if str(item).strip())

    total_signals_loaded = int(export_data.get("total_signals_loaded") or 0)
    blocked_signals = int(export_data.get("blocked_signals") or 0)
    ignored_signals = int(export_data.get("ignored_signals") or 0)

    total_candidates = int(export_data.get("total_candidates") or len(candidates) or 0)
    total_watchlist_candidates = int(
        export_data.get("total_watchlist_candidates") or len(watchlist_candidates) or 0
    )

    total_decisions = int(decision_data.get("total_decisions") or len(decisions) or 0)

    sender_result_ignored_because_no_decisions = total_decisions <= 0

    if sender_result_ignored_because_no_decisions:
        dry_run_data = {}
        sender_data = {}
        blockers = []
        warnings = [
            warning
            for warning in warnings
            if "scanner_telegram_" not in str(warning)
            and "send_not_attempted" not in str(warning)
        ]

    telegram_send_enabled = bool_value(sender_data.get("telegram_send_enabled", False))
    telegram_manual_confirm = bool_value(sender_data.get("telegram_manual_confirm", False))

    scanner_telegram_send_enabled = bool_value(
        dry_run_data.get("scanner_telegram_send_enabled", telegram_send_enabled)
    )
    scanner_telegram_manual_confirm = bool_value(
        dry_run_data.get("scanner_telegram_manual_confirm", telegram_manual_confirm)
    )

    ready_for_real_sender_now = bool_value(
        dry_run_data.get("ready_for_real_sender_now", False)
    )
    would_send_if_enabled = bool_value(
        dry_run_data.get("would_send_if_enabled", False)
    )

    telegram_api_used = bool_value(sender_data.get("telegram_api_used", False))
    telegram_message_sent = bool_value(sender_data.get("telegram_message_sent", False))
    send_attempted = bool_value(sender_data.get("send_attempted", False))

    if total_signals_loaded <= 0:
        final_status = "no_signals"
        final_note = "No scanner signals were loaded."
    elif blocked_signals == total_signals_loaded and total_decisions <= 0:
        final_status = "all_signals_blocked"
        final_note = "All scanner signals were blocked or skipped. Telegram sending should stay inactive."
    elif total_decisions <= 0:
        final_status = "no_decisions"
        final_note = "Scanner produced signals, but no analytical decisions were selected."
    elif telegram_message_sent:
        final_status = "notification_sent"
        final_note = "Analytical Telegram notification was sent. Orders remained disabled."
    elif send_attempted and not telegram_message_sent:
        final_status = "notification_failed"
        final_note = "Telegram sending was attempted but failed. Check sender result."
    elif ready_for_real_sender_now and total_decisions > 0:
        final_status = "ready_for_real_sender"
        final_note = "Decisions exist and both Telegram manual flags are enabled. Real sender may send if executed."
    elif would_send_if_enabled and total_decisions > 0:
        final_status = "ready_for_manual_review"
        final_note = "Decisions exist, but one or both Telegram manual flags are disabled. Review reports manually."
    else:
        final_status = "ready_for_manual_review"
        final_note = "Decisions exist. Telegram sending is disabled or skipped. Review reports manually."

    safe_pipeline = (
        bool(export_data.get("analytical_only", True))
        and bool(decision_data.get("analytical_only", True))
        and bool(dry_run_data.get("analytical_only", True) if dry_run_data else True)
        and bool(sender_data.get("analytical_only", True) if sender_data else True)
        and not bool(sender_data.get("orders_enabled", False))
        and not bool(sender_data.get("trading_enabled", False))
        and not bool(sender_data.get("binance_api_used", False))
        and not bool(sender_data.get("binance_orders_created", False))
    )

    return {
        "source": "scanner_agent_pipeline_summary",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analytical_only": True,
        "orders_enabled": False,
        "trading_enabled": False,
        "binance_orders_created": False,
        "safe_pipeline": safe_pipeline,
        "final_status": final_status,
        "final_note": final_note,
        "files": {
            "agent_export": {
                "path": str(EXPORT_PATH),
                "ok": export_file.get("ok"),
                "error": export_file.get("error"),
            },
            "agent_decision": {
                "path": str(DECISION_PATH),
                "ok": decision_file.get("ok"),
                "error": decision_file.get("error"),
            },
            "telegram_sender_dry_run": {
                "path": str(TELEGRAM_SENDER_DRY_RUN_PATH),
                "ok": dry_run_file.get("ok"),
                "error": dry_run_file.get("error"),
            },
            "telegram_sender_result": {
                "path": str(TELEGRAM_SENDER_RESULT_PATH),
                "ok": sender_file.get("ok"),
                "error": sender_file.get("error"),
            },
        },
        "scanner": {
            "total_signals_loaded": total_signals_loaded,
            "blocked_signals": blocked_signals,
            "ignored_signals": ignored_signals,
            "total_candidates": total_candidates,
            "total_watchlist_candidates": total_watchlist_candidates,
        },
        "decisions": {
            "total_decisions": total_decisions,
            "summary_by_decision": decision_data.get("summary_by_decision", {}),
        },
        "telegram": {
            "sender_result_ignored_because_no_decisions": sender_result_ignored_because_no_decisions,
            "telegram_send_enabled": telegram_send_enabled,
            "telegram_manual_confirm": telegram_manual_confirm,
            "scanner_telegram_send_enabled": scanner_telegram_send_enabled,
            "scanner_telegram_manual_confirm": scanner_telegram_manual_confirm,
            "ready_for_real_sender_now": ready_for_real_sender_now,
            "would_send_if_enabled": would_send_if_enabled,
            "telegram_api_used": telegram_api_used,
            "telegram_message_sent": telegram_message_sent,
            "send_attempted": send_attempted,
            "message_length": sender_data.get("message_length"),
            "message_within_telegram_limit": sender_data.get("message_within_telegram_limit"),
        },
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "disclaimer": (
            "This is a final analytical pipeline summary. "
            "It does not create orders, does not start trading, "
            "does not call Binance API, and does not send Telegram messages."
        ),
    }


def save_json_summary(payload: Dict[str, Any], path: Path = OUTPUT_PATH) -> Path:
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


def build_text_summary(payload: Dict[str, Any]) -> str:
    scanner = payload.get("scanner", {})
    decisions = payload.get("decisions", {})
    telegram = payload.get("telegram", {})

    lines: List[str] = []

    lines.append("SCANNER AGENT PIPELINE SUMMARY")
    lines.append("==============================")
    lines.append(f"Created at: {payload.get('created_at')}")
    lines.append("")
    lines.append(f"Final status: {payload.get('final_status')}")
    lines.append(f"Final note: {payload.get('final_note')}")
    lines.append(f"Safe pipeline: {payload.get('safe_pipeline')}")
    lines.append("")

    lines.append("SCANNER")
    lines.append("=======")
    lines.append(f"Total signals loaded: {scanner.get('total_signals_loaded')}")
    lines.append(f"Blocked signals: {scanner.get('blocked_signals')}")
    lines.append(f"Ignored signals: {scanner.get('ignored_signals')}")
    lines.append(f"Candidates: {scanner.get('total_candidates')}")
    lines.append(f"Watchlist candidates: {scanner.get('total_watchlist_candidates')}")
    lines.append("")

    lines.append("DECISIONS")
    lines.append("=========")
    lines.append(f"Total decisions: {decisions.get('total_decisions')}")
    lines.append(f"Summary by decision: {decisions.get('summary_by_decision')}")
    lines.append("")

    lines.append("TELEGRAM")
    lines.append("========")
    lines.append(f"Sender result ignored because no decisions: {telegram.get('sender_result_ignored_because_no_decisions')}")
    lines.append(f"Telegram send enabled: {telegram.get('telegram_send_enabled')}")
    lines.append(f"Telegram manual confirm: {telegram.get('telegram_manual_confirm')}")
    lines.append(f"Scanner Telegram send enabled: {telegram.get('scanner_telegram_send_enabled')}")
    lines.append(f"Scanner Telegram manual confirm: {telegram.get('scanner_telegram_manual_confirm')}")
    lines.append(f"Ready for real sender now: {telegram.get('ready_for_real_sender_now')}")
    lines.append(f"Would send if enabled: {telegram.get('would_send_if_enabled')}")
    lines.append(f"Telegram API used: {telegram.get('telegram_api_used')}")
    lines.append(f"Telegram message sent: {telegram.get('telegram_message_sent')}")
    lines.append(f"Send attempted: {telegram.get('send_attempted')}")
    lines.append(f"Message length: {telegram.get('message_length')}")
    lines.append(f"Message within Telegram limit: {telegram.get('message_within_telegram_limit')}")
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
    lines.append("[OK] This summary did not create orders.")
    lines.append("[OK] This summary did not start trading bot.")
    lines.append("[OK] This summary did not call Binance API.")
    lines.append("[OK] This summary did not send Telegram messages.")
    lines.append("[OK] This summary only reads existing analytical report files.")
    lines.append("[OK] Real Telegram delivery requires two manual flags.")
    lines.append("")

    return "\n".join(lines)


def save_text_summary(text: str, path: Path = OUTPUT_TXT_PATH) -> Path:
    path.parent.mkdir(exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def print_summary(payload: Dict[str, Any], json_path: Path, txt_path: Path) -> None:
    print("SCANNER AGENT PIPELINE SUMMARY")
    print("==============================")
    print("Mode: analytical only")
    print("Orders enabled:", payload.get("orders_enabled"))
    print("Trading enabled:", payload.get("trading_enabled"))
    print("Binance orders created:", payload.get("binance_orders_created"))
    print("Safe pipeline:", payload.get("safe_pipeline"))
    print("Final status:", payload.get("final_status"))
    print("Final note:", payload.get("final_note"))
    print("JSON output:", json_path)
    print("TXT output:", txt_path)
    print()

    scanner = payload.get("scanner", {})
    decisions = payload.get("decisions", {})
    telegram = payload.get("telegram", {})

    print("SUMMARY")
    print("=======")
    print("Signals loaded:", scanner.get("total_signals_loaded"))
    print("Blocked signals:", scanner.get("blocked_signals"))
    print("Candidates:", scanner.get("total_candidates"))
    print("Watchlist:", scanner.get("total_watchlist_candidates"))
    print("Decisions:", decisions.get("total_decisions"))
    print("Sender result ignored because no decisions:", telegram.get("sender_result_ignored_because_no_decisions"))
    print("Telegram send enabled:", telegram.get("telegram_send_enabled"))
    print("Telegram manual confirm:", telegram.get("telegram_manual_confirm"))
    print("Ready for real sender now:", telegram.get("ready_for_real_sender_now"))
    print("Would send if enabled:", telegram.get("would_send_if_enabled"))
    print("Telegram message sent:", telegram.get("telegram_message_sent"))

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
    print("[OK] This summary did not create orders.")
    print("[OK] This summary did not start trading bot.")
    print("[OK] This summary did not call Binance API.")
    print("[OK] This summary did not send Telegram messages.")
    print("[OK] This summary only reads existing analytical files.")
    print("[OK] Real Telegram delivery requires two manual flags.")


def main() -> None:
    payload = build_summary_payload()
    json_path = save_json_summary(payload)
    txt_path = save_text_summary(build_text_summary(payload))
    print_summary(payload, json_path, txt_path)


if __name__ == "__main__":
    main()
