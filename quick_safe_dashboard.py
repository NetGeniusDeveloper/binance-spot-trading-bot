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


def first_existing(item: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    for key in keys:
        value = item.get(key)
        if value not in (None, "", [], {}):
            return value
    return default


def format_pair(item: Dict[str, Any]) -> str:
    return str(
        first_existing(
            item,
            ["pair", "symbol", "ticker", "asset"],
            "UNKNOWN",
        )
    )


def short_risk_flags(item: Dict[str, Any], limit: int = 4) -> List[str]:
    flags = as_list(item.get("risk_flags"))

    if not flags:
        flags = as_list(item.get("message_flags"))

    result = [str(flag) for flag in flags if str(flag).strip()]

    return result[:limit]


def extract_top_blocked_items(blocked_risk: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
    items = []

    for raw_item in as_list(blocked_risk.get("blocked_items")):
        item = as_dict(raw_item)
        if not item:
            continue

        items.append(
            {
                "pair": format_pair(item),
                "risk_level": item.get("risk_level"),
                "final_score": item.get("final_score"),
                "market_score": item.get("market_score"),
                "telegram_score": item.get("telegram_score"),
                "unlock_score_gap": item.get("unlock_score_gap"),
                "risk_flags": short_risk_flags(item),
                "recommended_next_step": item.get("recommended_next_step"),
                "manager_note": item.get("manager_note"),
            }
        )

    def sort_key(item: Dict[str, Any]) -> float:
        gap = item.get("unlock_score_gap")
        try:
            return float(gap)
        except Exception:
            return 999999.0

    return sorted(items, key=sort_key)[:limit]


def extract_watchlist_preview(watchlist: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
    items = []

    for raw_item in as_list(watchlist.get("watchlist_items")):
        item = as_dict(raw_item)
        if not item:
            continue

        items.append(
            {
                "pair": format_pair(item),
                "watch_status": item.get("watch_status"),
                "decision": item.get("decision"),
                "risk_level": item.get("risk_level"),
                "final_score": item.get("final_score"),
                "risk_flags": short_risk_flags(item),
                "recommended_next_step": item.get("recommended_next_step"),
            }
        )

    return items[:limit]


def extract_closest_to_unlock(risk_filter: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
    items = []

    for raw_item in as_list(risk_filter.get("closest_to_unlock")):
        item = as_dict(raw_item)
        if not item:
            continue

        gap = as_dict(item.get("gap"))

        final_score_gap = first_existing(
            item,
            ["final_score_gap", "unlock_score_gap"],
            gap.get("final_score_gap"),
        )
        market_score_gap = first_existing(
            item,
            ["market_score_gap"],
            gap.get("market_score_gap"),
        )
        telegram_score_gap = first_existing(
            item,
            ["telegram_score_gap"],
            gap.get("telegram_score_gap"),
        )

        items.append(
            {
                "pair": format_pair(item),
                "bucket": first_existing(item, ["bucket", "backtest_bucket"]),
                "final_score_gap": final_score_gap,
                "market_score_gap": market_score_gap,
                "telegram_score_gap": telegram_score_gap,
                "risk_flags": short_risk_flags(item),
                "risk_level": item.get("risk_level"),
                "recommended_next_step": item.get("recommended_next_step"),
            }
        )

    def sort_key(item: Dict[str, Any]) -> float:
        gap = item.get("final_score_gap")
        try:
            return float(gap)
        except Exception:
            return 999999.0

    return sorted(items, key=sort_key)[:limit]


def build_manual_checklist(
    pipeline: Dict[str, Any],
    safety_gate: Dict[str, Any],
    risk_filter: Dict[str, Any],
    blocked_risk: Dict[str, Any],
    telegram: Dict[str, Any],
) -> List[str]:
    checklist: List[str] = []

    total_decisions = risk_filter.get("total_decisions") or 0
    blocked_count = blocked_risk.get("blocked_count") or 0

    try:
        total_decisions = int(total_decisions)
    except Exception:
        total_decisions = 0

    try:
        blocked_count = int(blocked_count)
    except Exception:
        blocked_count = 0

    if total_decisions <= 0:
        checklist.append("Новых аналитических решений нет: проверьте свежесть источников и повторите safe runner позже.")
    else:
        checklist.append("Проверить каждую пару из blocked/watchlist вручную перед любыми действиями.")

    if blocked_count > 0:
        checklist.append("Не использовать заблокированные пары для входа; сначала должны исчезнуть risk flags.")
        checklist.append("Проверить market confirmation, ретест и Telegram/social confirmation.")

    if safety_gate.get("review_required") is True:
        checklist.append("Safety gate требует ручного просмотра отчётов перед дальнейшими действиями.")

    if telegram.get("telegram_send_enabled") is not True:
        checklist.append("Telegram-отправка выключена: это безопасно, уведомления не отправлялись.")

    if telegram.get("telegram_manual_confirm") is not True:
        checklist.append("Ручное подтверждение Telegram выключено: автоматической отправки нет.")

    if pipeline.get("safe_pipeline") is True:
        checklist.append("Safe pipeline зелёный: можно продолжать только аналитический разбор, не торговлю.")

    return checklist


def build_decision_cockpit(
    pipeline: Dict[str, Any],
    safety_gate: Dict[str, Any],
    risk_filter: Dict[str, Any],
    scenario_matrix: Dict[str, Any],
    blocked_risk: Dict[str, Any],
    watchlist: Dict[str, Any],
    telegram: Dict[str, Any],
) -> Dict[str, Any]:
    total_decisions = risk_filter.get("total_decisions") or 0
    blocked_count = blocked_risk.get("blocked_count") or 0
    watchlist_count = watchlist.get("watchlist_count") or 0

    try:
        total_decisions = int(total_decisions)
    except Exception:
        total_decisions = 0

    try:
        blocked_count = int(blocked_count)
    except Exception:
        blocked_count = 0

    try:
        watchlist_count = int(watchlist_count)
    except Exception:
        watchlist_count = 0

    telegram_sent = telegram.get("telegram_message_sent") is True
    telegram_api_used = telegram.get("telegram_api_used") is True

    action_allowed = False

    if pipeline.get("safe_pipeline") is not True:
        state = "pipeline_not_safe"
        summary = "Конвейер не в безопасном состоянии. Ничего не делать, кроме диагностики."
    elif safety_gate.get("safety_gate_ok") is not True:
        state = "safety_gate_blocked"
        summary = "Safety gate не разрешает продолжение. Нужна диагностика."
    elif scenario_matrix.get("failed_count") not in (0, None):
        state = "scenario_matrix_failed"
        summary = "Synthetic scenario matrix содержит ошибки. Нельзя доверять фильтру до исправления."
    elif telegram_sent or telegram_api_used:
        state = "telegram_activity_detected"
        summary = "Обнаружена Telegram-активность. Нужно проверить, была ли она ожидаемой."
    elif total_decisions <= 0:
        state = "no_decisions"
        summary = "Новых аналитических решений нет. Можно только повторить сбор данных позже."
    elif blocked_count == total_decisions:
        state = "all_decisions_blocked"
        summary = "Все текущие решения заблокированы риск-фильтром. Вход запрещён."
    else:
        state = "manual_review_required"
        summary = "Есть решения для ручного просмотра, но автоматическая торговля всё равно запрещена."

    why_blocked = []

    risk_flags = as_dict(blocked_risk.get("summary_by_risk_flag"))
    if risk_flags:
        why_blocked.append(f"Активные risk flags: {risk_flags}")

    missing = as_dict(risk_filter.get("summary_by_missing_confirmation"))
    if missing:
        why_blocked.append(f"Не хватает подтверждений: {missing}")

    if blocked_count > 0:
        why_blocked.append(f"Заблокировано риск-фильтром: {blocked_count}")

    if watchlist_count > 0:
        why_blocked.append(f"В watchlist только для наблюдения: {watchlist_count}")

    if telegram.get("telegram_send_enabled") is not True:
        why_blocked.append("Telegram send выключен.")

    if telegram.get("telegram_manual_confirm") is not True:
        why_blocked.append("Telegram manual confirm выключен.")

    return {
        "state": state,
        "summary": summary,
        "action_allowed": action_allowed,
        "allowed_action": "manual_review_only",
        "forbidden_action": "no_orders_no_live_trading_no_auto_telegram",
        "total_decisions": total_decisions,
        "blocked_count": blocked_count,
        "watchlist_count": watchlist_count,
        "why_blocked": why_blocked,
        "closest_to_unlock": extract_closest_to_unlock(risk_filter),
        "top_blocked_items": extract_top_blocked_items(blocked_risk),
        "watchlist_preview": extract_watchlist_preview(watchlist),
        "manual_checklist": build_manual_checklist(
            pipeline=pipeline,
            safety_gate=safety_gate,
            risk_filter=risk_filter,
            blocked_risk=blocked_risk,
            telegram=telegram,
        ),
    }


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

    decision_cockpit = build_decision_cockpit(
        pipeline=pipeline,
        safety_gate=safety_gate,
        risk_filter=risk_filter,
        scenario_matrix=scenario_matrix,
        blocked_risk=blocked_risk,
        watchlist=watchlist,
        telegram=telegram,
    )

    dashboard["decision_cockpit"] = decision_cockpit

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

    cockpit = as_dict(dashboard.get("decision_cockpit"))

    lines.append("DECISION COCKPIT")
    lines.append("================")
    lines.append(f"State: {cockpit.get('state')}")
    lines.append(f"Summary: {cockpit.get('summary')}")
    lines.append(f"Action allowed: {format_bool(cockpit.get('action_allowed'))}")
    lines.append(f"Allowed action: {cockpit.get('allowed_action')}")
    lines.append(f"Forbidden action: {cockpit.get('forbidden_action')}")
    lines.append("")

    lines.append("WHY BLOCKED / LIMITED")
    lines.append("=====================")
    for reason in as_list(cockpit.get("why_blocked")):
        lines.append(f"- {reason}")
    if not as_list(cockpit.get("why_blocked")):
        lines.append("none")
    lines.append("")

    lines.append("CLOSEST TO UNLOCK")
    lines.append("=================")
    closest_items = as_list(cockpit.get("closest_to_unlock"))
    if closest_items:
        for item in closest_items:
            item = as_dict(item)
            lines.append(
                "- {pair}: bucket={bucket}, final_gap={final_gap}, market_gap={market_gap}, "
                "telegram_gap={telegram_gap}, risks={risks}".format(
                    pair=item.get("pair"),
                    bucket=item.get("bucket"),
                    final_gap=item.get("final_score_gap"),
                    market_gap=item.get("market_score_gap"),
                    telegram_gap=item.get("telegram_score_gap"),
                    risks=format_list(item.get("risk_flags")),
                )
            )
    else:
        lines.append("none")
    lines.append("")

    lines.append("HUMAN CHECKLIST")
    lines.append("===============")
    for item in as_list(cockpit.get("manual_checklist")):
        lines.append(f"- {item}")
    if not as_list(cockpit.get("manual_checklist")):
        lines.append("none")
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

    cockpit = as_dict(dashboard.get("decision_cockpit"))

    print("ONE SCREEN STATUS")
    print("=================")
    print("Cockpit:", cockpit.get("state"), "|", cockpit.get("summary"))
    print("Action allowed:", cockpit.get("action_allowed"), "|", cockpit.get("allowed_action"))
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

    closest_items = as_list(cockpit.get("closest_to_unlock"))
    if closest_items:
        print("Closest to unlock:")
        for item in closest_items[:3]:
            item = as_dict(item)
            print(
                "- {pair}: final_gap={final_gap}, market_gap={market_gap}, telegram_gap={telegram_gap}".format(
                    pair=item.get("pair"),
                    final_gap=item.get("final_score_gap"),
                    market_gap=item.get("market_score_gap"),
                    telegram_gap=item.get("telegram_score_gap"),
                )
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
