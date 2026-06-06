from datetime import datetime
from typing import Any, Dict, List

from scanner_demo import build_extra_demo_social_signals
from scanner_market_data import get_market_metrics_for_watchlist
from scanner_report import print_console_report, save_markdown_report
from scanner_storage import save_scanner_signals
from signal_rating import build_signal_rating
from social_signal_engine import analyze_social_signals
from telegram_social_collector import (
    build_demo_collector_messages,
    collect_public_channel_messages_sync,
    get_collector_status,
)


REAL_TELEGRAM_LIMIT_PER_CHANNEL = 50


def load_social_messages(now: datetime) -> List[Dict[str, Any]]:
    """
    Load social messages for scanner.

    Safe behavior:
    - if Telegram Client API is not ready, use demo messages;
    - if Telegram Client API is ready but real channels are not configured, use demo messages;
    - if real public channels are configured, collect real public Telegram messages;
    - never creates orders;
    - never enables trading.
    """
    status = get_collector_status()

    if not status.get("ready"):
        print("Telegram collector mode: DEMO")
        print("Reason:", ", ".join(status.get("reasons", [])) or "collector_not_ready")
        print("Using demo Telegram/social messages.")
        print()
        return build_demo_collector_messages(now)

    if int(status.get("real_channels_count", 0)) <= 0:
        print("Telegram collector mode: DEMO")
        print("Reason: no real Telegram channels configured.")
        print("Using demo Telegram/social messages.")
        print()
        return build_demo_collector_messages(now)

    print("Telegram collector mode: REAL PUBLIC CHANNELS")
    print("Enabled real channels:", status.get("real_channels_count"))
    print("Limit per channel:", REAL_TELEGRAM_LIMIT_PER_CHANNEL)
    print("[SAFE] Collector is analytical only. Orders are disabled.")
    print()

    real_messages = collect_public_channel_messages_sync(
        limit_per_channel=REAL_TELEGRAM_LIMIT_PER_CHANNEL,
    )

    if not real_messages:
        print("[SAFE] No real Telegram messages collected.")
        print("[SAFE] Falling back to demo Telegram/social messages.")
        print()
        return build_demo_collector_messages(now)

    print("Collected real Telegram messages:", len(real_messages))
    print()

    return real_messages


def build_social_signals(now: datetime) -> List[Dict[str, Any]]:
    """
    Build Telegram/social signals from either demo or real collector messages.

    Extra demo scenarios are still added to keep anti-pump and edge-case tests visible.
    """
    raw_messages = load_social_messages(now)

    social_results = analyze_social_signals(
        raw_messages=raw_messages,
        now=now,
    )

    # Keep these controlled scenarios for regression testing:
    # - SOL: strong but safe social impulse;
    # - AVAX: late/no retest scenario;
    # - PUMP: fake dangerous pump scenario.
    social_results.extend(build_extra_demo_social_signals())

    return social_results


def filter_market_symbols(social_signals: List[Dict[str, Any]]) -> List[str]:
    """
    Request Binance market data only for tickers found in social signals.

    PUMP is intentionally skipped because it is a fake demo-only symbol.
    """
    symbols: List[str] = []

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
    social_signals = build_social_signals(now)
    market_symbols = filter_market_symbols(social_signals)

    if market_symbols:
        print("Loading real Binance market metrics for:", ", ".join(market_symbols))
    else:
        print("No market symbols found from social signals.")

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
    print("Mode: TELEGRAM SOCIAL + REAL BINANCE MARKET DATA")
    print("Orders: disabled")
    print("Real exchange trading: disabled")
    print("Telegram collector: safe analytical mode")
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
    print("This mode uses safe Telegram/social collector messages.")
    print("If real Telegram credentials and real public channels are not configured, demo messages are used.")
    print("It combines social signals with real Binance market metrics.")
    print("It is analytical only and does not create orders.")


if __name__ == "__main__":
    main()
