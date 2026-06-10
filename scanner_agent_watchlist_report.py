import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


REPORTS_DIR = Path("reports")

INPUT_PATH = REPORTS_DIR / "scanner_agent_decision.json"
OUTPUT_JSON_PATH = REPORTS_DIR / "scanner_agent_watchlist_report.json"
OUTPUT_TXT_PATH = REPORTS_DIR / "scanner_agent_watchlist_report.txt"

WATCHLIST_SOURCE_GROUPS = {
    "watchlist",
    "weak_watchlist",
}

WATCHLIST_DECISIONS = {
    "candidate",
    "wait_confirmation",
    "wait_retest",
    "observe",
    "blocked_risk",
}

ENTRY_FINAL_SCORE_TARGET = 60.0
ENTRY_MARKET_SCORE_TARGET = 60.0
ENTRY_TELEGRAM_SCORE_TARGET = 30.0


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


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def score_gap(value: Any, target: float) -> float:
    return round(max(target - safe_float(value), 0.0), 2)


def bool_value(value: Any) -> bool:
    return value is True or str(value).strip().lower() in {"true", "1", "yes"}


def build_scoring_gap(item: Dict[str, Any]) -> Dict[str, Any]:
    risk_flags = normalize_list(item.get("risk_flags"))
    missing_confirmations: List[str] = []

    if not bool_value(item.get("market_confirmation")):
        missing_confirmations.append("market_confirmation")

    if not bool_value(item.get("has_retest")):
        missing_confirmations.append("retest")

    if score_gap(item.get("telegram_score"), ENTRY_TELEGRAM_SCORE_TARGET) > 0:
        missing_confirmations.append("telegram_social_confirmation")

    if risk_flags:
        missing_confirmations.extend(f"risk_flag:{flag}" for flag in risk_flags)

    if str(item.get("action_hint") or "") == "entry_forbidden":
        missing_confirmations.append("action_hint:entry_forbidden")

    return {
        "entry_final_score_target": ENTRY_FINAL_SCORE_TARGET,
        "entry_market_score_target": ENTRY_MARKET_SCORE_TARGET,
        "entry_telegram_score_target": ENTRY_TELEGRAM_SCORE_TARGET,
        "final_score_gap": score_gap(item.get("final_score"), ENTRY_FINAL_SCORE_TARGET),
        "market_score_gap": score_gap(item.get("market_score"), ENTRY_MARKET_SCORE_TARGET),
        "telegram_score_gap": score_gap(item.get("telegram_score"), ENTRY_TELEGRAM_SCORE_TARGET),
        "missing_confirmations": missing_confirmations,
    }


def classify_watch_status(item: Dict[str, Any]) -> str:
    decision = str(item.get("decision") or "").strip()
    action_hint = str(item.get("action_hint") or "").strip()

    if decision == "candidate" and action_hint != "entry_forbidden":
        return "ENTRY_ALLOWED_ANALYTICAL_REVIEW"

    if decision == "blocked_risk" or action_hint == "entry_forbidden":
        return "BLOCKED_WATCH_ONLY"

    if decision in {"wait_confirmation", "wait_retest"}:
        return "WAIT"

    return "WATCH"


def is_watchlist_item(item: Dict[str, Any]) -> bool:
    source_group = str(item.get("source_group") or "").strip()
    decision = str(item.get("decision") or "").strip()

    if source_group in WATCHLIST_SOURCE_GROUPS:
        return True

    return decision in WATCHLIST_DECISIONS and source_group.endswith("watchlist")


