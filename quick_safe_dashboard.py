import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


REPORTS_DIR = Path("reports")

OUTPUT_JSON_PATH = REPORTS_DIR / "quick_safe_dashboard.json"
OUTPUT_TXT_PATH = REPORTS_DIR / "quick_safe_dashboard.txt"

REPORT_PATHS = {
    "pipeline": REPORTS_DIR / "scanner_agent_pipeline_summary.json",
    "safety_gate": REPORTS_DIR / "scanner_agent_safety_gate_report.json",
    "risk_filter_backtest": REPORTS_DIR / "scanner_agent_risk_filter_backtest.json",
    "scenario_matrix": REPORTS_DIR / "scanner_agent_scenario_matrix_report.json",
    "blocked_risk": REPORTS_DIR / "scanner_agent_blocked_risk_report.json",
    "watchlist": REPORTS_DIR / "scanner_agent_watchlist_report.json",
    "telegram_audit": REPORTS_DIR / "scanner_agent_telegram_sender_audit_report.json",
}


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {
            "ok": False,
            "path": str(path),
            "error": "file_not_found",
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
            "error": f"invalid_json: {ex}",
            "data": {},
        }
    except OSError as ex:
        return {
            "ok": False,
            "path": str(path),
            "error": f"read_error: {ex}",
            "data": {},
        }


def as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def format_bool(value: Any) -> str:
    if value is True:
        return "True"
    if value is False:
        return "False"
    if value is None:
        return "n/a"
    return str(value)


def format_list(value: Any) -> str:
    items = [str(item) for item in as_list(value) if str(item).strip()]
    return ", ".join(items) if items else "none"


def get_nested(payload: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = payload

    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)

    return default if current is None else current


