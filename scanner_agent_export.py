import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from scanner_storage import get_connection, init_scanner_storage
from signal_rating import export_signal_for_agent


REPORTS_DIR = Path("reports")
EXPORT_PATH = REPORTS_DIR / "scanner_agent_export.json"

MIN_FINAL_SCORE = 60.0
EXCLUDED_STATUSES = {
    "пропустить",
    "опасный памп",
}


def load_raw_scanner_signals() -> List[Dict[str, Any]]:
    """
    Load raw scanner signals from SQLite.

    The raw_signal_json field contains the full analytical signal
    saved by scanner_demo.py / future scanner pipeline.
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


def is_export_candidate(signal: Dict[str, Any]) -> bool:
    """
    Select only useful analytical candidates for the future agent layer.

    This does not approve trades.
    It only filters scanner signals for further market analysis.
    """
    status = str(signal.get("status", ""))
    final_score = float(signal.get("final_score", 0.0))

    if status in EXCLUDED_STATUSES:
        return False

    if final_score < MIN_FINAL_SCORE:
        return False

    return True


def build_agent_export_payload(signals: List[Dict[str, Any]]) -> Dict[str, Any]:
    candidates = []

    for signal in signals:
        if not is_export_candidate(signal):
            continue

        agent_item = export_signal_for_agent(signal)

        agent_item["final_score"] = signal.get("final_score")
        agent_item["market_score"] = signal.get("market_score")
        agent_item["risk_adjustment"] = signal.get("risk_adjustment")
        agent_item["created_by"] = "scanner_agent_export"
        agent_item["analytical_only"] = True
        agent_item["order_execution_allowed"] = False

        candidates.append(agent_item)

    candidates.sort(
        key=lambda item: float(item.get("final_score") or 0.0),
        reverse=True,
    )

    return {
        "source": "telegram_social_scanner",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analytical_only": True,
        "order_execution_allowed": False,
        "min_final_score": MIN_FINAL_SCORE,
        "excluded_statuses": sorted(EXCLUDED_STATUSES),
        "total_candidates": len(candidates),
        "candidates": candidates,
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


def print_agent_export_summary(payload: Dict[str, Any], export_path: Path) -> None:
    print("SCANNER AGENT EXPORT")
    print("====================")
    print("Export path:", export_path)
    print("Analytical only:", payload["analytical_only"])
    print("Order execution allowed:", payload["order_execution_allowed"])
    print("Min final score:", payload["min_final_score"])
    print("Total candidates:", payload["total_candidates"])
    print()

    candidates = payload.get("candidates", [])

    if not candidates:
        print("No export candidates found.")
        return

    print("CANDIDATES")
    print("==========")

    for item in candidates:
        print(
            str(item.get("pair")).ljust(10),
            "status=" + str(item.get("suggested_status")),
            "final=" + str(item.get("final_score")),
            "telegram=" + str(item.get("telegram_score")),
            "market=" + str(item.get("market_score")),
            "risks=" + (", ".join(item.get("risk_flags", [])) or "none"),
        )


def main() -> None:
    signals = load_raw_scanner_signals()
    payload = build_agent_export_payload(signals)
    export_path = save_agent_export(payload)
    print_agent_export_summary(payload, export_path)


if __name__ == "__main__":
    main()
