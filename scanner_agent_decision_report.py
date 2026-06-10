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


SOURCE_GROUP_TITLES = {
    "candidate": "SOURCE GROUP: CANDIDATE",
    "watchlist": "SOURCE GROUP: WATCHLIST",
    "weak_watchlist": "SOURCE GROUP: WEAK WATCHLIST",
    "unknown": "SOURCE GROUP: UNKNOWN",
}


DECISION_ORDER = [
    "candidate",
    "wait_confirmation",
    "wait_retest",
    "observe",
    "blocked_risk",
    "ignore",
]


SOURCE_GROUP_ORDER = [
    "candidate",
    "watchlist",
    "weak_watchlist",
    "unknown",
]

ENTRY_FINAL_SCORE_TARGET = 60.0
ENTRY_MARKET_SCORE_TARGET = 60.0
ENTRY_TELEGRAM_SCORE_TARGET = 30.0


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


def format_scoring_gap_short(item: Dict[str, Any]) -> str:
    gap = build_scoring_gap(item)
    missing = gap.get("missing_confirmations") or []

    return (
        f"final_gap={gap['final_score_gap']} "
        f"market_gap={gap['market_score_gap']} "
        f"telegram_gap={gap['telegram_score_gap']} "
        f"missing={','.join(str(item) for item in missing) if missing else 'none'}"
    )


def print_scoring_gap(item: Dict[str, Any]) -> None:
    gap = build_scoring_gap(item)

    print("  Scoring gap:")
    print("   - entry final target:", gap["entry_final_score_target"])
    print("   - entry market target:", gap["entry_market_score_target"])
    print("   - entry telegram target:", gap["entry_telegram_score_target"])
    print("   - final score gap:", gap["final_score_gap"])
    print("   - market score gap:", gap["market_score_gap"])
    print("   - telegram score gap:", gap["telegram_score_gap"])

    missing = gap.get("missing_confirmations") or []

    if missing:
        print("   - missing confirmations:")
        for item in missing:
            print("     -", item)
    else:
        print("   - missing confirmations: none")


def normalize_source_group(value: Any) -> str:
    source_group = str(value or "").strip()

    if source_group in SOURCE_GROUP_TITLES:
        return source_group

    return "unknown"


def group_decisions(decisions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}

    for item in decisions:
        decision = str(item.get("decision", "unknown"))
        grouped.setdefault(decision, []).append(item)

    for decision_items in grouped.values():
        sort_decision_items(decision_items)

    return grouped


def group_by_source_group(decisions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}

    for item in decisions:
        source_group = normalize_source_group(item.get("source_group"))
        grouped.setdefault(source_group, []).append(item)

    for source_items in grouped.values():
        sort_decision_items(source_items)

    return grouped


def group_by_decision_inside_source(
    decisions: List[Dict[str, Any]],
) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    grouped: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

    for item in decisions:
        source_group = normalize_source_group(item.get("source_group"))
        decision = str(item.get("decision", "unknown"))

        grouped.setdefault(source_group, {})
        grouped[source_group].setdefault(decision, [])
        grouped[source_group][decision].append(item)

    for source_group in grouped:
        for decision in grouped[source_group]:
            sort_decision_items(grouped[source_group][decision])

    return grouped


def sort_decision_items(items: List[Dict[str, Any]]) -> None:
    items.sort(
        key=lambda item: (
            safe_int(item.get("priority"), 0),
            safe_float(item.get("final_score"), 0.0),
        ),
        reverse=True,
    )


def count_by_field(items: List[Dict[str, Any]], field_name: str) -> Dict[str, int]:
    summary: Dict[str, int] = {}

    for item in items:
        key = str(item.get(field_name) or "unknown")
        summary[key] = summary.get(key, 0) + 1

    return dict(sorted(summary.items()))


def classify_decision_bucket(item: Dict[str, Any]) -> str:
    decision = str(item.get("decision") or "").strip()
    action_hint = str(item.get("action_hint") or "").strip()
    order_execution_allowed = item.get("order_execution_allowed") is True

    if order_execution_allowed and decision == "candidate":
        return "ENTRY_ALLOWED"

    if decision in {"blocked_risk", "ignore"}:
        return "BLOCKED"

    if action_hint == "entry_forbidden":
        return "BLOCKED"

    return "WATCH"


