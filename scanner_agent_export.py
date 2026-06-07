import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from scanner_storage import get_connection, init_scanner_storage
from signal_rating import export_signal_for_agent


REPORTS_DIR = Path("reports")
EXPORT_PATH = REPORTS_DIR / "scanner_agent_export.json"

MIN_FINAL_SCORE = 60.0
MIN_WATCHLIST_SCORE = 55.0
MIN_WEAK_WATCHLIST_SCORE = 35.0

BLOCKED_STATUSES = {
    "опасный памп",
}

CANDIDATE_STATUSES = {
    "движение возможно",
    "ждать ретест",
}

WATCHLIST_STATUSES = {
    "только наблюдать",
}

WEAK_WATCHLIST_STATUSES = {
    "пропустить",
}


def load_raw_scanner_signals() -> List[Dict[str, Any]]:
    """
    Load raw scanner signals from SQLite.

    The raw_signal_json field contains the full analytical signal
    saved by scanner_demo.py / scanner_real_market_demo.py / future scanner pipeline.
    """
    init_scanner_storage()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT raw_signal_json
            FROM scanner_signals
            ORDER BY id ASC
            """
        )

        rows = cursor.fetchall()

    signals: List[Dict[str, Any]] = []

    for row in rows:
        raw_json = row[0]

        try:
            signal = json.loads(raw_json)
        except json.JSONDecodeError:
            continue

        if isinstance(signal, dict):
            signals.append(signal)

    return signals


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def get_risk_flags(signal: Dict[str, Any]) -> List[str]:
    risk_flags = signal.get("risk_flags", [])

    if isinstance(risk_flags, list):
        return [str(item) for item in risk_flags]

    if isinstance(risk_flags, str) and risk_flags.strip():
        return [
            item.strip()
            for item in risk_flags.split(",")
            if item.strip()
        ]

    return []


def get_social_signal(signal: Dict[str, Any]) -> Dict[str, Any]:
    social_signal = signal.get("social_signal", {})

    if isinstance(social_signal, dict):
        return social_signal

    return {}


def get_message_intent(signal: Dict[str, Any]) -> str:
    social_signal = get_social_signal(signal)
    return str(social_signal.get("message_intent") or "").strip()


def get_message_score_adjustment(signal: Dict[str, Any]) -> float:
    social_signal = get_social_signal(signal)
    return safe_float(social_signal.get("message_score_adjustment"), 0.0)


def is_blocked_signal(signal: Dict[str, Any]) -> bool:
    """
    Block only clearly dangerous analytical signals.

    Important:
    - Status 'пропустить' is no longer automatically blocked.
    - Weak safe signals may still be exported to watchlist for observation.
    - This does not approve trades and does not allow order execution.
    """
    status = str(signal.get("status", ""))
    risk_flags = get_risk_flags(signal)

    if status in BLOCKED_STATUSES:
        return True

    if "pump_risk" in risk_flags:
        return True

    if "dangerous_fomo" in risk_flags:
        return True

    return False


def is_export_candidate(signal: Dict[str, Any]) -> bool:
    """
    Select stronger analytical candidates for the future agent layer.

    Important:
    - This does not approve trades.
    - This does not allow order execution.
    - Status 'только наблюдать' and 'пропустить' must never become candidates.
    """
    if is_blocked_signal(signal):
        return False

    status = str(signal.get("status", ""))
    final_score = safe_float(signal.get("final_score"), 0.0)

    if status not in CANDIDATE_STATUSES:
        return False

    if final_score < MIN_FINAL_SCORE:
        return False

    return True


def is_weak_watchlist_candidate(signal: Dict[str, Any]) -> bool:
    """
    Select weak but safe analytical signals for observation only.

    This exists because status 'пропустить' can still contain useful information:
    - neutral BTC/ETH market mention;
    - SOL/TON watch message;
    - low score but no dangerous risk flags.

    Weak watchlist signals:
    - are NOT trade candidates;
    - are NOT order permissions;
    - are only passed to the decision/report layer for visibility.
    """
    if is_blocked_signal(signal):
        return False

    status = str(signal.get("status", ""))
    final_score = safe_float(signal.get("final_score"), 0.0)
    market_score = safe_float(signal.get("market_score"), 0.0)
    telegram_score = safe_float(signal.get("telegram_score"), 0.0)
    message_intent = get_message_intent(signal)
    message_score_adjustment = get_message_score_adjustment(signal)

    if status not in WEAK_WATCHLIST_STATUSES:
        return False

    if final_score < MIN_WEAK_WATCHLIST_SCORE:
        return False

    if telegram_score > 0:
        return True

    if message_score_adjustment > 0:
        return True

    if message_intent in {"watch_signal", "possible_news"}:
        return True

    if market_score >= 40:
        return True

    return False


def is_watchlist_candidate(signal: Dict[str, Any]) -> bool:
    """
    Select weaker but still interesting signals for observation.

    Example:
    - strong Telegram/social signal;
    - market is not confirmed yet;
    - status is 'только наблюдать';
    - status is 'пропустить' but final score is still useful for observation.
    """
    if is_blocked_signal(signal):
        return False

    if is_export_candidate(signal):
        return False

    status = str(signal.get("status", ""))
    final_score = safe_float(signal.get("final_score"), 0.0)

    if status in WATCHLIST_STATUSES:
        return True

    if status == "ждать ретест" and final_score < MIN_FINAL_SCORE:
        return True

    if final_score >= MIN_WATCHLIST_SCORE:
        return True

    if is_weak_watchlist_candidate(signal):
        return True

    return False


def get_export_group(signal: Dict[str, Any]) -> str:
    status = str(signal.get("status", ""))

    if status in WEAK_WATCHLIST_STATUSES:
        return "weak_watchlist"

    return "watchlist"


def build_agent_item(signal: Dict[str, Any], export_group: str) -> Dict[str, Any]:
    agent_item = export_signal_for_agent(signal)

    social_signal = get_social_signal(signal)
    classification_summary = social_signal.get("message_classification_summary", {})

    if not isinstance(classification_summary, dict):
        classification_summary = {}

    agent_item["final_score"] = signal.get("final_score")
    agent_item["market_score"] = signal.get("market_score")
    agent_item["risk_adjustment"] = signal.get("risk_adjustment")

    agent_item["message_intent"] = social_signal.get("message_intent")
    agent_item["message_quality_score"] = social_signal.get("message_quality_score")
    agent_item["message_score_adjustment"] = social_signal.get("message_score_adjustment")
    agent_item["message_risk_flags"] = social_signal.get("message_risk_flags", [])
    agent_item["message_reasons"] = classification_summary.get("reasons", [])
    agent_item["message_intent_counts"] = classification_summary.get("counts_by_intent", {})

    agent_item["created_by"] = "scanner_agent_export"
    agent_item["export_group"] = export_group
    agent_item["analytical_only"] = True
    agent_item["order_execution_allowed"] = False

    return agent_item


def build_agent_export_payload(signals: List[Dict[str, Any]]) -> Dict[str, Any]:
    candidates: List[Dict[str, Any]] = []
    watchlist_candidates: List[Dict[str, Any]] = []
    blocked_count = 0
    ignored_count = 0

    for signal in signals:
        if is_export_candidate(signal):
            candidates.append(build_agent_item(signal, export_group="candidate"))
            continue

        if is_watchlist_candidate(signal):
            watchlist_candidates.append(
                build_agent_item(
                    signal,
                    export_group=get_export_group(signal),
                )
            )
            continue

        if is_blocked_signal(signal):
            blocked_count += 1
        else:
            ignored_count += 1

    candidates.sort(
        key=lambda item: safe_float(item.get("final_score"), 0.0),
        reverse=True,
    )

    watchlist_candidates.sort(
        key=lambda item: safe_float(item.get("final_score"), 0.0),
        reverse=True,
    )

    return {
        "source": "telegram_social_scanner",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analytical_only": True,
        "order_execution_allowed": False,
        "min_final_score": MIN_FINAL_SCORE,
        "min_watchlist_score": MIN_WATCHLIST_SCORE,
        "min_weak_watchlist_score": MIN_WEAK_WATCHLIST_SCORE,
        "candidate_statuses": sorted(CANDIDATE_STATUSES),
        "blocked_statuses": sorted(BLOCKED_STATUSES),
        "weak_watchlist_statuses": sorted(WEAK_WATCHLIST_STATUSES),
        "watchlist_statuses": sorted(WATCHLIST_STATUSES),
        "total_signals_loaded": len(signals),
        "total_candidates": len(candidates),
        "total_watchlist_candidates": len(watchlist_candidates),
        "blocked_signals": blocked_count,
        "ignored_signals": ignored_count,
        "candidates": candidates,
        "watchlist_candidates": watchlist_candidates,
        "disclaimer": (
            "Telegram/social signal is not a trading entry. "
            "This export is for analytical filtering only. "
            "Weak watchlist signals are observation-only. "
            "No orders are created."
        ),
    }


def save_agent_export(payload: Dict[str, Any]) -> Path:
    REPORTS_DIR.mkdir(exist_ok=True)

    EXPORT_PATH.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    return EXPORT_PATH


def print_items(title: str, items: List[Dict[str, Any]]) -> None:
    print(title)
    print("=" * len(title))

    if not items:
        print("None")
        return

    for item in items:
        print(
            str(item.get("pair")).ljust(10),
            "group=" + str(item.get("export_group")),
            "status=" + str(item.get("suggested_status")),
            "final=" + str(item.get("final_score")),
            "telegram=" + str(item.get("telegram_score")),
            "market=" + str(item.get("market_score")),
            "risks=" + (", ".join(item.get("risk_flags", [])) or "none"),
        )


def print_agent_export_summary(payload: Dict[str, Any], export_path: Path) -> None:
    print("SCANNER AGENT EXPORT")
    print("====================")
    print("Export path:", export_path)
    print("Analytical only:", payload["analytical_only"])
    print("Order execution allowed:", payload["order_execution_allowed"])
    print("Min final score:", payload["min_final_score"])
    print("Min watchlist score:", payload["min_watchlist_score"])
    print("Min weak watchlist score:", payload["min_weak_watchlist_score"])
    print("Candidate statuses:", ", ".join(payload["candidate_statuses"]))
    print("Watchlist statuses:", ", ".join(payload["watchlist_statuses"]))
    print("Weak watchlist statuses:", ", ".join(payload["weak_watchlist_statuses"]))
    print("Blocked statuses:", ", ".join(payload["blocked_statuses"]))
    print("Total signals loaded:", payload["total_signals_loaded"])
    print("Total candidates:", payload["total_candidates"])
    print("Total watchlist candidates:", payload["total_watchlist_candidates"])
    print("Blocked signals:", payload["blocked_signals"])
    print("Ignored signals:", payload["ignored_signals"])
    print()

    print_items("CANDIDATES", payload.get("candidates", []))
    print()
    print_items("WATCHLIST CANDIDATES", payload.get("watchlist_candidates", []))


def main() -> None:
    signals = load_raw_scanner_signals()
    payload = build_agent_export_payload(signals)
    export_path = save_agent_export(payload)
    print_agent_export_summary(payload, export_path)


if __name__ == "__main__":
    main()
