import json
from pathlib import Path
from typing import Any, Dict, List


INPUT_PATH = Path("reports") / "scanner_agent_decision.json"


DECISION_TITLES = {
    "candidate": "STRONG ANALYTICAL CANDIDATES",
    "wait_confirmation": "WAIT CONFIRMATION",
    "wait_retest": "WAIT RETEST",
    "observe": "OBSERVE ONLY",
    "blocked_risk": "BLOCKED BY RISK",
    "ignore": "IGNORED",
}


DECISION_ORDER = [
    "candidate",
    "wait_confirmation",
    "wait_retest",
    "observe",
    "blocked_risk",
    "ignore",
]


def load_decision_payload(path: Path = INPUT_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {
            "error": f"Decision file not found: {path}",
            "decisions": [],
            "blockers": ["decision_file_not_found"],
            "warnings": [],
            "safe_to_continue": False,
        }

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as ex:
        return {
            "error": f"Invalid decision JSON: {ex}",
            "decisions": [],
            "blockers": ["invalid_decision_json"],
            "warnings": [],
            "safe_to_continue": False,
        }


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


def group_decisions(decisions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}

    for item in decisions:
        decision = str(item.get("decision", "unknown"))
        grouped.setdefault(decision, []).append(item)

    for decision_items in grouped.values():
        decision_items.sort(
            key=lambda item: (
                int(item.get("priority", 0)),
                float(item.get("final_score") or 0.0),
            ),
            reverse=True,
        )

    return grouped


def print_decision_line(item: Dict[str, Any]) -> None:
    print(
        str(item.get("pair")).ljust(10),
        "priority=" + str(item.get("priority")),
        "status=" + str(item.get("suggested_status")),
        "final=" + str(item.get("final_score")),
        "market=" + str(item.get("market_score")),
        "telegram=" + str(item.get("telegram_score")),
        "retest=" + str(item.get("has_retest")),
        "risks=" + format_list(item.get("risk_flags")),
        "message=" + str(item.get("message_intent")),
    )


def print_reasons(item: Dict[str, Any]) -> None:
    reasons = item.get("reasons", [])

    if not reasons:
        print("  Reasons: none")
        return

    print("  Reasons:")

    for reason in reasons:
        print("   -", reason)


def print_message_details(item: Dict[str, Any]) -> None:
    print("  Message:")
    print("   - intent:", item.get("message_intent"))
    print("   - quality:", item.get("message_quality_score"))
    print("   - adjustment:", item.get("message_score_adjustment"))
    print("   - flags:", format_list(item.get("message_risk_flags")))

    message_reasons = item.get("message_reasons", [])

    if message_reasons:
        print("   - reasons:", ", ".join(str(reason) for reason in message_reasons))
    else:
        print("   - reasons: none")


def print_section(title: str, items: List[Dict[str, Any]]) -> None:
    print()
    print(title)
    print("=" * len(title))

    if not items:
        print("None")
        return

    for item in items:
        print_decision_line(item)
        print_message_details(item)
        print_reasons(item)
        print()


def print_payload_summary(payload: Dict[str, Any]) -> None:
    print("SCANNER AGENT DECISION REPORT")
    print("=============================")
    print("Mode: analytical only")
    print("Input file:", INPUT_PATH)
    print("Source:", payload.get("source"))
    print("Created at:", payload.get("created_at"))
    print("Safe to continue:", payload.get("safe_to_continue"))
    print("Order execution allowed:", payload.get("order_execution_allowed"))
    print("Trading enabled:", payload.get("trading_enabled"))
    print()

    if payload.get("error"):
        print("[FAIL]", payload.get("error"))

    print("SUMMARY")
    print("=======")
    print("Input candidates:", payload.get("total_input_candidates", 0))
    print("Input watchlist candidates:", payload.get("total_input_watchlist_candidates", 0))
    print("Total decisions:", payload.get("total_decisions", 0))
    print("Summary by decision:", payload.get("summary_by_decision", {}))

    if payload.get("blockers"):
        print("Blockers:", ", ".join(str(item) for item in payload["blockers"]))
    else:
        print("Blockers: none")

    if payload.get("warnings"):
        print("Warnings:", ", ".join(str(item) for item in payload["warnings"]))
    else:
        print("Warnings: none")


def print_safety_block() -> None:
    print()
    print("SAFETY")
    print("======")
    print("[OK] This report did not create orders.")
    print("[OK] This report did not start trading bot.")
    print("[OK] This report did not call Binance API.")
    print("[OK] This report did not read Telegram.")
    print("[OK] This report only reads scanner_agent_decision.json.")


def print_next_step(payload: Dict[str, Any]) -> None:
    print()
    print("NEXT STEP")
    print("=========")

    decisions = payload.get("decisions", [])

    if not decisions:
        print("No decisions found. Rerun ./run_telegram_real_market_scanner_safe.sh")
        return

    summary = payload.get("summary_by_decision", {})

    if summary.get("candidate"):
        print("There are strong analytical candidates, but orders are still disabled.")
        print("Next safe step: build a manual approval layer.")
        return

    if summary.get("wait_confirmation") or summary.get("wait_retest"):
        print("Signals require confirmation or retest.")
        print("Next safe step: build a notification/report layer, not order execution.")
        return

    print("All signals are observation-only or ignored.")
    print("Next safe step: continue collecting more public Telegram messages.")


def main() -> None:
    payload = load_decision_payload()
    decisions = payload.get("decisions", [])

    if not isinstance(decisions, list):
        decisions = []

    grouped = group_decisions(decisions)

    print_payload_summary(payload)

    for decision in DECISION_ORDER:
        title = DECISION_TITLES.get(decision, decision.upper())
        print_section(title, grouped.get(decision, []))

    unknown_decisions = sorted(
        decision
        for decision in grouped
        if decision not in DECISION_ORDER
    )

    for decision in unknown_decisions:
        print_section("UNKNOWN: " + decision, grouped.get(decision, []))

    print_safety_block()
    print_next_step(payload)


if __name__ == "__main__":
    main()
