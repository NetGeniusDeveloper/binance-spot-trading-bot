import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


REPORTS_DIR = Path("reports")

INPUT_PATH = REPORTS_DIR / "scanner_agent_decision.json"
OUTPUT_JSON_PATH = REPORTS_DIR / "scanner_agent_risk_filter_backtest.json"
OUTPUT_TXT_PATH = REPORTS_DIR / "scanner_agent_risk_filter_backtest.txt"

ENTRY_FINAL_SCORE_TARGET = 60.0
ENTRY_MARKET_SCORE_TARGET = 60.0
ENTRY_TELEGRAM_SCORE_TARGET = 30.0

BLOCKED_DECISIONS = {
    "blocked_risk",
    "ignore",
}

WATCH_DECISIONS = {
    "wait_confirmation",
    "wait_retest",
    "observe",
}

ENTRY_ALLOWED_DECISIONS = {
    "candidate",
}


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {
            "ok": False,
            "error": f"File not found: {path}",
            "data": {},
        }

    try:
        return {
            "ok": True,
            "error": None,
            "data": json.loads(path.read_text(encoding="utf-8")),
        }
    except json.JSONDecodeError as ex:
        return {
            "ok": False,
            "error": f"Invalid JSON: {ex}",
            "data": {},
        }
    except OSError as ex:
        return {
            "ok": False,
            "error": f"Cannot read file: {ex}",
            "data": {},
        }


def as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value

    return []


def normalize_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]

    if isinstance(value, str) and value.strip():
        return [
            item.strip()
            for item in value.split(",")
            if item.strip()
        ]

    return []


def format_list(value: Any) -> str:
    items = normalize_list(value)
    return ", ".join(items) if items else "none"


def format_score(value: Any) -> str:
    try:
        return str(round(float(value), 2))
    except Exception:
        return "n/a"


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def bool_value(value: Any) -> bool:
    return value is True or str(value).strip().lower() in {"true", "1", "yes"}


def score_gap(value: Any, target: float) -> float:
    return round(max(target - safe_float(value), 0.0), 2)


def count_by_field(items: List[Dict[str, Any]], field_name: str) -> Dict[str, int]:
    result: Dict[str, int] = {}

    for item in items:
        key = str(item.get(field_name) or "unknown")
        result[key] = result.get(key, 0) + 1

    return dict(sorted(result.items()))


def count_risk_flags(items: List[Dict[str, Any]]) -> Dict[str, int]:
    result: Dict[str, int] = {}

    for item in items:
        for flag in normalize_list(item.get("risk_flags")):
            result[flag] = result.get(flag, 0) + 1

    return dict(sorted(result.items()))


def classify_backtest_bucket(item: Dict[str, Any]) -> str:
    decision = str(item.get("decision") or "").strip()
    action_hint = str(item.get("action_hint") or "").strip()
    order_execution_allowed = item.get("order_execution_allowed") is True

    if decision in BLOCKED_DECISIONS:
        return "BLOCKED"

    if action_hint == "entry_forbidden":
        return "BLOCKED"

    if order_execution_allowed:
        return "BLOCKED"

    if decision in ENTRY_ALLOWED_DECISIONS:
        return "ENTRY_ALLOWED_ANALYTICAL_ONLY"

    if decision in WATCH_DECISIONS:
        return "WATCH"

    return "WATCH"


def build_gap(item: Dict[str, Any]) -> Dict[str, Any]:
    risk_flags = normalize_list(item.get("risk_flags"))
    missing: List[str] = []

    if not bool_value(item.get("market_confirmation")):
        missing.append("market_confirmation")

    if not bool_value(item.get("has_retest")):
        missing.append("retest")

    if score_gap(item.get("telegram_score"), ENTRY_TELEGRAM_SCORE_TARGET) > 0:
        missing.append("telegram_social_confirmation")

    for flag in risk_flags:
        missing.append(f"risk_flag:{flag}")

    if str(item.get("action_hint") or "") == "entry_forbidden":
        missing.append("action_hint:entry_forbidden")

    return {
        "final_score_gap": score_gap(item.get("final_score"), ENTRY_FINAL_SCORE_TARGET),
        "market_score_gap": score_gap(item.get("market_score"), ENTRY_MARKET_SCORE_TARGET),
        "telegram_score_gap": score_gap(item.get("telegram_score"), ENTRY_TELEGRAM_SCORE_TARGET),
        "missing_confirmations": missing,
    }


