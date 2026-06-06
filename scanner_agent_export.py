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

EXCLUDED_STATUSES = {
    "пропустить",
    "опасный памп",
}

WATCHLIST_STATUSES = {
    "только наблюдать",
    "ждать ретест",
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


def is_blocked_signal(signal: Dict[str, Any]) -> bool:
    """
    Block signals that must not be sent to the future agent layer.

    This does not approve trades.
    It only prevents dangerous or useless analytical signals from being exported.
    """
    status = str(signal.get("status", ""))
    risk_flags = signal.get("risk_flags", [])

    if status in EXCLUDED_STATUSES:
        return True

    if isinstance(risk_flags, list) and "pump_risk" in risk_flags:
        return True

    return False


def is_export_candidate(signal: Dict[str, Any]) -> bool:
    """
    Select stronger analytical candidates for the future agent layer.

    This does not approve trades.
    It only filters scanner signals for deeper market analysis.
    """
    if is_blocked_signal(signal):
        return False

    final_score = float(signal.get("final_score", 0.0))

    if final_score < MIN_FINAL_SCORE:
        return False

    return True


def is_watchlist_candidate(signal: Dict[str, Any]) -> bool:
    """
    Select weaker but still interesting signals for observation.

    Example:
    - strong Telegram/social signal;
    - market not confirmed yet;
    - status is 'только наблюдать';
    - final score is below strict candidate threshold.
    """
    if is_blocked_signal(signal):
        return False

    status = str(signal.get("status", ""))
    final_score = float(signal.get("final_score", 0.0))

    if is_export_candidate(signal):
        return False

    if status in WATCHLIST_STATUSES:
        return True

    if final_score >= MIN_WATCHLIST_SCORE:
        return True

    return False


def build_agent_item(signal: Dict[str, Any], export_group: str) -> Dict[str, Any]:
    agent_item = export_signal_for_agent(signal)

    agent_item["final_score"] = signal.get("final_score")
    agent_item["market_score"] = signal.get("market_score")
    agent_item["risk_adjustment"] = signal.get("risk_adjustment")
    agent_item["created_by"] = "scanner_agent_export"
    agent_item["export_group"] = export_group
    agent_item["analytical_only"] = True
    agent_item["order_execution_allowed"] = False

    return agent_item


def build_agent_export_payload(signals: List[Dict[str, Any]]) -> Dict[str, Any]:
    candidates: List[Dict[str, Any]] = []
    watchlist_candidates: List[Dict[str, Any]] = []
    blocked_count = 0

    for signal in signals:
        if is_export_candidate(signal):
            candidates.append(build_agent_item(signal, export_group="candidate"))
            continue

        if is_watchlist_candidate(signal):
            watchlist_candidates.append(build_agent_item(signal, export_group="watchlist"))
            continue

        if is_blocked_signal(signal):
            blocked_count += 1

    candidates.sort(
        key=lambda item: float(item.get("final_score") or 0.0),
        reverse=True,
    )

    watchlist_candidates.sort(
        key=lambda item: float(item.get("final_score") or 0.0),
        reverse=True,
    )

    return {
        "source": "telegram_social_scanner",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analytical_only": True,
        "order_execution_allowed": False,
        "min_final_score": MIN_FINAL_SCORE,
        "min_watchlist_score": MIN_WATCHLIST_SCORE,
        "excluded_statuses": sorted(EXCLUDED_STATUSES),
        "watchlist_statuses": sorted(WATCHLIST_STATUSES),
        "total_signals_loaded": len(signals),
        "total_candidates": len(candidates),
        "total_watchlist_candidates": len(watchlist_candidates),
        "blocked_signals": blocked_count,
        "candidates": candidates,
        "watchlist_candidates": watchlist_candidates,
        "disclaimer": (
            "Telegram/social signal is not a trading entry. "
            "This export is for analytical filtering only. "
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
    print("Total signals loaded:", payload["total_signals_loaded"])
    print("Total candidates:", payload["total_candidates"])
    print("Total watchlist candidates:", payload["total_watchlist_candidates"])
    print("Blocked signals:", payload["blocked_signals"])
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
