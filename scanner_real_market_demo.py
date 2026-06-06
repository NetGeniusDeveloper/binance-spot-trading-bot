from datetime import datetime
from typing import Any, Dict, List

from scanner_demo import build_extra_demo_social_signals
from scanner_market_data import get_market_metrics_for_watchlist
from scanner_report import print_console_report, save_markdown_report
from scanner_storage import save_scanner_signals
from signal_rating import build_signal_rating
from social_signal_engine import analyze_social_signals
from telegram_social_collector import build_demo_collector_messages


def build_demo_social_signals(now: datetime) -> List[Dict[str, Any]]:
    """
    Build demo Telegram/social signals.

    Demo messages come from telegram_social_collector.py.
    This function does not use real Telegram API.
    It creates analytical demo social signals only.
    """
    demo_messages = build_demo_collector_messages(now)
    social_results = analyze_social_signals(demo_messages, now=now)
    social_results.extend(build_extra_demo_social_signals())

    return social_results


def filter_market_symbols(social_signals: List[Dict[str, Any]]) -> List[str]:
    """
    Request Binance market data only for tickers found in demo social signals.

    PUMP is intentionally skipped because it is a fake demo-only symbol.
    """
    symbols = []

    for signal in social_signals:
        ticker = str(signal.get("ticker", "")).upper()

        if not ticker:
            continue

        if ticker == "PUMP":
            continue

        if ticker not in symbols:
            symbols.append(ticker)

    return symbols


def build_demo_pump_market_metrics() -> Dict[str, Any]:
    """
    Build artificial market metrics for the dangerous-pump demo scenario.

    This fake symbol is used only to test anti-pump classification.
    It is not requested from Binance and must never be treated as a tradable pair.
    """
    return {
        "symbol": "PUMP",
        "pair": "PUMPUSDT",
        "price_change_15m_percent": 20.0,
        "price_change_1h_percent": 45.0,
        "price_change_4h_percent": 80.0,
        "volume_24h_usdt": 400_000,
        "volume_change_ratio": 10.0,
        "estimated_spread_percent": 0.9,
        "distance_from_local_high_percent": 0.1,
        "has_retest": False,
        "demo_only": True,
    }


def build_real_market_rated_signals(now: datetime) -> List[Dict[str, Any]]:
    social_signals = build_demo_social_signals(now)
    market_symbols = filter_market_symbols(social_signals)

    print("Loading real Binance market metrics for:", ", ".join(market_symbols))
    print()

    market_metrics_by_symbol = get_market_metrics_for_watchlist(
        symbols=market_symbols,
        quote="USDT",
        interval="1m",
        limit=240,
    )

    rated_signals: List[Dict[str, Any]] = []

    for social_signal in social_signals:
        ticker = str(social_signal.get("ticker", "")).upper()

        if ticker == "PUMP":
            metrics = build_demo_pump_market_metrics()
        else:
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
            item["status"] == "движение возможно",
            item["final_score"],
        ),
        reverse=True,
    )

    return rated_signals


def main() -> None:
    print("CRYPTO SOCIAL SCANNER REAL MARKET DEMO")
    print("======================================")
    print("Mode: DEMO SOCIAL + REAL BINANCE MARKET DATA")
    print("Orders: disabled")
    print("Telegram API: disabled")
    print("Real exchange trading: disabled")
    print()

    now = datetime.now()
    rated_signals = build_real_market_rated_signals(now)

    saved_ids = save_scanner_signals(rated_signals, created_at=now)
    report_path = save_markdown_report(rated_signals, now)

    print_console_report(rated_signals, report_path=report_path)
    print()
    print("Scanner signals saved to SQLite:", len(saved_ids))
    print()
    print("NOTE")
    print("====")
    print("This mode uses demo social signals from telegram_social_collector.py.")
    print("It combines them with real Binance market metrics.")
    print("It is still analytical only and does not create orders.")


if __name__ == "__main__":
    main()
