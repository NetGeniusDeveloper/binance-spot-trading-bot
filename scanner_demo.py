from datetime import datetime
from typing import Any, Dict, List

from scanner_report import print_console_report, save_markdown_report
from scanner_storage import save_scanner_signals
from signal_rating import build_demo_market_metrics, build_signal_rating
from social_signal_engine import analyze_social_signals, build_demo_messages


def build_extra_demo_social_signals() -> List[Dict[str, Any]]:
    """
    Extra demo scenarios to demonstrate all main statuses.

    These are analytical examples only.
    They do not create orders and do not approve trades.
    """
    return [
        {
            "ticker": "SOL",
            "mentions_5m": 6,
            "mentions_15m": 8,
            "mentions_1h": 10,
            "mentions_4h": 12,
            "mentions_24h": 16,
            "unique_channels": 4,
            "weighted_mentions": 8.5,
            "mention_growth_factor": 4.0,
            "social_signal": True,
            "status": "social_impulse",
            "sample_texts": [
                "SOL breakout after accumulation and volume growth",
                "Solana ecosystem update and retest confirmed",
            ],
        },
        {
            "ticker": "AVAX",
            "mentions_5m": 5,
            "mentions_15m": 7,
            "mentions_1h": 9,
            "mentions_4h": 13,
            "mentions_24h": 20,
            "unique_channels": 3,
            "weighted_mentions": 7.0,
            "mention_growth_factor": 3.5,
            "social_signal": True,
            "status": "social_impulse",
            "sample_texts": [
                "AVAX strong breakout, but price is near local high",
                "Avalanche volume spike, no retest yet",
            ],
        },
        {
            "ticker": "PUMP",
            "mentions_5m": 12,
            "mentions_15m": 20,
            "mentions_1h": 25,
            "mentions_4h": 30,
            "mentions_24h": 30,
            "unique_channels": 5,
            "weighted_mentions": 12.0,
            "mention_growth_factor": 8.0,
            "social_signal": True,
            "status": "social_impulse",
            "sample_texts": [
                "urgent buy now 100x moon guaranteed pump",
                "next PEPE insider signal group",
            ],
        },
    ]


def build_extra_demo_market_metrics() -> Dict[str, Dict[str, Any]]:
    return {
        "SOL": {
            "price_change_15m_percent": 1.4,
            "price_change_1h_percent": 3.8,
            "price_change_4h_percent": 7.5,
            "volume_24h_usdt": 120_000_000,
            "volume_change_ratio": 2.8,
            "estimated_spread_percent": 0.05,
            "distance_from_local_high_percent": 4.0,
            "has_retest": True,
        },
        "AVAX": {
            "price_change_15m_percent": 4.0,
            "price_change_1h_percent": 10.5,
            "price_change_4h_percent": 22.0,
            "volume_24h_usdt": 45_000_000,
            "volume_change_ratio": 3.2,
            "estimated_spread_percent": 0.08,
            "distance_from_local_high_percent": 0.8,
            "has_retest": False,
        },
        "PUMP": {
            "price_change_15m_percent": 20.0,
            "price_change_1h_percent": 45.0,
            "price_change_4h_percent": 80.0,
            "volume_24h_usdt": 400_000,
            "volume_change_ratio": 10.0,
            "estimated_spread_percent": 0.9,
            "distance_from_local_high_percent": 0.1,
            "has_retest": False,
        },
    }


def build_demo_rated_signals(now: datetime) -> List[Dict[str, Any]]:
    demo_messages = build_demo_messages(now)
    social_results = analyze_social_signals(demo_messages, now=now)
    social_results.extend(build_extra_demo_social_signals())

    market_metrics = build_demo_market_metrics()
    market_metrics.update(build_extra_demo_market_metrics())

    rated_signals: List[Dict[str, Any]] = []

    for social_signal in social_results:
        ticker = social_signal["ticker"]
        metrics = market_metrics.get(ticker, {})

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
    now = datetime.now()
    rated_signals = build_demo_rated_signals(now)

    saved_ids = save_scanner_signals(rated_signals, created_at=now)
    report_path = save_markdown_report(rated_signals, now)

    print_console_report(rated_signals, report_path=report_path)
    print()
    print("Scanner signals saved to SQLite:", len(saved_ids))


if __name__ == "__main__":
    main()