def build_payload() -> Dict[str, Any]:
    loaded_reports = {
        name: load_json(path)
        for name, path in REPORT_PATHS.items()
    }

    pipeline = as_dict(loaded_reports["pipeline"].get("data"))
    safety_gate = as_dict(loaded_reports["safety_gate"].get("data"))
    risk_filter = as_dict(loaded_reports["risk_filter_backtest"].get("data"))
    scenario_matrix = as_dict(loaded_reports["scenario_matrix"].get("data"))
    blocked_risk = as_dict(loaded_reports["blocked_risk"].get("data"))
    watchlist = as_dict(loaded_reports["watchlist"].get("data"))
    telegram_audit = as_dict(loaded_reports["telegram_audit"].get("data"))

    critical_reports = [
        "pipeline",
        "safety_gate",
        "risk_filter_backtest",
        "scenario_matrix",
        "blocked_risk",
        "watchlist",
    ]

    missing_or_invalid = [
        name
        for name in critical_reports
        if not loaded_reports[name].get("ok")
    ]

    telegram = as_dict(pipeline.get("telegram"))
    decisions = as_dict(pipeline.get("decisions"))
    scanner = as_dict(pipeline.get("scanner"))

    dangerous_flags = as_dict(safety_gate.get("dangerous_flags"))

    blockers: List[str] = []

    if missing_or_invalid:
        blockers.append("critical_reports_missing_or_invalid")

    if pipeline and pipeline.get("safe_pipeline") is not True:
        blockers.append("pipeline_not_safe")

    if safety_gate and safety_gate.get("safety_gate_ok") is not True:
        blockers.append("safety_gate_not_ok")

    if risk_filter and risk_filter.get("safe_to_continue") is not True:
        blockers.append("risk_filter_not_safe")

    if risk_filter and risk_filter.get("synthetic_scenarios_ok") is not True:
        blockers.append("risk_filter_synthetic_scenarios_failed")

    if scenario_matrix and scenario_matrix.get("safe_to_continue") is not True:
        blockers.append("scenario_matrix_not_safe")

    if scenario_matrix and scenario_matrix.get("failed_count") not in (0, None):
        blockers.append("scenario_matrix_has_failed_rows")

    if scenario_matrix and scenario_matrix.get("unsafe_runtime_count") not in (0, None):
        blockers.append("scenario_matrix_has_unsafe_runtime_rows")

    for key in [
        "orders_enabled",
        "trading_enabled",
        "binance_orders_created",
        "binance_api_used",
    ]:
        if dangerous_flags.get(key) is True:
            blockers.append(f"dangerous_flag:{key}")

    telegram_message_sent = telegram.get("telegram_message_sent")
    telegram_api_used = telegram.get("telegram_api_used")
    audit_safety_ok = telegram_audit.get("safety_ok")

    if telegram_message_sent is True:
        blockers.append("telegram_message_was_sent")

    if telegram_api_used is True:
        blockers.append("telegram_api_was_used")

    if telegram_audit and audit_safety_ok is not True:
        blockers.append("telegram_audit_not_safe")

    warnings: List[str] = []

    for name, loaded in loaded_reports.items():
        if not loaded.get("ok"):
            warnings.append(f"{name}:{loaded.get('error')}")

    warnings.extend(str(item) for item in as_list(pipeline.get("warnings")))
    warnings.extend(str(item) for item in as_list(safety_gate.get("warnings")))
    warnings.extend(str(item) for item in as_list(risk_filter.get("warnings")))
    warnings.extend(str(item) for item in as_list(scenario_matrix.get("warnings")))

    unique_warnings = sorted(set(item for item in warnings if item))

    dashboard = {
        "pipeline_status": pipeline.get("final_status"),
        "safe_pipeline": pipeline.get("safe_pipeline"),
        "signals_loaded": scanner.get("total_signals_loaded"),
        "decisions_total": decisions.get("total_decisions"),
        "safety_gate_status": safety_gate.get("gate_status"),
        "safety_gate_ok": safety_gate.get("safety_gate_ok"),
        "review_required": safety_gate.get("review_required"),
        "risk_filter_safe": risk_filter.get("safe_to_continue"),
        "risk_filter_decisions": risk_filter.get("total_decisions"),
        "risk_filter_buckets": risk_filter.get("summary_by_bucket"),
        "risk_filter_synthetic_ok": risk_filter.get("synthetic_scenarios_ok"),
        "risk_filter_synthetic_count": risk_filter.get("synthetic_scenario_count"),
        "risk_filter_synthetic_failed": risk_filter.get("synthetic_scenario_failed_count"),
        "scenario_matrix_safe": scenario_matrix.get("safe_to_continue"),
        "scenario_matrix_count": scenario_matrix.get("scenario_count"),
        "scenario_matrix_failed": scenario_matrix.get("failed_count"),
        "scenario_matrix_unsafe_runtime": scenario_matrix.get("unsafe_runtime_count"),
        "scenario_matrix_result_summary": scenario_matrix.get("summary_by_result"),
        "scenario_matrix_bucket_summary": scenario_matrix.get("summary_by_actual_bucket"),
        "telegram_send_enabled": telegram.get("telegram_send_enabled"),
        "telegram_manual_confirm": telegram.get("telegram_manual_confirm"),
        "scanner_telegram_send_enabled": telegram.get("scanner_telegram_send_enabled"),
        "scanner_telegram_manual_confirm": telegram.get("scanner_telegram_manual_confirm"),
        "telegram_message_sent": telegram_message_sent,
        "telegram_api_used": telegram_api_used,
        "telegram_send_attempted": telegram.get("send_attempted"),
        "telegram_would_send_if_enabled": telegram.get("would_send_if_enabled"),
        "telegram_audit_status": telegram_audit.get("audit_status"),
        "telegram_audit_safety_ok": audit_safety_ok,
        "blocked_risk_count": blocked_risk.get("blocked_count"),
        "blocked_risk_levels": blocked_risk.get("summary_by_risk_level"),
        "blocked_risk_flags": blocked_risk.get("summary_by_risk_flag"),
        "watchlist_count": watchlist.get("watchlist_count"),
        "watchlist_statuses": watchlist.get("summary_by_watch_status"),
        "watchlist_decisions": watchlist.get("summary_by_decision"),
    }

    return {
        "source": "quick_safe_dashboard",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "output_json": str(OUTPUT_JSON_PATH),
        "output_txt": str(OUTPUT_TXT_PATH),
        "analytical_only": True,
        "orders_enabled": False,
        "order_execution_allowed": False,
        "trading_enabled": False,
        "telegram_sending": False,
        "binance_private_api_used": False,
        "safe_to_continue": not blockers,
        "loaded_reports": {
            name: {
                "ok": loaded.get("ok"),
                "path": loaded.get("path"),
                "error": loaded.get("error"),
            }
            for name, loaded in loaded_reports.items()
        },
        "dashboard": dashboard,
        "blockers": blockers,
        "warnings": unique_warnings,
        "disclaimer": (
            "This dashboard is analytical only. It reads existing JSON reports, "
            "does not create orders, does not start trading, does not call Binance private API, "
            "and does not send Telegram messages."
        ),
    }


