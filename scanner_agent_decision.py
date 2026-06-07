import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


REPORTS_DIR = Path("reports")
INPUT_PATH = REPORTS_DIR / "scanner_agent_export.json"
OUTPUT_PATH = REPORTS_DIR / "scanner_agent_decision.json"

BLOCKING_RISKS = {
    "pump_risk",
    "dangerous_fomo",
}

CONFIRMATION_FLAGS = {
    "message_wait_confirmation",
}

LIQUIDITY_RISKS = {
    "low_liquidity",
}

MIN_CANDIDATE_SCORE = 70.0
MIN_OBSERVE_SCORE = 55.0


def load_agent_export(path: Path = INPUT_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {
            "error": f"Agent export file not found: {path}",
            "candidates": [],
            "watchlist_candidates": [],
            "blockers": ["agent_export_file_not_found"],
            "warnings": [],
            "safe_to_continue": False,
        }

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as ex:
        return {
            "error": f"Invalid agent export JSON: {ex}",
            "candidates": [],
            "watchlist_candidates": [],
            "blockers": ["invalid_agent_export_json"],
            "warnings": [],
            "safe_to_continue": False,
        }


def normalize_risk_flags(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]

    if isinstance(value, str) and value.strip():
        return [
            item.strip()
            for item in value.split(",")
            if item.strip()
        ]

    return []


def has_any(items: List[str], flags: set[str]) -> bool:
    return any(item in flags for item in items)


def build_decision_reason(
    item: Dict[str, Any],
    decision: str,
    risk_flags: List[str],
    message_flags: List[str],
) -> List[str]:
    reasons: List[str] = []

    status = str(item.get("suggested_status", ""))
    final_score = float(item.get("final_score") or 0.0)
    market_score = float(item.get("market_score") or 0.0)
    telegram_score = float(item.get("telegram_score") or 0.0)
    has_retest = bool(item.get("has_retest"))
    message_intent = str(item.get("message_intent") or "")

    reasons.append(f"status={status}")
    reasons.append(f"final_score={final_score}")
    reasons.append(f"market_score={market_score}")
    reasons.append(f"telegram_score={telegram_score}")
    reasons.append(f"has_retest={has_retest}")

    if message_intent:
        reasons.append(f"message_intent={message_intent}")

    if risk_flags:
        reasons.append("risk_flags=" + ",".join(risk_flags))
    else:
        reasons.append("risk_flags=none")

    if message_flags:
        reasons.append("message_flags=" + ",".join(message_flags))

    if decision == "blocked_risk":
        reasons.append("blocked because dangerous or weak-risk conditions were detected")

    if decision == "wait_confirmation":
        reasons.append("message asks to wait for confirmation")

    if decision == "wait_retest":
        reasons.append("нужен ретест или подтверждение перед любыми действиями")

    if decision == "observe":
        reasons.append("signal is suitable only for observation")

    if decision == "candidate":
        reasons.append("strong analytical candidate, still not a trade entry")

    if decision == "ignore":
        reasons.append("сигнал слабый, нейтральный или не подходит для действия")

    return reasons


def decide_item(item: Dict[str, Any], source_group: str) -> Dict[str, Any]:
    risk_flags = normalize_risk_flags(item.get("risk_flags", []))
    message_flags = normalize_risk_flags(item.get("message_risk_flags", []))

    status = str(item.get("suggested_status", ""))
    final_score = float(item.get("final_score") or 0.0)
    market_score = float(item.get("market_score") or 0.0)
    telegram_score = float(item.get("telegram_score") or 0.0)
    has_retest = bool(item.get("has_retest"))
    message_intent = str(item.get("message_intent") or "")

    decision = "ignore"
    priority = 0

    if has_any(risk_flags, BLOCKING_RISKS):
        decision = "blocked_risk"
        priority = 90

    elif "low_liquidity" in risk_flags and final_score < MIN_OBSERVE_SCORE:
        decision = "blocked_risk"
        priority = 70

    elif has_any(risk_flags, CONFIRMATION_FLAGS) or has_any(message_flags, CONFIRMATION_FLAGS):
        if has_retest and final_score >= MIN_OBSERVE_SCORE:
            decision = "wait_confirmation"
            priority = 60
        else:
            decision = "wait_retest"
            priority = 55

    elif not has_retest and status in {"ждать ретест"}:
        decision = "wait_retest"
        priority = 55

    elif status in {"движение возможно", "ждать ретест"} and final_score >= MIN_CANDIDATE_SCORE:
        decision = "candidate"
        priority = 80

    elif status == "только наблюдать" and final_score >= MIN_OBSERVE_SCORE:
        decision = "observe"
        priority = 50

    elif final_score >= MIN_OBSERVE_SCORE and market_score >= 60:
        decision = "observe"
        priority = 45

    elif message_intent == "neutral" and telegram_score < 30:
        decision = "ignore"
        priority = 10

    else:
        decision = "ignore"
        priority = 20

    return {
        "source": "scanner_agent_decision",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analytical_only": True,
        "order_execution_allowed": False,
        "trading_enabled": False,
        "decision": decision,
        "priority": priority,
        "source_group": source_group,
        "ticker": item.get("ticker"),
        "pair": item.get("pair"),
        "exchange": item.get("exchange"),
        "suggested_status": status,
        "final_score": final_score,
        "telegram_score": telegram_score,
        "market_score": market_score,
        "risk_adjustment": item.get("risk_adjustment"),
        "risk_flags": risk_flags,
        "has_retest": has_retest,
        "market_confirmation": bool(item.get("market_confirmation")),
        "message_intent": item.get("message_intent"),
        "message_quality_score": item.get("message_quality_score"),
        "message_score_adjustment": item.get("message_score_adjustment"),
        "message_risk_flags": message_flags,
        "message_reasons": item.get("message_reasons", []),
        "message_intent_counts": item.get("message_intent_counts", {}),
        "reasons": build_decision_reason(
            item=item,
            decision=decision,
            risk_flags=risk_flags,
            message_flags=message_flags,
        ),
        "safe_note": (
            "This is an analytical decision only. "
            "It is not a trading entry and it cannot create orders."
        ),
    }


def build_not_ready_payload(export_payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source": "scanner_agent_decision",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "input_file": str(INPUT_PATH),
        "output_file": str(OUTPUT_PATH),
        "analytical_only": True,
        "order_execution_allowed": False,
        "trading_enabled": False,
        "safe_to_continue": False,
        "decisions": [],
        "total_decisions": 0,
        "summary_by_decision": {},
        "blockers": export_payload.get("blockers", []) or ["agent_export_not_ready"],
        "warnings": export_payload.get("warnings", []),
        "error": export_payload.get("error"),
        "disclaimer": (
            "Telegram/social signal is not a trading entry. "
            "This decision layer is analytical only. "
            "No orders are created."
        ),
    }


def count_by_decision(decisions: List[Dict[str, Any]]) -> Dict[str, int]:
    summary: Dict[str, int] = {}

    for item in decisions:
        decision = str(item.get("decision", "unknown"))
        summary[decision] = summary.get(decision, 0) + 1

    return dict(sorted(summary.items()))


def build_decision_payload(export_payload: Dict[str, Any]) -> Dict[str, Any]:
    if export_payload.get("error"):
        return build_not_ready_payload(export_payload)

    candidates = export_payload.get("candidates", [])
    watchlist_candidates = export_payload.get("watchlist_candidates", [])

    if not isinstance(candidates, list):
        candidates = []

    if not isinstance(watchlist_candidates, list):
        watchlist_candidates = []

    decisions: List[Dict[str, Any]] = []

    for item in candidates:
        if isinstance(item, dict):
            source_group = str(item.get("export_group") or "candidate")
            decisions.append(decide_item(item, source_group=source_group))

    for item in watchlist_candidates:
        if isinstance(item, dict):
            source_group = str(item.get("export_group") or "watchlist")
            decisions.append(decide_item(item, source_group=source_group))

    decisions.sort(
        key=lambda item: (
            int(item.get("priority", 0)),
            float(item.get("final_score") or 0.0),
        ),
        reverse=True,
    )

    return {
        "source": "scanner_agent_decision",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "input_file": str(INPUT_PATH),
        "output_file": str(OUTPUT_PATH),
        "input_source": export_payload.get("source"),
        "input_created_at": export_payload.get("created_at"),
        "analytical_only": True,
        "order_execution_allowed": False,
        "trading_enabled": False,
        "safe_to_continue": True,
        "total_input_candidates": len(candidates),
        "total_input_watchlist_candidates": len(watchlist_candidates),
        "total_decisions": len(decisions),
        "summary_by_decision": count_by_decision(decisions),
        "decisions": decisions,
        "blockers": [],
        "warnings": [],
        "disclaimer": (
            "Telegram/social signal is not a trading entry. "
            "This decision layer is analytical only. "
            "No orders are created."
        ),
    }


def save_decision_payload(payload: Dict[str, Any], path: Path = OUTPUT_PATH) -> Path:
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


def format_flags(flags: Any) -> str:
    if isinstance(flags, list):
        return ", ".join(str(item) for item in flags) or "none"

    if flags:
        return str(flags)

    return "none"


def print_decision_item(item: Dict[str, Any]) -> None:
    print(
        str(item.get("pair")).ljust(10),
        "decision=" + str(item.get("decision")),
        "priority=" + str(item.get("priority")),
        "status=" + str(item.get("suggested_status")),
        "final=" + str(item.get("final_score")),
        "market=" + str(item.get("market_score")),
        "telegram=" + str(item.get("telegram_score")),
        "retest=" + str(item.get("has_retest")),
        "risks=" + format_flags(item.get("risk_flags")),
        "message=" + str(item.get("message_intent")),
    )


def print_decision_summary(payload: Dict[str, Any], output_path: Path) -> None:
    print("SCANNER AGENT DECISION")
    print("======================")
    print("Mode: analytical only")
    print("Orders enabled:", payload.get("order_execution_allowed"))
    print("Trading enabled:", payload.get("trading_enabled"))
    print("Input file:", payload.get("input_file"))
    print("Output file:", output_path)
    print()

    if payload.get("error"):
        print("[FAIL]", payload.get("error"))

    print("SUMMARY")
    print("=======")
    print("Safe to continue:", payload.get("safe_to_continue"))
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

    print()
    print("DECISIONS")
    print("=========")

    decisions = payload.get("decisions", [])

    if not decisions:
        print("No decisions.")
    else:
        for item in decisions:
            print_decision_item(item)

    print()
    print("SAFETY")
    print("======")
    print("[OK] This decision layer did not create orders.")
    print("[OK] This decision layer did not start trading bot.")
    print("[OK] This decision layer did not call Binance API.")
    print("[OK] This decision layer used only scanner_agent_export.json.")

    print()
    print("NEXT STEP")
    print("=========")

    if not decisions:
        print("No analytical decisions found. Add stronger real Telegram messages or rerun scanner.")
        return

    print("Decision JSON is ready for the future agent layer.")
    print("Keep order execution disabled until a separate manual approval layer exists.")


def main() -> None:
    export_payload = load_agent_export()
    decision_payload = build_decision_payload(export_payload)
    output_path = save_decision_payload(decision_payload)
    print_decision_summary(decision_payload, output_path)


if __name__ == "__main__":
    main()
