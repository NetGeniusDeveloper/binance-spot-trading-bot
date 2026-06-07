import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


INPUT_PATH = Path("reports") / "scanner_agent_decision.json"
OUTPUT_PATH = Path("reports") / "scanner_agent_notification_report.txt"


DECISION_TITLES = {
    "candidate": "🔥 STRONG ANALYTICAL CANDIDATES",
    "wait_confirmation": "⏳ WAIT CONFIRMATION",
    "wait_retest": "🔁 WAIT RETEST",
    "observe": "👀 OBSERVE ONLY",
    "blocked_risk": "🚫 BLOCKED BY RISK",
    "ignore": "⚪ IGNORED",
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

    for items in grouped.values():
        items.sort(
            key=lambda item: (
                int(item.get("priority", 0)),
                float(item.get("final_score") or 0.0),
            ),
            reverse=True,
        )

    return grouped


def build_item_line(item: Dict[str, Any]) -> str:
    return (
        f"{item.get('pair')} | "
        f"decision={item.get('decision')} | "
        f"priority={item.get('priority')} | "
        f"status={item.get('suggested_status')} | "
        f"final={item.get('final_score')} | "
        f"market={item.get('market_score')} | "
        f"telegram={item.get('telegram_score')} | "
        f"retest={item.get('has_retest')} | "
        f"risks={format_list(item.get('risk_flags'))} | "
        f"message={item.get('message_intent')}"
    )


def build_item_details(item: Dict[str, Any]) -> List[str]:
    lines: List[str] = []

    lines.append(build_item_line(item))
    lines.append("")

    lines.append("Message:")
    lines.append(f"- intent: {item.get('message_intent')}")
    lines.append(f"- quality: {item.get('message_quality_score')}")
    lines.append(f"- adjustment: {item.get('message_score_adjustment')}")
    lines.append(f"- flags: {format_list(item.get('message_risk_flags'))}")

    message_reasons = normalize_list(item.get("message_reasons", []))
    lines.append(f"- reasons: {', '.join(message_reasons) if message_reasons else 'none'}")
    lines.append("")

    reasons = normalize_list(item.get("reasons", []))

    if reasons:
        lines.append("Reasons:")

        for reason in reasons:
            lines.append(f"- {reason}")
    else:
        lines.append("Reasons: none")

    lines.append("")

    return lines


def build_notification_text(payload: Dict[str, Any]) -> str:
    created_at = datetime.now().isoformat(timespec="seconds")
    decisions = payload.get("decisions", [])

    if not isinstance(decisions, list):
        decisions = []

    grouped = group_decisions(decisions)

    lines: List[str] = []

    lines.append("CRYPTO SCANNER AGENT NOTIFICATION REPORT")
    lines.append("========================================")
    lines.append(f"Created at: {created_at}")
    lines.append(f"Input file: {INPUT_PATH}")
    lines.append(f"Source: {payload.get('source')}")
    lines.append(f"Input created at: {payload.get('created_at')}")
    lines.append("")
    lines.append("SAFETY")
    lines.append("======")
    lines.append("Analytical only: True")
    lines.append("Order execution allowed: False")
    lines.append("Trading enabled: False")
    lines.append("Telegram send: disabled")
    lines.append("Binance API: disabled")
    lines.append("Orders: disabled")
    lines.append("")

    if payload.get("error"):
        lines.append("ERROR")
        lines.append("=====")
        lines.append(str(payload.get("error")))
        lines.append("")

    lines.append("SUMMARY")
    lines.append("=======")
    lines.append(f"Safe to continue: {payload.get('safe_to_continue')}")
    lines.append(f"Input candidates: {payload.get('total_input_candidates', 0)}")
    lines.append(f"Input watchlist candidates: {payload.get('total_input_watchlist_candidates', 0)}")
    lines.append(f"Total decisions: {payload.get('total_decisions', 0)}")
    lines.append(f"Summary by decision: {payload.get('summary_by_decision', {})}")
    lines.append(f"Blockers: {format_list(payload.get('blockers', []))}")
    lines.append(f"Warnings: {format_list(payload.get('warnings', []))}")
    lines.append("")

    for decision in DECISION_ORDER:
        title = DECISION_TITLES.get(decision, decision.upper())
        items = grouped.get(decision, [])

        lines.append(title)
        lines.append("=" * len(title))

        if not items:
            lines.append("None")
            lines.append("")
            continue

        for item in items:
            lines.extend(build_item_details(item))

    unknown_decisions = sorted(
        decision
        for decision in grouped
        if decision not in DECISION_ORDER
    )

    for decision in unknown_decisions:
        title = "UNKNOWN: " + decision
        lines.append(title)
        lines.append("=" * len(title))

        for item in grouped.get(decision, []):
            lines.extend(build_item_details(item))

    lines.append("NEXT STEP")
    lines.append("=========")

    summary = payload.get("summary_by_decision", {})

    if summary.get("candidate"):
        lines.append("There are strong analytical candidates, but orders are still disabled.")
        lines.append("Next safe step: manual approval layer.")
    elif summary.get("wait_confirmation") or summary.get("wait_retest"):
        lines.append("Signals require confirmation or retest.")
        lines.append("Next safe step: notification delivery preview, not order execution.")
    elif decisions:
        lines.append("All signals are observation-only, blocked, or ignored.")
        lines.append("Next safe step: continue collecting more public Telegram messages.")
    else:
        lines.append("No decisions found.")
        lines.append("Run ./run_telegram_real_market_scanner_safe.sh first.")

    lines.append("")
    lines.append("DISCLAIMER")
    lines.append("==========")
    lines.append("Telegram/social signal is not a trading entry.")
    lines.append("This notification report is analytical only.")
    lines.append("No orders are created.")
    lines.append("No Telegram messages are sent.")
    lines.append("No Binance API calls are made.")
    lines.append("Crypto assets are high-risk. Final decision is always user's responsibility.")
    lines.append("")

    return "\n".join(lines)


def save_notification_text(text: str, path: Path = OUTPUT_PATH) -> Path:
    path.parent.mkdir(exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def print_notification_summary(payload: Dict[str, Any], output_path: Path) -> None:
    print("SCANNER AGENT NOTIFICATION REPORT")
    print("=================================")
    print("Mode: analytical only")
    print("Telegram send enabled:", False)
    print("Orders enabled:", False)
    print("Trading enabled:", False)
    print("Binance API used:", False)
    print("Input file:", INPUT_PATH)
    print("Output file:", output_path)
    print()

    print("SUMMARY")
    print("=======")
    print("Safe to continue:", payload.get("safe_to_continue"))
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

    if payload.get("error"):
        print("Error:", payload.get("error"))

    print()
    print("SAFETY")
    print("======")
    print("[OK] This script did not create orders.")
    print("[OK] This script did not start trading bot.")
    print("[OK] This script did not call Binance API.")
    print("[OK] This script did not read Telegram.")
    print("[OK] This script did not send Telegram messages.")
    print("[OK] This script only reads scanner_agent_decision.json.")

    print()
    print("NEXT STEP")
    print("=========")
    print("Review the generated text report before building any notification sender.")


def main() -> None:
    payload = load_decision_payload()
    text = build_notification_text(payload)
    output_path = save_notification_text(text)
    print_notification_summary(payload, output_path)


if __name__ == "__main__":
    main()
