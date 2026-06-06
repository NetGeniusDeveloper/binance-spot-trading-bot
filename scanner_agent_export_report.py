import json
from pathlib import Path
from typing import Any, Dict, List


EXPORT_PATH = Path("reports") / "scanner_agent_export.json"


def load_export_payload(path: Path = EXPORT_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {
            "error": f"Export file not found: {path}",
            "candidates": [],
            "watchlist_candidates": [],
        }

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as ex:
        return {
            "error": f"Invalid JSON export: {ex}",
            "candidates": [],
            "watchlist_candidates": [],
        }


def format_risks(item: Dict[str, Any]) -> str:
    risk_flags = item.get("risk_flags", [])

    if not risk_flags:
        return "none"

    if isinstance(risk_flags, list):
        return ", ".join(str(flag) for flag in risk_flags)

    return str(risk_flags)


def print_item(item: Dict[str, Any]) -> None:
    print(
        str(item.get("pair")).ljust(10),
        "status=" + str(item.get("suggested_status")),
        "final=" + str(item.get("final_score")),
        "telegram=" + str(item.get("telegram_score")),
        "market=" + str(item.get("market_score")),
        "retest=" + str(item.get("has_retest")),
        "risks=" + format_risks(item),
    )


def print_section(title: str, items: List[Dict[str, Any]]) -> None:
    print()
    print(title)
    print("=" * len(title))

    if not items:
        print("None")
        return

    for item in items:
        print_item(item)


def print_safety_block(payload: Dict[str, Any]) -> None:
    print()
    print("SAFETY")
    print("======")
    print("Analytical only:", payload.get("analytical_only"))
    print("Order execution allowed:", payload.get("order_execution_allowed"))
    print("Source:", payload.get("source"))
    print("Created at:", payload.get("created_at"))
    print("Min final score:", payload.get("min_final_score"))
    print("Min watchlist score:", payload.get("min_watchlist_score"))

    if payload.get("order_execution_allowed") is False:
        print("[OK] Orders are disabled.")
    else:
        print("[WARN] order_execution_allowed is not false. Check export config.")


def print_summary(payload: Dict[str, Any]) -> None:
    print("SCANNER AGENT EXPORT REPORT")
    print("===========================")

    if payload.get("error"):
        print("[FAIL]", payload["error"])
        return

    print("Export file:", EXPORT_PATH)
    print("Total signals loaded:", payload.get("total_signals_loaded"))
    print("Trade candidates:", payload.get("total_candidates"))
    print("Watchlist candidates:", payload.get("total_watchlist_candidates"))
    print("Blocked signals:", payload.get("blocked_signals"))

    print_safety_block(payload)

    candidates = payload.get("candidates", [])
    watchlist_candidates = payload.get("watchlist_candidates", [])

    print_section("TRADE CANDIDATES", candidates)
    print_section("WATCHLIST CANDIDATES", watchlist_candidates)

    print()
    print("BLOCKED / REJECTED SUMMARY")
    print("==========================")
    print("Blocked signals:", payload.get("blocked_signals"))
    print("Excluded statuses:", ", ".join(payload.get("excluded_statuses", [])) or "none")

    print()
    print("DISCLAIMER")
    print("==========")
    print("This report is analytical only.")
    print("Telegram/social signal is not a trading entry.")
    print("No orders are created.")
    print("Crypto assets are high-risk. Final decision is always user's responsibility.")


def main() -> None:
    payload = load_export_payload()
    print_summary(payload)


if __name__ == "__main__":
    main()
