import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


REPORTS_DIR = Path("reports")

PIPELINE_SUMMARY_JSON = REPORTS_DIR / "scanner_agent_pipeline_summary.json"
TELEGRAM_AUDIT_JSON = REPORTS_DIR / "scanner_agent_telegram_sender_audit_report.json"
TELEGRAM_SENDER_RESULT_JSON = REPORTS_DIR / "scanner_agent_telegram_sender_result.json"
TELEGRAM_DRY_RUN_JSON = REPORTS_DIR / "scanner_agent_telegram_sender_dry_run.json"
DECISION_JSON = REPORTS_DIR / "scanner_agent_decision.json"
EXPORT_JSON = REPORTS_DIR / "scanner_agent_export.json"
CHANNEL_QUALITY_JSON = REPORTS_DIR / "telegram_channel_quality_report.json"
CHANNEL_RECOMMENDATIONS_JSON = REPORTS_DIR / "telegram_channel_config_recommendations.json"

OUTPUT_JSON = REPORTS_DIR / "scanner_agent_safety_gate_report.json"
OUTPUT_TXT = REPORTS_DIR / "scanner_agent_safety_gate_report.txt"


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


def unique_strings(items: List[Any]) -> List[str]:
    result: List[str] = []

    for item in items:
        text = str(item).strip()

        if text and text not in result:
            result.append(text)

    return sorted(result)


def collect_file_warnings(files: List[Dict[str, Any]]) -> List[str]:
    warnings: List[str] = []

    for item in files:
        if not item.get("ok"):
            warnings.append(str(item.get("error")))

    return warnings


