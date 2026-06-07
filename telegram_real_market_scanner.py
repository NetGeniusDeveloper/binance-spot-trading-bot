import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from scanner_market_data import get_market_metrics_for_watchlist
from scanner_report import print_console_report, save_markdown_report
from scanner_storage import save_scanner_signals
from signal_rating import build_signal_rating


REPORTS_DIR = Path("reports")
INPUT_PATH = REPORTS_DIR / "telegram_real_social_signals.json"
OUTPUT_PATH = REPORTS_DIR / "telegram_real_market_rated_signals.json"


def load_real_social_payload(path: Path = INPUT_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {
            "safe_to_continue": False,
            "blockers": [f"input_file_not_found:{path}"],
            "warnings": [],
            "signals": [],
        }

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as ex:
        return {
            "safe_to_continue": False,
            "blockers": [f"invalid_json:{ex}"],
            "warnings": [],
            "signals": [],
        }

    if not isinstance(payload, dict):
        return {
            "safe_to_continue": False,
            "blockers": ["input_payload_is_not_dict"],
            "warnings": [],
            "signals": [],
        }

    return payload


def extract_social_signals(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    signals = payload.get("signals", [])

    if not isinstance(signals, list):
        return []

    result: List[Dict[str, Any]] = []

    for signal in signals:
        if not isinstance(signal, dict):
            continue

        ticker = str(signal.get("ticker", "")).strip().upper()

        if not ticker:
            continue

        normalized_signal = {
            **signal,
            "ticker": ticker,
        }

        result.append(normalized_signal)

    return result


def filter_market_symbols(social_signals: List[Dict[str, Any]]) -> List[str]:
    symbols: List[str] = []

    for signal in social_signals:
        ticker = str(signal.get("ticker", "")).strip().upper()

        if not ticker:
            continue

        if ticker == "PUMP":
            continue

        if ticker not in symbols:
            symbols.append(ticker)

    return symbols


def build_rated_signals_from_real_social(
    social_signals: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    market_symbols = filter_market_symbols(social_signals)

    if market_symbols:
        print("Loading real Binance market metrics for:", ", ".join(market_symbols))
    else:
        print("No market symbols found from real Telegram social signals.")

    print()

    market_metrics_by_symbol = get_market_metrics_for_watchlist(
        symbols=market_symbols,
        quote="USDT",
        interval="1m",
        limit=240,
    )

    rated_signals: List[Dict[str, Any]] = []

    for social_signal in social_signals:
        ticker = str(social_signal.get("ticker", "")).strip().upper()

        if not ticker:
            continue

        metrics = market_metrics_by_symbol.get(ticker, {})

        if metrics.get("error"):
            print("Skipping", ticker, "because market metrics returned error:", metrics["error"])
            continue

        rated_signals.append(
            build_signal_rating(
                social_signal=social_signal,
                market_metrics=metrics,
            )
        )

    rated_signals.sort(
        key=lambda item: (
            item.get("status") == "движение возможно",
            float(item.get("final_score", 0.0)),
        ),
        reverse=True,
    )

    return rated_signals


def build_output_payload(
    source_payload: Dict[str, Any],
    social_signals: List[Dict[str, Any]],
    rated_signals: List[Dict[str, Any]],
    saved_ids: List[int],
) -> Dict[str, Any]:
    return {
        "source": "telegram_real_market_scanner",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analytical_only": True,
        "orders_enabled": False,
        "trading_enabled": False,
        "binance_private_api_used": False,
        "binance_orders_created": False,
        "telegram_messages_read": False,
        "input_file": str(INPUT_PATH),
        "input_source": source_payload.get("source"),
        "input_created_at": source_payload.get("created_at"),
        "messages_loaded": source_payload.get("messages_loaded"),
        "social_signals_loaded": len(social_signals),
        "rated_signals_count": len(rated_signals),
        "saved_signal_ids": saved_ids,
        "tickers_detected": [
            str(signal.get("ticker"))
            for signal in social_signals
            if signal.get("ticker")
        ],
        "rated_signals": rated_signals,
        "blockers": [],
        "warnings": source_payload.get("warnings", []),
        "disclaimer": (
            "Telegram/social signal is not a trading entry. "
            "This scanner combines saved Telegram analytics with public Binance market data only. "
            "No orders are created."
        ),
    }


def save_output_payload(payload: Dict[str, Any]) -> Path:
    REPORTS_DIR.mkdir(exist_ok=True)

    OUTPUT_PATH.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )

    return OUTPUT_PATH


def print_market_scanner_summary(
    payload: Dict[str, Any],
    output_path: Path,
) -> None:
    print("TELEGRAM REAL MARKET SCANNER")
    print("============================")
    print("Mode: analytical only")
    print("Orders enabled:", payload.get("orders_enabled"))
    print("Trading enabled:", payload.get("trading_enabled"))
    print("Binance private API used:", payload.get("binance_private_api_used"))
    print("Binance orders created:", payload.get("binance_orders_created"))
    print("Telegram messages read:", payload.get("telegram_messages_read"))
    print("Input file:", payload.get("input_file"))
    print("Output file:", output_path)
    print()

    print("SUMMARY")
    print("=======")
    print("Messages loaded:", payload.get("messages_loaded"))
    print("Social signals loaded:", payload.get("social_signals_loaded"))
    print("Rated signals:", payload.get("rated_signals_count"))
    print("Saved signal ids:", payload.get("saved_signal_ids"))
    print("Tickers detected:", ", ".join(payload.get("tickers_detected", [])) or "none")

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
    print("[OK] This scanner did not create orders.")
    print("[OK] This scanner did not start trading bot.")
    print("[OK] This scanner used only saved Telegram social analysis JSON.")
    print("[OK] Binance was used only for public market metrics.")

    print()
    print("NEXT STEP")
    print("=========")

    if payload.get("rated_signals_count", 0) <= 0:
        print("Add Telegram messages with supported tickers, rerun analysis, then rerun this scanner.")
        return

    print("Real Telegram social signals were rated with real Binance market data.")
    print("Next step: run scanner_agent_export.py and scanner_agent_export_report.py.")


def main() -> None:
    print("TELEGRAM REAL MARKET SCANNER")
    print("============================")
    print("Mode: REAL TELEGRAM SOCIAL SIGNALS + REAL BINANCE MARKET DATA")
    print("Orders: disabled")
    print("Trading: disabled")
    print("Telegram reading: disabled here, this script uses saved JSON only")
    print()

    source_payload = load_real_social_payload()

    if source_payload.get("blockers"):
        output_payload = build_output_payload(
            source_payload=source_payload,
            social_signals=[],
            rated_signals=[],
            saved_ids=[],
        )
        output_payload["blockers"] = source_payload.get("blockers", [])
        output_path = save_output_payload(output_payload)
        print_market_scanner_summary(output_payload, output_path)
        return

    social_signals = extract_social_signals(source_payload)

    if not social_signals:
        output_payload = build_output_payload(
            source_payload=source_payload,
            social_signals=[],
            rated_signals=[],
            saved_ids=[],
        )
        output_payload["warnings"].append("no_social_signals_found")
        output_path = save_output_payload(output_payload)
        print_market_scanner_summary(output_payload, output_path)
        return

    now = datetime.now()
    rated_signals = build_rated_signals_from_real_social(social_signals)
    saved_ids = save_scanner_signals(rated_signals, created_at=now)
    report_path = save_markdown_report(rated_signals, now)

    output_payload = build_output_payload(
        source_payload=source_payload,
        social_signals=social_signals,
        rated_signals=rated_signals,
        saved_ids=saved_ids,
    )

    output_path = save_output_payload(output_payload)

    print_console_report(rated_signals, report_path=report_path)
    print()
    print_market_scanner_summary(output_payload, output_path)


if __name__ == "__main__":
    main()