def build_text_report(payload: Dict[str, Any]) -> str:
    dashboard = as_dict(payload.get("dashboard"))
    lines: List[str] = []

    lines.append("QUICK SAFE DASHBOARD")
    lines.append("====================")
    lines.append(f"Created at: {payload.get('created_at')}")
    lines.append(f"Safe to continue: {payload.get('safe_to_continue')}")
    lines.append(f"Blockers: {format_list(payload.get('blockers'))}")
    lines.append(f"Warnings: {format_list(payload.get('warnings'))}")
    lines.append("")

    lines.append("PIPELINE")
    lines.append("========")
    lines.append(f"Status: {dashboard.get('pipeline_status')}")
    lines.append(f"Safe pipeline: {format_bool(dashboard.get('safe_pipeline'))}")
    lines.append(f"Signals loaded: {dashboard.get('signals_loaded')}")
    lines.append(f"Decisions total: {dashboard.get('decisions_total')}")
    lines.append("")

    lines.append("SAFETY GATE")
    lines.append("===========")
    lines.append(f"Gate status: {dashboard.get('safety_gate_status')}")
    lines.append(f"Safety gate OK: {format_bool(dashboard.get('safety_gate_ok'))}")
    lines.append(f"Review required: {format_bool(dashboard.get('review_required'))}")
    lines.append("")

    lines.append("RISK FILTER BACKTEST")
    lines.append("====================")
    lines.append(f"Safe: {format_bool(dashboard.get('risk_filter_safe'))}")
    lines.append(f"Decisions: {dashboard.get('risk_filter_decisions')}")
    lines.append(f"Buckets: {dashboard.get('risk_filter_buckets')}")
    lines.append(f"Synthetic OK: {format_bool(dashboard.get('risk_filter_synthetic_ok'))}")
    lines.append(f"Synthetic count: {dashboard.get('risk_filter_synthetic_count')}")
    lines.append(f"Synthetic failed: {dashboard.get('risk_filter_synthetic_failed')}")
    lines.append("")

    lines.append("SCENARIO MATRIX")
    lines.append("===============")
    lines.append(f"Safe: {format_bool(dashboard.get('scenario_matrix_safe'))}")
    lines.append(f"Count: {dashboard.get('scenario_matrix_count')}")
    lines.append(f"Failed: {dashboard.get('scenario_matrix_failed')}")
    lines.append(f"Unsafe runtime: {dashboard.get('scenario_matrix_unsafe_runtime')}")
    lines.append(f"Result summary: {dashboard.get('scenario_matrix_result_summary')}")
    lines.append(f"Bucket summary: {dashboard.get('scenario_matrix_bucket_summary')}")
    lines.append("")

    lines.append("TELEGRAM")
    lines.append("========")
    lines.append(f"Telegram send enabled: {format_bool(dashboard.get('telegram_send_enabled'))}")
    lines.append(f"Telegram manual confirm: {format_bool(dashboard.get('telegram_manual_confirm'))}")
    lines.append(f"Scanner Telegram send enabled: {format_bool(dashboard.get('scanner_telegram_send_enabled'))}")
    lines.append(f"Scanner Telegram manual confirm: {format_bool(dashboard.get('scanner_telegram_manual_confirm'))}")
    lines.append(f"Would send if enabled: {format_bool(dashboard.get('telegram_would_send_if_enabled'))}")
    lines.append(f"Send attempted: {format_bool(dashboard.get('telegram_send_attempted'))}")
    lines.append(f"Telegram message sent: {format_bool(dashboard.get('telegram_message_sent'))}")
    lines.append(f"Telegram API used: {format_bool(dashboard.get('telegram_api_used'))}")
    lines.append(f"Telegram audit status: {dashboard.get('telegram_audit_status')}")
    lines.append(f"Telegram audit safety OK: {format_bool(dashboard.get('telegram_audit_safety_ok'))}")
    lines.append("")

    lines.append("BLOCKED / WATCHLIST")
    lines.append("===================")
    lines.append(f"Blocked risk count: {dashboard.get('blocked_risk_count')}")
    lines.append(f"Blocked risk levels: {dashboard.get('blocked_risk_levels')}")
    lines.append(f"Blocked risk flags: {dashboard.get('blocked_risk_flags')}")
    lines.append(f"Watchlist count: {dashboard.get('watchlist_count')}")
    lines.append(f"Watchlist statuses: {dashboard.get('watchlist_statuses')}")
    lines.append(f"Watchlist decisions: {dashboard.get('watchlist_decisions')}")
    lines.append("")

    lines.append("SAFETY")
    lines.append("======")
    lines.append("Analytical only: True")
    lines.append("Orders enabled: False")
    lines.append("Order execution allowed: False")
    lines.append("Trading enabled: False")
    lines.append("Telegram sending: False")
    lines.append("Binance private API used: False")
    lines.append("")
    lines.append("FINAL NOTE")
    lines.append("==========")
    lines.append("This dashboard reads existing reports only.")
    lines.append("No orders are created.")
    lines.append("No Telegram messages are sent.")
    lines.append("")

    return "\n".join(lines)