def simulate_decision(item: Dict[str, Any]) -> Dict[str, Any]:
    bucket = classify_backtest_bucket(item)
    gap = build_gap(item)

    return {
        "pair": item.get("pair"),
        "ticker": item.get("ticker"),
        "source_group": item.get("source_group"),
        "decision": item.get("decision"),
        "backtest_bucket": bucket,
        "priority": item.get("priority"),
        "risk_level": item.get("risk_level"),
        "action_hint": item.get("action_hint"),
        "final_score": safe_float(item.get("final_score")),
        "market_score": safe_float(item.get("market_score")),
        "telegram_score": safe_float(item.get("telegram_score")),
        "risk_adjustment": safe_float(item.get("risk_adjustment")),
        "risk_flags": normalize_list(item.get("risk_flags")),
        "market_confirmation": bool_value(item.get("market_confirmation")),
        "has_retest": bool_value(item.get("has_retest")),
        "recommended_next_step": item.get("recommended_next_step"),
        "gap": gap,
        "analytical_only": True,
        "orders_enabled": False,
        "order_execution_allowed": False,
        "trading_enabled": False,
    }


def average(values: List[float]) -> float:
    if not values:
        return 0.0

    return round(sum(values) / len(values), 2)


def summarize_gaps(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    gaps = [item.get("gap", {}) for item in items]

    return {
        "average_final_score_gap": average([
            safe_float(gap.get("final_score_gap"))
            for gap in gaps
        ]),
        "average_market_score_gap": average([
            safe_float(gap.get("market_score_gap"))
            for gap in gaps
        ]),
        "average_telegram_score_gap": average([
            safe_float(gap.get("telegram_score_gap"))
            for gap in gaps
        ]),
    }


def count_missing_confirmations(items: List[Dict[str, Any]]) -> Dict[str, int]:
    result: Dict[str, int] = {}

    for item in items:
        gap = item.get("gap", {})
        missing = normalize_list(gap.get("missing_confirmations"))

        for value in missing:
            result[value] = result.get(value, 0) + 1

    return dict(sorted(result.items()))


def closest_to_unlock(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    selected = sorted(
        items,
        key=lambda item: (
            safe_float(item.get("gap", {}).get("final_score_gap")),
            safe_float(item.get("gap", {}).get("market_score_gap")),
            safe_float(item.get("gap", {}).get("telegram_score_gap")),
        ),
    )

    return selected[:10]


def build_synthetic_scenario_items() -> List[Dict[str, Any]]:
    return [
        {
            "scenario_name": "pump_fomo_should_block",
            "expected_buckets": ["BLOCKED"],
            "decision": "blocked_risk",
            "pair": "PUMPUSDT",
            "ticker": "PUMP",
            "source_group": "synthetic",
            "priority": 99,
            "risk_level": "high",
            "action_hint": "entry_forbidden",
            "final_score": 72.0,
            "market_score": 82.0,
            "telegram_score": 70.0,
            "risk_adjustment": 5.0,
            "risk_flags": ["pump_risk", "dangerous_fomo"],
            "market_confirmation": True,
            "has_retest": False,
            "recommended_next_step": "Synthetic check: pump/FOMO must stay blocked.",
        },
        {
            "scenario_name": "negative_news_should_block",
            "expected_buckets": ["BLOCKED"],
            "decision": "blocked_risk",
            "pair": "NEWSUSDT",
            "ticker": "NEWS",
            "source_group": "synthetic",
            "priority": 95,
            "risk_level": "high",
            "action_hint": "entry_forbidden",
            "final_score": 68.0,
            "market_score": 70.0,
            "telegram_score": 45.0,
            "risk_adjustment": 20.0,
            "risk_flags": ["negative_news_risk", "message_possible_news"],
            "market_confirmation": True,
            "has_retest": True,
            "recommended_next_step": "Synthetic check: negative news must stay blocked.",
        },
        {
            "scenario_name": "no_market_confirmation_should_block",
            "expected_buckets": ["BLOCKED"],
            "decision": "blocked_risk",
            "pair": "NOMKTUSDT",
            "ticker": "NOMKT",
            "source_group": "synthetic",
            "priority": 85,
            "risk_level": "medium",
            "action_hint": "entry_forbidden",
            "final_score": 57.0,
            "market_score": 42.0,
            "telegram_score": 62.0,
            "risk_adjustment": 55.0,
            "risk_flags": ["no_market_confirmation"],
            "market_confirmation": False,
            "has_retest": True,
            "recommended_next_step": "Synthetic check: no market confirmation must stay blocked.",
        },
        {
            "scenario_name": "weak_social_should_block_or_watch",
            "expected_buckets": ["BLOCKED", "WATCH"],
            "decision": "wait_confirmation",
            "pair": "WEAKSOCUSDT",
            "ticker": "WEAKSOC",
            "source_group": "synthetic",
            "priority": 60,
            "risk_level": "medium",
            "action_hint": "wait_retest_confirmation",
            "final_score": 58.0,
            "market_score": 66.0,
            "telegram_score": 18.0,
            "risk_adjustment": 50.0,
            "risk_flags": ["weak_social_confirmation"],
            "market_confirmation": True,
            "has_retest": False,
            "recommended_next_step": "Synthetic check: weak social signal must not become entry.",
        },
        {
            "scenario_name": "good_candidate_still_analytical_only",
            "expected_buckets": ["ENTRY_ALLOWED_ANALYTICAL_ONLY"],
            "decision": "candidate",
            "pair": "GOODUSDT",
            "ticker": "GOOD",
            "source_group": "synthetic",
            "priority": 80,
            "risk_level": "low",
            "action_hint": "manual_review_only",
            "final_score": 78.0,
            "market_score": 74.0,
            "telegram_score": 65.0,
            "risk_adjustment": 82.0,
            "risk_flags": [],
            "market_confirmation": True,
            "has_retest": True,
            "recommended_next_step": "Synthetic check: good candidate is analytical only, not an order.",
        },
    ]


def run_synthetic_scenarios() -> Dict[str, Any]:
    scenario_items = build_synthetic_scenario_items()
    results: List[Dict[str, Any]] = []

    for raw_item in scenario_items:
        expected_buckets = normalize_list(raw_item.get("expected_buckets"))
        simulated = simulate_decision(raw_item)
        bucket = str(simulated.get("backtest_bucket"))
        passed = bucket in expected_buckets

        dangerous_runtime_flags = {
            "orders_enabled": bool(simulated.get("orders_enabled")),
            "order_execution_allowed": bool(simulated.get("order_execution_allowed")),
            "trading_enabled": bool(simulated.get("trading_enabled")),
        }

        runtime_safe = not any(dangerous_runtime_flags.values())

        results.append(
            {
                "scenario_name": raw_item.get("scenario_name"),
                "expected_buckets": expected_buckets,
                "actual_bucket": bucket,
                "passed": passed and runtime_safe,
                "runtime_safe": runtime_safe,
                "dangerous_runtime_flags": dangerous_runtime_flags,
                "decision": simulated.get("decision"),
                "pair": simulated.get("pair"),
                "risk_level": simulated.get("risk_level"),
                "risk_flags": simulated.get("risk_flags"),
                "gap": simulated.get("gap"),
                "note": raw_item.get("recommended_next_step"),
            }
        )

    failed = [
        item
        for item in results
        if not item.get("passed")
    ]

    return {
        "synthetic_scenarios_ok": not failed,
        "synthetic_scenario_count": len(results),
        "synthetic_scenario_failed_count": len(failed),
        "synthetic_scenarios": results,
        "synthetic_scenario_failures": failed,
    }


def build_payload() -> Dict[str, Any]:
    loaded = load_json(INPUT_PATH)
    data = loaded.get("data", {})

    if not loaded.get("ok"):
        return {
            "source": "scanner_agent_risk_filter_backtest",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "input_file": str(INPUT_PATH),
            "output_json": str(OUTPUT_JSON_PATH),
            "output_txt": str(OUTPUT_TXT_PATH),
            "analytical_only": True,
            "orders_enabled": False,
            "trading_enabled": False,
            "safe_to_continue": False,
            "total_decisions": 0,
            "backtest_items": [],
            "summary_by_bucket": {},
            "summary_by_decision": {},
            "summary_by_risk_level": {},
            "summary_by_risk_flag": {},
            "summary_by_missing_confirmation": {},
            "gap_summary": {},
            "closest_to_unlock": [],
            **run_synthetic_scenarios(),
            "blockers": ["decision_file_not_ready"],
            "warnings": [],
            "error": loaded.get("error"),
        }

    decisions = [
        item
        for item in as_list(data.get("decisions"))
        if isinstance(item, dict)
    ]

    backtest_items = [simulate_decision(item) for item in decisions]

    backtest_items.sort(
        key=lambda item: (
            safe_float(item.get("priority")),
            safe_float(item.get("final_score")),
        ),
        reverse=True,
    )

    synthetic = run_synthetic_scenarios()
    synthetic_blockers = []
    if not synthetic.get("synthetic_scenarios_ok"):
        synthetic_blockers.append("synthetic_scenarios_failed")

    return {
        "source": "scanner_agent_risk_filter_backtest",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "input_file": str(INPUT_PATH),
        "output_json": str(OUTPUT_JSON_PATH),
        "output_txt": str(OUTPUT_TXT_PATH),
        "input_created_at": data.get("created_at"),
        "analytical_only": True,
        "orders_enabled": False,
        "order_execution_allowed": False,
        "trading_enabled": False,
        "telegram_sending": False,
        "safe_to_continue": True,
        "total_decisions": len(decisions),
        "backtest_items": backtest_items,
        "summary_by_bucket": count_by_field(backtest_items, "backtest_bucket"),
        "summary_by_decision": count_by_field(backtest_items, "decision"),
        "summary_by_risk_level": count_by_field(backtest_items, "risk_level"),
        "summary_by_risk_flag": count_risk_flags(backtest_items),
        "summary_by_missing_confirmation": count_missing_confirmations(backtest_items),
        "gap_summary": summarize_gaps(backtest_items),
        "closest_to_unlock": closest_to_unlock(backtest_items),
        **synthetic,
        "blockers": synthetic_blockers,
        "warnings": [],
        "disclaimer": (
            "This is a safe analytical risk-filter backtest over saved scanner decisions. "
            "It does not create orders, does not start trading, does not call Binance private API, "
            "and does not send Telegram messages."
        ),
    }


def build_text_report(payload: Dict[str, Any]) -> str:
    lines: List[str] = []

    lines.append("SCANNER AGENT RISK FILTER BACKTEST")
    lines.append("==================================")
    lines.append(f"Created at: {payload.get('created_at')}")
    lines.append(f"Input file: {payload.get('input_file')}")
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
    lines.append("SUMMARY")
    lines.append("=======")
    lines.append(f"Safe to continue: {payload.get('safe_to_continue')}")
    lines.append(f"Total decisions: {payload.get('total_decisions')}")
    lines.append(f"Summary by bucket: {payload.get('summary_by_bucket')}")
    lines.append(f"Summary by decision: {payload.get('summary_by_decision')}")
    lines.append(f"Summary by risk level: {payload.get('summary_by_risk_level')}")
    lines.append(f"Summary by risk flag: {payload.get('summary_by_risk_flag')}")
    lines.append(f"Summary by missing confirmation: {payload.get('summary_by_missing_confirmation')}")
    lines.append(f"Gap summary: {payload.get('gap_summary')}")
    lines.append(f"Synthetic scenarios OK: {payload.get('synthetic_scenarios_ok')}")
    lines.append(f"Synthetic scenario count: {payload.get('synthetic_scenario_count')}")
    lines.append(f"Synthetic scenario failed count: {payload.get('synthetic_scenario_failed_count')}")
    lines.append(f"Blockers: {format_list(payload.get('blockers'))}")
    lines.append(f"Warnings: {format_list(payload.get('warnings'))}")

    if payload.get("error"):
        lines.append(f"Error: {payload.get('error')}")

    lines.append("")
    lines.append("SYNTHETIC SCENARIOS")
    lines.append("===================")

    synthetic_scenarios = as_list(payload.get("synthetic_scenarios"))

    if not synthetic_scenarios:
        lines.append("No synthetic scenarios.")
    else:
        for scenario in synthetic_scenarios:
            status = "PASS" if scenario.get("passed") else "FAIL"
            lines.append(
                f"{scenario.get('scenario_name')} — {status} "
                f"(expected={format_list(scenario.get('expected_buckets'))}, "
                f"actual={scenario.get('actual_bucket')}, "
                f"runtime_safe={scenario.get('runtime_safe')})"
            )

    lines.append("")
    lines.append("BACKTEST ITEMS")
    lines.append("==============")

    items = as_list(payload.get("backtest_items"))

    if not items:
        lines.append("No backtest items.")
    else:
        for item in items:
            gap = item.get("gap", {})
            lines.append("")
            lines.append(f"{item.get('pair')} — {item.get('backtest_bucket')}")
            lines.append("-" * (len(str(item.get("pair"))) + len(str(item.get("backtest_bucket"))) + 3))
            lines.append(f"Decision: {item.get('decision')}")
            lines.append(f"Source group: {item.get('source_group')}")
            lines.append(f"Risk level: {item.get('risk_level')}")
            lines.append(f"Action hint: {item.get('action_hint')}")
            lines.append(
                "Scores: "
                f"final={format_score(item.get('final_score'))}, "
                f"market={format_score(item.get('market_score'))}, "
                f"telegram={format_score(item.get('telegram_score'))}, "
                f"risk_adjustment={format_score(item.get('risk_adjustment'))}"
            )
            lines.append(
                "Gaps: "
                f"final={format_score(gap.get('final_score_gap'))}, "
                f"market={format_score(gap.get('market_score_gap'))}, "
                f"telegram={format_score(gap.get('telegram_score_gap'))}"
            )
            lines.append(f"Market confirmation: {item.get('market_confirmation')}")
            lines.append(f"Retest confirmed: {item.get('has_retest')}")
            lines.append(f"Risk flags: {format_list(item.get('risk_flags'))}")
            lines.append(f"Missing confirmations: {format_list(gap.get('missing_confirmations'))}")
            lines.append(f"Recommended next step: {item.get('recommended_next_step')}")

    lines.append("")
    lines.append("CLOSEST TO UNLOCK")
    lines.append("=================")

    closest = as_list(payload.get("closest_to_unlock"))

    if not closest:
        lines.append("No items.")
    else:
        for item in closest:
            gap = item.get("gap", {})
            lines.append(
                f"- {item.get('pair')}: bucket={item.get('backtest_bucket')}, "
                f"final_gap={format_score(gap.get('final_score_gap'))}, "
                f"market_gap={format_score(gap.get('market_score_gap'))}, "
                f"telegram_gap={format_score(gap.get('telegram_score_gap'))}, "
                f"risks={format_list(item.get('risk_flags'))}"
            )

    lines.append("")
    lines.append("FINAL NOTE")
    lines.append("==========")
    lines.append("This backtest is analytical only.")
    lines.append("Blocked means: do not use this signal for entry.")
    lines.append("ENTRY_ALLOWED_ANALYTICAL_ONLY is still not permission to trade.")
    lines.append("No orders are created.")
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
    print("SCANNER AGENT RISK FILTER BACKTEST")
    print("==================================")
    print("Mode: analytical only")
    print("Orders enabled:", payload.get("orders_enabled"))
    print("Trading enabled:", payload.get("trading_enabled"))
    print("Telegram sending:", payload.get("telegram_sending"))
    print("Input file:", payload.get("input_file"))
    print("JSON output:", json_path)
    print("TXT output:", txt_path)
    print()

    print("SUMMARY")
    print("=======")
    print("Safe to continue:", payload.get("safe_to_continue"))
    print("Total decisions:", payload.get("total_decisions"))
    print("Summary by bucket:", payload.get("summary_by_bucket"))
    print("Summary by decision:", payload.get("summary_by_decision"))
    print("Summary by risk level:", payload.get("summary_by_risk_level"))
    print("Summary by risk flag:", payload.get("summary_by_risk_flag"))
    print("Summary by missing confirmation:", payload.get("summary_by_missing_confirmation"))
    print("Gap summary:", payload.get("gap_summary"))
    print("Synthetic scenarios OK:", payload.get("synthetic_scenarios_ok"))
    print("Synthetic scenario count:", payload.get("synthetic_scenario_count"))
    print("Synthetic scenario failed count:", payload.get("synthetic_scenario_failed_count"))

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
    print("[OK] This backtest did not create orders.")
    print("[OK] This backtest did not start trading bot.")
    print("[OK] This backtest did not call Binance private API.")
    print("[OK] This backtest did not send Telegram messages.")
    print("[OK] This backtest only reads scanner_agent_decision.json.")


def main() -> None:
    payload = build_payload()
    json_path = save_json(payload)
    txt_path = save_text(build_text_report(payload))
    print_summary(payload, json_path, txt_path)


if __name__ == "__main__":
    main()