def select_watchlist_items(decisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = []

    for item in decisions:
        if not isinstance(item, dict):
            continue

        if not is_watchlist_item(item):
            continue

        enriched = dict(item)
        enriched["watch_status"] = classify_watch_status(item)
        enriched["scoring_gap"] = build_scoring_gap(item)
        selected.append(enriched)

    selected.sort(
        key=lambda item: (
            safe_int(item.get("priority"), 0),
            safe_float(item.get("final_score"), 0.0),
        ),
        reverse=True,
    )

    return selected


def count_by_field(items: List[Dict[str, Any]], field_name: str) -> Dict[str, int]:
    result: Dict[str, int] = {}

    for item in items:
        key = str(item.get(field_name) or "unknown")
        result[key] = result.get(key, 0) + 1

    return dict(sorted(result.items()))


def build_report_payload() -> Dict[str, Any]:
    loaded = load_json(INPUT_PATH)
    data = loaded.get("data", {})

    if not loaded.get("ok"):
        return {
            "source": "scanner_agent_watchlist_report",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "input_file": str(INPUT_PATH),
            "output_json": str(OUTPUT_JSON_PATH),
            "output_txt": str(OUTPUT_TXT_PATH),
            "analytical_only": True,
            "orders_enabled": False,
            "trading_enabled": False,
            "safe_to_continue": False,
            "total_decisions": 0,
            "watchlist_count": 0,
            "watchlist_items": [],
            "summary_by_watch_status": {},
            "summary_by_decision": {},
            "summary_by_source_group": {},
            "summary_by_risk_level": {},
            "summary_by_risk_flag": {},
            "blockers": ["decision_file_not_ready"],
            "warnings": [],
            "error": loaded.get("error"),
            "disclaimer": (
                "This report is analytical only. It does not create orders, "
                "does not start trading, does not call Binance API, "
                "and does not send Telegram messages."
            ),
        }

    decisions = as_list(data.get("decisions"))
    watchlist_items = select_watchlist_items(decisions)

    return {
        "source": "scanner_agent_watchlist_report",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "input_file": str(INPUT_PATH),
        "output_json": str(OUTPUT_JSON_PATH),
        "output_txt": str(OUTPUT_TXT_PATH),
        "input_created_at": data.get("created_at"),
        "analytical_only": True,
        "orders_enabled": False,
        "trading_enabled": False,
        "safe_to_continue": True,
        "total_decisions": len(decisions),
        "watchlist_count": len(watchlist_items),
        "watchlist_items": watchlist_items,
        "summary_by_watch_status": count_by_field(watchlist_items, "watch_status"),
        "summary_by_decision": count_by_field(watchlist_items, "decision"),
        "summary_by_source_group": count_by_field(watchlist_items, "source_group"),
        "summary_by_risk_level": count_by_field(watchlist_items, "risk_level"),
        "summary_by_risk_flag": count_risk_flags(watchlist_items),
        "blockers": [],
        "warnings": [],
        "disclaimer": (
            "This report is analytical only. Watchlist signals are not trading entries. "
            "No orders are created."
        ),
    }


def count_risk_flags(items: List[Dict[str, Any]]) -> Dict[str, int]:
    result: Dict[str, int] = {}

    for item in items:
        for flag in normalize_list(item.get("risk_flags")):
            result[flag] = result.get(flag, 0) + 1

    return dict(sorted(result.items()))


def build_text_report(payload: Dict[str, Any]) -> str:
    lines: List[str] = []

    lines.append("SCANNER AGENT WATCHLIST REPORT")
    lines.append("==============================")
    lines.append(f"Created at: {payload.get('created_at')}")
    lines.append(f"Input file: {payload.get('input_file')}")
    lines.append("")
    lines.append("SAFETY")
    lines.append("======")
    lines.append("Analytical only: True")
    lines.append("Orders enabled: False")
    lines.append("Trading enabled: False")
    lines.append("Binance orders created: False")
    lines.append("Telegram sending: False")
    lines.append("")
    lines.append("SUMMARY")
    lines.append("=======")
    lines.append(f"Safe to continue: {payload.get('safe_to_continue')}")
    lines.append(f"Total decisions: {payload.get('total_decisions')}")
    lines.append(f"Watchlist items: {payload.get('watchlist_count')}")
    lines.append(f"Summary by watch status: {payload.get('summary_by_watch_status')}")
    lines.append(f"Summary by decision: {payload.get('summary_by_decision')}")
    lines.append(f"Summary by source group: {payload.get('summary_by_source_group')}")
    lines.append(f"Summary by risk level: {payload.get('summary_by_risk_level')}")
    lines.append(f"Summary by risk flag: {payload.get('summary_by_risk_flag')}")
    lines.append(f"Blockers: {format_list(payload.get('blockers'))}")
    lines.append(f"Warnings: {format_list(payload.get('warnings'))}")

    if payload.get("error"):
        lines.append(f"Error: {payload.get('error')}")

    lines.append("")
    lines.append("WATCHLIST ITEMS")
    lines.append("===============")

    watchlist_items = as_list(payload.get("watchlist_items"))

    if not watchlist_items:
        lines.append("No watchlist items.")
    else:
        for item in watchlist_items:
            pair = item.get("pair")
            status = item.get("watch_status")
            lines.append("")
            lines.append(f"{pair} — {status}")
            lines.append("-" * (len(str(pair)) + len(str(status)) + 3))
            lines.append(f"Ticker: {item.get('ticker')}")
            lines.append(f"Source group: {item.get('source_group')}")
            lines.append(f"Decision: {item.get('decision')}")
            lines.append(f"Risk level: {item.get('risk_level')}")
            lines.append(f"Action hint: {item.get('action_hint')}")
            lines.append(
                "Scores: "
                f"final={format_score(item.get('final_score'))}, "
                f"market={format_score(item.get('market_score'))}, "
                f"telegram={format_score(item.get('telegram_score'))}, "
                f"risk_adjustment={format_score(item.get('risk_adjustment'))}"
            )
            lines.append(f"Market confirmation: {item.get('market_confirmation')}")
            lines.append(f"Retest confirmed: {item.get('has_retest')}")
            lines.append(f"Risk flags: {format_list(item.get('risk_flags'))}")

            scoring_gap = item.get("scoring_gap") or {}
            lines.append("")
            lines.append("Scoring gap:")
            lines.append(f"- entry final target: {scoring_gap.get('entry_final_score_target')}")
            lines.append(f"- entry market target: {scoring_gap.get('entry_market_score_target')}")
            lines.append(f"- entry telegram target: {scoring_gap.get('entry_telegram_score_target')}")
            lines.append(f"- final score gap: {scoring_gap.get('final_score_gap')}")
            lines.append(f"- market score gap: {scoring_gap.get('market_score_gap')}")
            lines.append(f"- telegram score gap: {scoring_gap.get('telegram_score_gap')}")

            missing_confirmations = normalize_list(scoring_gap.get("missing_confirmations"))
            if missing_confirmations:
                lines.append("- missing confirmations:")
                for missing in missing_confirmations:
                    lines.append(f"  - {missing}")
            else:
                lines.append("- missing confirmations: none")

            lines.append(f"Message intent: {item.get('message_intent')}")
            lines.append(f"Message quality: {format_score(item.get('message_quality_score'))}")
            lines.append(f"Recommended next step: {item.get('recommended_next_step')}")

            block_reasons = normalize_list(item.get("block_reasons"))

            if block_reasons:
                lines.append("")
                lines.append("Watch reasons / blockers:")
                for reason in block_reasons:
                    lines.append(f"- {reason}")

    lines.append("")
    lines.append("FINAL NOTE")
    lines.append("==========")
    lines.append("Watchlist means: observe, wait for confirmation/retest, or keep blocked.")
    lines.append("This report is only for analytical review.")
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
    print("SCANNER AGENT WATCHLIST REPORT")
    print("==============================")
    print("Mode: analytical only")
    print("Orders enabled:", payload.get("orders_enabled"))
    print("Trading enabled:", payload.get("trading_enabled"))
    print("Input file:", payload.get("input_file"))
    print("JSON output:", json_path)
    print("TXT output:", txt_path)
    print()

    print("SUMMARY")
    print("=======")
    print("Safe to continue:", payload.get("safe_to_continue"))
    print("Total decisions:", payload.get("total_decisions"))
    print("Watchlist items:", payload.get("watchlist_count"))
    print("Summary by watch status:", payload.get("summary_by_watch_status"))
    print("Summary by decision:", payload.get("summary_by_decision"))
    print("Summary by source group:", payload.get("summary_by_source_group"))
    print("Summary by risk level:", payload.get("summary_by_risk_level"))
    print("Summary by risk flag:", payload.get("summary_by_risk_flag"))

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
    print("[OK] This report did not create orders.")
    print("[OK] This report did not start trading bot.")
    print("[OK] This report did not call Binance API.")
    print("[OK] This report did not send Telegram messages.")
    print("[OK] This report only reads scanner_agent_decision.json.")


def main() -> None:
    payload = build_report_payload()
    json_path = save_json(payload)
    txt_path = save_text(build_text_report(payload))
    print_summary(payload, json_path, txt_path)


if __name__ == "__main__":
    main()