def build_safety_gate_payload() -> Dict[str, Any]:
    pipeline_file = load_json(PIPELINE_SUMMARY_JSON)
    audit_file = load_json(TELEGRAM_AUDIT_JSON)
    sender_file = load_json(TELEGRAM_SENDER_RESULT_JSON)
    dry_run_file = load_json(TELEGRAM_DRY_RUN_JSON)
    decision_file = load_json(DECISION_JSON)
    export_file = load_json(EXPORT_JSON)
    quality_file = load_json(CHANNEL_QUALITY_JSON)
    recommendations_file = load_json(CHANNEL_RECOMMENDATIONS_JSON)

    pipeline = as_dict(pipeline_file.get("data"))
    audit = as_dict(audit_file.get("data"))
    sender = as_dict(sender_file.get("data"))
    dry_run = as_dict(dry_run_file.get("data"))
    decision = as_dict(decision_file.get("data"))
    export = as_dict(export_file.get("data"))
    quality = as_dict(quality_file.get("data"))
    recommendations = as_dict(recommendations_file.get("data"))

    blockers: List[str] = []
    warnings: List[str] = []

    all_files = [
        pipeline_file,
        audit_file,
        sender_file,
        dry_run_file,
        decision_file,
        export_file,
        quality_file,
        recommendations_file,
    ]

    warnings.extend(collect_file_warnings(all_files))

    for source in [
        pipeline,
        audit,
        sender,
        dry_run,
        decision,
        export,
        quality,
        recommendations,
    ]:
        blockers.extend(as_list(source.get("blockers")))
        warnings.extend(as_list(source.get("warnings")))

    final_status = str(pipeline.get("final_status", "unknown"))
    audit_status = str(audit.get("audit_status", "unknown"))

    safe_pipeline = bool_value(pipeline.get("safe_pipeline"))
    audit_safety_ok = bool_value(audit.get("safety_ok"))

    telegram = as_dict(pipeline.get("telegram"))
    telegram_message_sent = bool_value(telegram.get("telegram_message_sent"))
    duplicate_notification_blocked = bool_value(
        telegram.get("duplicate_notification_blocked")
        or audit.get("duplicate_delivery_text_blocked")
    )

    telegram_delivery_timeout_unknown = bool_value(
        telegram.get("telegram_delivery_timeout_unknown")
        or audit.get("telegram_delivery_timeout_unknown")
        or audit_status == "delivery_unknown"
        or final_status == "telegram_delivery_unknown"
    )

    total_decisions = int(
        as_dict(pipeline.get("decisions")).get("total_decisions")
        or sender.get("total_decisions")
        or decision.get("total_decisions")
        or 0
    )

    dangerous_flags = {
        "orders_enabled": bool_value(sender.get("orders_enabled"))
        or bool_value(pipeline.get("orders_enabled")),
        "trading_enabled": bool_value(sender.get("trading_enabled"))
        or bool_value(pipeline.get("trading_enabled")),
        "binance_api_used": bool_value(sender.get("binance_api_used"))
        or bool_value(pipeline.get("binance_api_used")),
        "binance_orders_created": bool_value(sender.get("binance_orders_created"))
        or bool_value(pipeline.get("binance_orders_created")),
    }

    if any(dangerous_flags.values()):
        blockers.append("dangerous_runtime_flag_detected")

    if not safe_pipeline:
        blockers.append("pipeline_summary_not_safe")

    if not audit_safety_ok and not telegram_delivery_timeout_unknown:
        blockers.append("telegram_audit_not_safe")

    quality_safe = bool_value(quality.get("safe_to_continue", True))
    recommendations_safe = bool_value(recommendations.get("safe_to_continue", True))

    if not quality_safe:
        warnings.append("channel_quality_report_requires_review")

    if not recommendations_safe:
        warnings.append("channel_recommendations_require_review")

    if duplicate_notification_blocked:
        blockers = [
            blocker
            for blocker in blockers
            if blocker != "duplicate_delivery_text_hash"
        ]
        warnings = [
            warning
            for warning in warnings
            if warning != "send_not_attempted_because_duplicate_delivery_text"
        ]

    if telegram_delivery_timeout_unknown:
        blockers = [
            blocker
            for blocker in blockers
            if blocker not in {
                "telegram_delivery_timeout_unknown",
                "telegram_send_failed",
                "send_attempted_but_message_not_sent",
                "telegram_audit_not_safe",
            }
        ]
        if "manual_telegram_chat_check_required" not in warnings:
            warnings.append("manual_telegram_chat_check_required")

    failed_statuses = {
        "notification_failed",
        "send_attempt_failed",
    }

    safe_terminal_statuses = {
        "notification_sent",
        "duplicate_notification_blocked",
        "no_decisions",
        "no_signals",
        "all_signals_blocked",
    }

    if any(dangerous_flags.values()):
        gate_status = "blocked"
        gate_note = "Dangerous runtime flag detected. Manual review is required."
    elif final_status in failed_statuses or audit_status in failed_statuses:
        gate_status = "failed"
        gate_note = "Pipeline or Telegram sender reported a failed notification attempt."
    elif blockers:
        gate_status = "blocked"
        gate_note = "Blocking conditions were found. Do not proceed until reviewed."
    elif duplicate_notification_blocked:
        gate_status = "duplicate_blocked"
        gate_note = "Duplicate analytical Telegram notification was safely blocked."
    elif telegram_delivery_timeout_unknown:
        gate_status = "review_required"
        gate_note = "Telegram delivery status is unknown after timeout. Check Telegram chat manually before rerun."
    elif final_status == "notification_sent" and telegram_message_sent:
        gate_status = "safe"
        gate_note = "Analytical notification was sent safely. Orders remained disabled."
    elif final_status in safe_terminal_statuses:
        gate_status = "safe"
        gate_note = "Pipeline ended in a safe analytical state. Orders remained disabled."
    else:
        gate_status = "review_required"
        gate_note = "Pipeline is not blocked, but the final state requires manual review."

    review_required = gate_status == "review_required" or bool(warnings)

    if gate_status == "safe" and review_required:
        gate_status = "review_required"
        gate_note = "Pipeline is safe, but warnings require manual review."

    safety_gate_ok = gate_status in {"safe", "duplicate_blocked"}

    return {
        "source": "scanner_agent_safety_gate_report",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "gate_status": gate_status,
        "gate_note": gate_note,
        "safety_gate_ok": safety_gate_ok,
        "review_required": review_required,
        "analytical_only": True,
        "orders_enabled": False,
        "trading_enabled": False,
        "binance_api_used": False,
        "binance_orders_created": False,
        "dangerous_flags": dangerous_flags,
        "pipeline": {
            "final_status": final_status,
            "final_note": pipeline.get("final_note"),
            "safe_pipeline": safe_pipeline,
            "total_decisions": total_decisions,
            "telegram_message_sent": telegram_message_sent,
            "duplicate_notification_blocked": duplicate_notification_blocked,
            "telegram_delivery_timeout_unknown": telegram_delivery_timeout_unknown,
        },
        "telegram_audit": {
            "audit_status": audit_status,
            "safety_ok": audit_safety_ok,
            "duplicate_delivery_text_blocked": bool_value(
                audit.get("duplicate_delivery_text_blocked")
            ),
            "telegram_delivery_timeout_unknown": telegram_delivery_timeout_unknown,
        },
        "channel_quality": {
            "safe_to_continue": quality_safe,
            "channels_analyzed": quality.get("channels_analyzed"),
            "keep": quality.get("channels_keep"),
            "watch": quality.get("channels_watch"),
            "disable": quality.get("channels_disable"),
        },
        "channel_recommendations": {
            "safe_to_continue": recommendations_safe,
            "scanner_real_channels_modified": recommendations.get(
                "scanner_real_channels_modified"
            ),
            "keep": recommendations.get("keep"),
            "watch": recommendations.get("watch"),
            "disable": recommendations.get("disable"),
        },
        "files": {
            "pipeline_summary": {
                "path": str(PIPELINE_SUMMARY_JSON),
                "ok": pipeline_file.get("ok"),
                "error": pipeline_file.get("error"),
            },
            "telegram_audit": {
                "path": str(TELEGRAM_AUDIT_JSON),
                "ok": audit_file.get("ok"),
                "error": audit_file.get("error"),
            },
            "telegram_sender_result": {
                "path": str(TELEGRAM_SENDER_RESULT_JSON),
                "ok": sender_file.get("ok"),
                "error": sender_file.get("error"),
            },
            "telegram_dry_run": {
                "path": str(TELEGRAM_DRY_RUN_JSON),
                "ok": dry_run_file.get("ok"),
                "error": dry_run_file.get("error"),
            },
            "decision": {
                "path": str(DECISION_JSON),
                "ok": decision_file.get("ok"),
                "error": decision_file.get("error"),
            },
            "export": {
                "path": str(EXPORT_JSON),
                "ok": export_file.get("ok"),
                "error": export_file.get("error"),
            },
            "channel_quality": {
                "path": str(CHANNEL_QUALITY_JSON),
                "ok": quality_file.get("ok"),
                "error": quality_file.get("error"),
            },
            "channel_recommendations": {
                "path": str(CHANNEL_RECOMMENDATIONS_JSON),
                "ok": recommendations_file.get("ok"),
                "error": recommendations_file.get("error"),
            },
        },
        "blockers": unique_strings(blockers),
        "warnings": unique_strings(warnings),
        "disclaimer": (
            "This safety gate only reads local analytical report files. "
            "It does not send Telegram messages, does not create orders, "
            "does not start trading, and does not call Binance API."
        ),
    }


