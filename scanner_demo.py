from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from signal_rating import (
    build_demo_market_metrics,
    build_signal_rating,
    export_signal_for_agent,
)


REPORTS_DIR = Path("reports")
REPORT_PATH = REPORTS_DIR / "social_scanner_demo_report.md"

from social_signal_engine import (
    analyze_social_signals,
    build_demo_messages,
)


def build_extra_demo_social_signals() -> List[Dict[str, Any]]:
    """
    Extra scenarios to demonstrate all main statuses.

    These are demo-only analytical examples.
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


def format_agent_export(signal: Dict[str, Any]) -> str:
    agent_export = export_signal_for_agent(signal)
    lines = ["```python"]

    for key, value in agent_export.items():
        lines.append(f"{key}: {value}")

    lines.append("```")
    return "\n".join(lines)


def build_markdown_report(signals: List[Dict[str, Any]], created_at: datetime) -> str:
    lines = [
        "# Crypto Social Scanner Demo Report",
        "",
        f"Дата запуска: `{created_at.isoformat(timespec='seconds')}`",
        "",
        "Режим: **DEMO / ANALYTICAL ONLY**",
        "",
        "- Telegram API: отключён",
        "- Реальная торговля: отключена",
        "- Ордера: не создаются",
        "- Назначение: аналитический social/market scanner",
        "",
        "## Summary",
        "",
        "| Pair | Status | Telegram Score | Market Score | Final Score | Risk Flags |",
        "|---|---:|---:|---:|---:|---|",
    ]

    for signal in signals:
        risk_flags = ", ".join(signal["risk_flags"]) or "none"
        lines.append(
            f"| {signal['pair']} | {signal['status']} | "
            f"{signal['telegram_score']} | {signal['market_score']} | "
            f"{signal['final_score']} | {risk_flags} |"
        )

    lines.extend([
        "",
        "## Full Signal Cards",
        "",
    ])

    for signal in signals:
        social = signal["social_signal"]
        market = signal["market_metrics"]
        risk_flags = ", ".join(signal["risk_flags"]) or "none"

        lines.extend([
            f"### {signal['pair']}",
            "",
            f"**Статус:** {signal['status']}",
            "",
            f"- Telegram Score: `{signal['telegram_score']}`",
            f"- Market Score: `{signal['market_score']}`",
            f"- Risk Adjustment: `{signal['risk_adjustment']}`",
            f"- Final Score: `{signal['final_score']}`",
            f"- Risk Flags: `{risk_flags}`",
            "",
            "#### Telegram",
            "",
            f"- mentions_15m: `{social.get('mentions_15m')}`",
            f"- mention_growth: `{social.get('mention_growth_factor')}`",
            f"- unique_channels: `{social.get('unique_channels')}`",
            f"- weighted_mentions: `{social.get('weighted_mentions')}`",
            "",
            "#### Market",
            "",
            f"- price_change_15m_percent: `{market.get('price_change_15m_percent')}`",
            f"- price_change_1h_percent: `{market.get('price_change_1h_percent')}`",
            f"- price_change_4h_percent: `{market.get('price_change_4h_percent')}`",
            f"- volume_24h_usdt: `{market.get('volume_24h_usdt')}`",
            f"- volume_change_ratio: `{market.get('volume_change_ratio')}`",
            f"- spread_percent: `{market.get('estimated_spread_percent')}`",
            f"- distance_from_high_percent: `{market.get('distance_from_local_high_percent')}`",
            f"- has_retest: `{market.get('has_retest')}`",
            "",
            "#### Agent Export",
            "",
            format_agent_export(signal),
            "",
        ])

    lines.extend([
        "## Disclaimer",
        "",
        "Telegram/social signal is not a trading entry.",
        "",
        "This scanner is analytical only. No orders are created.",
        "",
        "Crypto assets are high-risk. Final decision is always user's responsibility.",
        "",
    ])

    return "\n".join(lines)


def save_markdown_report(signals: List[Dict[str, Any]], created_at: datetime) -> Path:
    REPORTS_DIR.mkdir(exist_ok=True)
    report_text = build_markdown_report(signals, created_at)
    REPORT_PATH.write_text(report_text, encoding="utf-8")
    return REPORT_PATH


def print_header() -> None:
    print("CRYPTO SOCIAL SCANNER DEMO")
    print("==========================")
    print("Mode: DEMO / ANALYTICAL ONLY")
    print("Orders: disabled")
    print("Telegram API: disabled")
    print("Real exchange trading: disabled")
    print()


def print_signal(signal: Dict[str, Any]) -> None:
    social = signal["social_signal"]
    market = signal["market_metrics"]
    agent_export = export_signal_for_agent(signal)

    print("-" * 70)
    print("Монета:", signal["pair"])
    print("Статус:", signal["status"])
    print("Telegram Score:", signal["telegram_score"])
    print("Market Score:", signal["market_score"])
    print("Risk Adjustment:", signal["risk_adjustment"])
    print("Final Score:", signal["final_score"])
    print("Risk Flags:", ", ".join(signal["risk_flags"]) or "none")
    print()
    print("Telegram:")
    print("  mentions_15m:", social.get("mentions_15m"))
    print("  mention_growth:", social.get("mention_growth_factor"))
    print("  unique_channels:", social.get("unique_channels"))
    print("  weighted_mentions:", social.get("weighted_mentions"))
    print()
    print("Market:")
    print("  price_change_15m_percent:", market.get("price_change_15m_percent"))
    print("  price_change_1h_percent:", market.get("price_change_1h_percent"))
    print("  price_change_4h_percent:", market.get("price_change_4h_percent"))
    print("  volume_24h_usdt:", market.get("volume_24h_usdt"))
    print("  volume_change_ratio:", market.get("volume_change_ratio"))
    print("  spread_percent:", market.get("estimated_spread_percent"))
    print("  distance_from_high_percent:", market.get("distance_from_local_high_percent"))
    print("  has_retest:", market.get("has_retest"))
    print()
    print("Agent export:")
    print(agent_export)


def print_summary(signals: List[Dict[str, Any]]) -> None:
    print()
    print("SUMMARY")
    print("=======")

    if not signals:
        print("No signals.")
        return

    header = (
        "Pair".ljust(10)
        + "Status".ljust(20)
        + "Telegram".rjust(10)
        + "Market".rjust(10)
        + "Final".rjust(10)
        + "Risks".rjust(25)
    )

    print(header)
    print("-" * len(header))

    for signal in signals:
        row = (
            str(signal["pair"]).ljust(10)
            + str(signal["status"]).ljust(20)
            + str(signal["telegram_score"]).rjust(10)
            + str(signal["market_score"]).rjust(10)
            + str(signal["final_score"]).rjust(10)
            + (", ".join(signal["risk_flags"]) or "none").rjust(25)
        )
        print(row)


def main() -> None:
    print_header()

    now = datetime.now()

    demo_messages = build_demo_messages(now)
    social_results = analyze_social_signals(demo_messages, now=now)

    extra_social = build_extra_demo_social_signals()
    social_results.extend(extra_social)

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

    for signal in rated_signals:
        print_signal(signal)

    print_summary(rated_signals)

    report_path = save_markdown_report(rated_signals, now)
    print()
    print("Markdown report saved:", report_path)

    print()
    print("DISCLAIMER")
    print("==========")
    print("Telegram/social signal is not a trading entry.")
    print("This scanner is analytical only.")
    print("No orders are created.")
    print("Crypto assets are high-risk. Final decision is always user's responsibility.")


if __name__ == "__main__":
    main()