def save_json(payload: Dict[str, Any], path: Path = OUTPUT_JSON_PATH) -> Path:
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def save_text(text: str, path: Path = OUTPUT_TXT_PATH) -> Path:
    path.parent.mkdir(exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def print_summary(payload: Dict[str, Any], json_path: Path, txt_path: Path) -> None:
    dashboard = as_dict(payload.get("dashboard"))

    print("QUICK SAFE DASHBOARD")
    print("====================")
    print("Mode: analytical only")
    print("Safe to continue:", payload.get("safe_to_continue"))
    print("JSON output:", json_path)
    print("TXT output:", txt_path)
    print()

    print("ONE SCREEN STATUS")
    print("=================")
    print("Pipeline:", dashboard.get("pipeline_status"), "| safe:", dashboard.get("safe_pipeline"))
    print("Safety gate:", dashboard.get("safety_gate_status"), "| ok:", dashboard.get("safety_gate_ok"))
    print("Risk filter buckets:", dashboard.get("risk_filter_buckets"))
    print(
        "Scenario matrix:",
        "count=",
        dashboard.get("scenario_matrix_count"),
        "failed=",
        dashboard.get("scenario_matrix_failed"),
        "unsafe_runtime=",
        dashboard.get("scenario_matrix_unsafe_runtime"),
    )
    print(
        "Telegram:",
        "enabled=",
        dashboard.get("telegram_send_enabled"),
        "manual_confirm=",
        dashboard.get("telegram_manual_confirm"),
        "sent=",
        dashboard.get("telegram_message_sent"),
        "api_used=",
        dashboard.get("telegram_api_used"),
    )
    print(
        "Blocked/watchlist:",
        "blocked=",
        dashboard.get("blocked_risk_count"),
        "watchlist=",
        dashboard.get("watchlist_count"),
    )

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
    print("[OK] This dashboard did not create orders.")
    print("[OK] This dashboard did not start trading bot.")
    print("[OK] This dashboard did not call Binance private API.")
    print("[OK] This dashboard did not send Telegram messages.")
    print("[OK] This dashboard only reads existing JSON reports.")


def main() -> None:
    payload = build_payload()
    json_path = save_json(payload)
    txt_path = save_text(build_text_report(payload))
    print_summary(payload, json_path, txt_path)


if __name__ == "__main__":
    main()