def save_json(payload: Dict[str, Any], path: Path = OUTPUT_JSON) -> Path:
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def build_text_report(payload: Dict[str, Any]) -> str:
    pipeline = payload.get("pipeline", {})
    audit = payload.get("telegram_audit", {})
    quality = payload.get("channel_quality", {})
    recommendations = payload.get("channel_recommendations", {})
    dangerous_flags = payload.get("dangerous_flags", {})

    lines: List[str] = []

    lines.append("SCANNER AGENT SAFETY GATE REPORT")
    lines.append("================================")
    lines.append(f"Created at: {payload.get('created_at')}")
    lines.append("")
    lines.append(f"Gate status: {payload.get('gate_status')}")
    lines.append(f"Gate note: {payload.get('gate_note')}")
    lines.append(f"Safety gate OK: {payload.get('safety_gate_ok')}")
    lines.append(f"Review required: {payload.get('review_required')}")
    lines.append("")

    lines.append("PIPELINE")
    lines.append("========")
    lines.append(f"Final status: {pipeline.get('final_status')}")
    lines.append(f"Final note: {pipeline.get('final_note')}")
    lines.append(f"Safe pipeline: {pipeline.get('safe_pipeline')}")
    lines.append(f"Total decisions: {pipeline.get('total_decisions')}")
    lines.append(f"Telegram message sent: {pipeline.get('telegram_message_sent')}")
    lines.append(f"Duplicate notification blocked: {pipeline.get('duplicate_notification_blocked')}")
    lines.append(f"Telegram delivery timeout unknown: {pipeline.get('telegram_delivery_timeout_unknown')}")
    lines.append("")

    lines.append("TELEGRAM AUDIT")
    lines.append("==============")
    lines.append(f"Audit status: {audit.get('audit_status')}")
    lines.append(f"Audit safety OK: {audit.get('safety_ok')}")
    lines.append(f"Duplicate delivery text blocked: {audit.get('duplicate_delivery_text_blocked')}")
    lines.append(f"Telegram delivery timeout unknown: {audit.get('telegram_delivery_timeout_unknown')}")
    lines.append("")

    lines.append("DANGEROUS FLAGS")
    lines.append("===============")
    lines.append(f"Orders enabled: {dangerous_flags.get('orders_enabled')}")
    lines.append(f"Trading enabled: {dangerous_flags.get('trading_enabled')}")
    lines.append(f"Binance API used: {dangerous_flags.get('binance_api_used')}")
    lines.append(f"Binance orders created: {dangerous_flags.get('binance_orders_created')}")
    lines.append("")

    lines.append("CHANNEL QUALITY")
    lines.append("===============")
    lines.append(f"Safe to continue: {quality.get('safe_to_continue')}")
    lines.append(f"Channels analyzed: {quality.get('channels_analyzed')}")
    lines.append(f"Keep: {quality.get('keep')}")
    lines.append(f"Watch: {quality.get('watch')}")
    lines.append(f"Disable: {quality.get('disable')}")
    lines.append("")

    lines.append("CHANNEL RECOMMENDATIONS")
    lines.append("=======================")
    lines.append(f"Safe to continue: {recommendations.get('safe_to_continue')}")
    lines.append(f"scanner_real_channels.py modified: {recommendations.get('scanner_real_channels_modified')}")
    lines.append(f"Keep: {recommendations.get('keep')}")
    lines.append(f"Watch: {recommendations.get('watch')}")
    lines.append(f"Disable: {recommendations.get('disable')}")
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
    lines.append("[OK] This safety gate did not send Telegram messages.")
    lines.append("[OK] This safety gate did not create orders.")
    lines.append("[OK] This safety gate did not start trading bot.")
    lines.append("[OK] This safety gate did not call Binance API.")
    lines.append("[OK] This safety gate only reads existing analytical reports.")
    lines.append("")

    return "\n".join(lines)


def save_text(text: str, path: Path = OUTPUT_TXT) -> Path:
    path.parent.mkdir(exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def print_gate_summary(payload: Dict[str, Any], json_path: Path, txt_path: Path) -> None:
    print("SCANNER AGENT SAFETY GATE REPORT")
    print("================================")
    print("Gate status:", payload.get("gate_status"))
    print("Gate note:", payload.get("gate_note"))
    print("Safety gate OK:", payload.get("safety_gate_ok"))
    print("Review required:", payload.get("review_required"))
    print("Pipeline final status:", payload.get("pipeline", {}).get("final_status"))
    print("Telegram audit status:", payload.get("telegram_audit", {}).get("audit_status"))
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
    print("[OK] This safety gate did not send Telegram messages.")
    print("[OK] This safety gate did not create orders.")
    print("[OK] This safety gate did not start trading bot.")
    print("[OK] This safety gate did not call Binance API.")


def main() -> None:
    payload = build_safety_gate_payload()
    json_path = save_json(payload)
    txt_path = save_text(build_text_report(payload))
    print_gate_summary(payload, json_path, txt_path)


if __name__ == "__main__":
    main()
