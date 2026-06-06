from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from signal_rating import export_signal_for_agent


REPORTS_DIR = Path("reports")
REPORT_PATH = REPORTS_DIR / "social_scanner_demo_report.md"


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
        risk_text = ", ".join(signal["risk_flags"]) or "none"

        row = (
            str(signal["pair"]).ljust(10)
            + str(signal["status"]).ljust(20)
            + str(signal["telegram_score"]).rjust(10)
            + str(signal["market_score"]).rjust(10)
            + str(signal["final_score"]).rjust(10)
            + " "
            + risk_text
        )

        print(row)


def print_disclaimer() -> None:
    print()
    print("DISCLAIMER")
    print("==========")
    print("Telegram/social signal is not a trading entry.")
    print("This scanner is analytical only.")
    print("No orders are created.")
    print("Crypto assets are high-risk. Final decision is always user's responsibility.")


def print_console_report(signals: List[Dict[str, Any]], report_path: Path | None = None) -> None:
    print_header()

    for signal in signals:
        print_signal(signal)

    print_summary(signals)

    if report_path is not None:
        print()
        print("Markdown report saved:", report_path)

    print_disclaimer()


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