def build_decision_table_rows(decisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for item in decisions:
        bucket = classify_decision_bucket(item)
        rows.append(
            {
                "bucket": bucket,
                "pair": str(item.get("pair") or "unknown"),
                "decision": str(item.get("decision") or "unknown"),
                "group": normalize_source_group(item.get("source_group")),
                "priority": safe_int(item.get("priority"), 0),
                "final_score": safe_float(item.get("final_score"), 0.0),
                "market_score": safe_float(item.get("market_score"), 0.0),
                "telegram_score": safe_float(item.get("telegram_score"), 0.0),
                "risk_level": str(item.get("risk_level") or "unknown"),
                "risk_flags": format_list(item.get("risk_flags")),
                "scoring_gap": format_scoring_gap_short(item),
                "action_hint": str(item.get("action_hint") or "unknown"),
                "next_step": str(item.get("recommended_next_step") or "manual review"),
            }
        )

    rows.sort(
        key=lambda row: (
            {"ENTRY_ALLOWED": 3, "WATCH": 2, "BLOCKED": 1}.get(row["bucket"], 0),
            row["priority"],
            row["final_score"],
        ),
        reverse=True,
    )

    return rows


def count_by_bucket(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    result = {
        "ENTRY_ALLOWED": 0,
        "WATCH": 0,
        "BLOCKED": 0,
    }

    for row in rows:
        bucket = str(row.get("bucket") or "WATCH")
        result[bucket] = result.get(bucket, 0) + 1

    return result


def format_table_cell(value: Any, width: int) -> str:
    text = str(value)

    if len(text) > width:
        return text[: max(width - 1, 0)] + "…"

    return text.ljust(width)


def print_decision_status_table(decisions: List[Dict[str, Any]]) -> None:
    rows = build_decision_table_rows(decisions)

    print()
    print("DECISION STATUS TABLE")
    print("=====================")
    print("Buckets: ENTRY_ALLOWED = analytical candidate only; WATCH = observe/retest/confirm; BLOCKED = do not enter.")

    if not rows:
        print("No decisions.")
        return

    summary = count_by_bucket(rows)
    print("Summary by bucket:", summary)
    print()

    columns = [
        ("bucket", 13),
        ("pair", 10),
        ("decision", 17),
        ("group", 15),
        ("priority", 8),
        ("final_score", 7),
        ("market_score", 7),
        ("telegram_score", 8),
        ("risk_level", 8),
        ("action_hint", 16),
    ]

    header = " | ".join(format_table_cell(name, width) for name, width in columns)
    separator = "-+-".join("-" * width for _, width in columns)

    print(header)
    print(separator)

    for row in rows:
        printable = dict(row)
        printable["final_score"] = round(float(row["final_score"]), 2)
        printable["market_score"] = round(float(row["market_score"]), 2)
        printable["telegram_score"] = round(float(row["telegram_score"]), 2)

        print(
            " | ".join(
                format_table_cell(printable.get(name), width)
                for name, width in columns
            )
        )

    print()
    print("Decision notes:")

    for row in rows:
        print(
            f"- {row['bucket']} {row['pair']}: "
            f"risks={row['risk_flags']}; "
            f"gap={row['scoring_gap']}; "
            f"next={row['next_step']}"
        )


def print_decision_line(item: Dict[str, Any]) -> None:
    print(
        str(item.get("pair")).ljust(10),
        "decision=" + str(item.get("decision")),
        "group=" + normalize_source_group(item.get("source_group")),
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


def print_safe_note(item: Dict[str, Any]) -> None:
    safe_note = str(item.get("safe_note") or "").strip()

    if safe_note:
        print("  Safe note:", safe_note)



def print_human_decision_fields(item: Dict[str, Any]) -> None:
    block_reasons = normalize_list(item.get("block_reasons", []))

    if block_reasons:
        print("  Human block reasons:")
        for reason in block_reasons:
            print("   -", reason)

    if item.get("risk_explanation"):
        print("  Risk explanation:", item.get("risk_explanation"))

    if item.get("manager_note"):
        print("  Manager note:", item.get("manager_note"))

    if item.get("recommended_next_step"):
        print("  Recommended next step:", item.get("recommended_next_step"))


def print_item_details(item: Dict[str, Any]) -> None:
    print_decision_line(item)
    print_message_details(item)
    print_scoring_gap(item)
    print_human_decision_fields(item)
    print_reasons(item)
    print_safe_note(item)
    print()


def print_section(title: str, items: List[Dict[str, Any]]) -> None:
    print()
    print(title)
    print("=" * len(title))

    if not items:
        print("None")
        return

    for item in items:
        print_item_details(item)


def print_payload_summary(payload: Dict[str, Any], decisions: List[Dict[str, Any]]) -> None:
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
    print("Summary by source group:", count_by_field(decisions, "source_group"))

    if payload.get("blockers"):
        print("Blockers:", ", ".join(str(item) for item in payload["blockers"]))
    else:
        print("Blockers: none")

    if payload.get("warnings"):
        print("Warnings:", ", ".join(str(item) for item in payload["warnings"]))
    else:
        print("Warnings: none")


def print_source_group_summary(decisions: List[Dict[str, Any]]) -> None:
    grouped = group_by_source_group(decisions)

    print()
    print("SOURCE GROUP SUMMARY")
    print("====================")

    if not decisions:
        print("No decisions.")
        return

    for source_group in SOURCE_GROUP_ORDER:
        items = grouped.get(source_group, [])

        if not items:
            continue

        print(
            SOURCE_GROUP_TITLES.get(source_group, source_group.upper()) + ":",
            len(items),
            count_by_field(items, "decision"),
        )

    unknown_groups = sorted(
        source_group
        for source_group in grouped
        if source_group not in SOURCE_GROUP_ORDER
    )

    for source_group in unknown_groups:
        items = grouped.get(source_group, [])
        print(
            "SOURCE GROUP: " + source_group.upper() + ":",
            len(items),
            count_by_field(items, "decision"),
        )


def print_grouped_by_decision(decisions: List[Dict[str, Any]]) -> None:
    grouped = group_decisions(decisions)

    print()
    print("DECISIONS BY TYPE")
    print("=================")

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


def print_grouped_by_source(decisions: List[Dict[str, Any]]) -> None:
    grouped = group_by_decision_inside_source(decisions)

    print()
    print("DECISIONS BY SOURCE GROUP")
    print("=========================")

    if not decisions:
        print("No decisions.")
        return

    for source_group in SOURCE_GROUP_ORDER:
        decision_map = grouped.get(source_group)

        if not decision_map:
            continue

        title = SOURCE_GROUP_TITLES.get(source_group, source_group.upper())
        print()
        print(title)
        print("=" * len(title))

        for decision in DECISION_ORDER:
            items = decision_map.get(decision, [])

            if not items:
                continue

            section_title = DECISION_TITLES.get(decision, decision.upper())
            print()
            print(section_title)
            print("-" * len(section_title))

            for item in items:
                print_item_details(item)

        unknown_decisions = sorted(
            decision
            for decision in decision_map
            if decision not in DECISION_ORDER
        )

        for decision in unknown_decisions:
            section_title = "UNKNOWN: " + decision
            print()
            print(section_title)
            print("-" * len(section_title))

            for item in decision_map.get(decision, []):
                print_item_details(item)

    unknown_groups = sorted(
        source_group
        for source_group in grouped
        if source_group not in SOURCE_GROUP_ORDER
    )

    for source_group in unknown_groups:
        decision_map = grouped.get(source_group, {})
        title = "SOURCE GROUP: " + source_group.upper()

        print()
        print(title)
        print("=" * len(title))

        for decision, items in sorted(decision_map.items()):
            section_title = DECISION_TITLES.get(decision, "UNKNOWN: " + decision)
            print()
            print(section_title)
            print("-" * len(section_title))

            for item in items:
                print_item_details(item)


def print_safety_block() -> None:
    print()
    print("SAFETY")
    print("======")
    print("[OK] This report did not create orders.")
    print("[OK] This report did not start trading bot.")
    print("[OK] This report did not call Binance API.")
    print("[OK] This report did not read Telegram.")
    print("[OK] This report only reads scanner_agent_decision.json.")
    print("[OK] Weak watchlist items are observation-only analytical records.")


def print_next_step(payload: Dict[str, Any], decisions: List[Dict[str, Any]]) -> None:
    print()
    print("NEXT STEP")
    print("=========")

    if not decisions:
        print("No decisions found. Rerun ./run_telegram_real_market_scanner_safe.sh")
        return

    summary = payload.get("summary_by_decision", {})
    by_source = count_by_field(decisions, "source_group")

    if summary.get("candidate"):
        print("There are strong analytical candidates, but orders are still disabled.")
        print("Next safe step: build a manual approval layer.")
        return

    if summary.get("wait_confirmation") or summary.get("wait_retest"):
        print("Signals require confirmation or retest.")
        print("Next safe step: improve notification/report text, not order execution.")
        return

    if by_source.get("weak_watchlist"):
        print("Only weak watchlist or ignored analytical signals are present.")
        print("Next safe step: continue collecting public Telegram messages and improve signal scoring.")
        return

    print("All signals are observation-only or ignored.")
    print("Next safe step: continue collecting more public Telegram messages.")


def main() -> None:
    payload = load_decision_payload()
    decisions = payload.get("decisions", [])

    if not isinstance(decisions, list):
        decisions = []

    print_payload_summary(payload, decisions)
    print_decision_status_table(decisions)
    print_source_group_summary(decisions)
    print_grouped_by_decision(decisions)
    print_grouped_by_source(decisions)
    print_safety_block()
    print_next_step(payload, decisions)


if __name__ == "__main__":
    main()
