import json
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List

from config import WATCHLIST
from ticker_extractor import extract_tickers


PREVIEW_PATH = Path("reports") / "telegram_real_messages_preview.json"
OUTPUT_JSON_PATH = Path("reports") / "telegram_channel_quality_report.json"
OUTPUT_TXT_PATH = Path("reports") / "telegram_channel_quality_report.txt"

CRYPTO_KEYWORDS = {
    "btc",
    "bitcoin",
    "eth",
    "ethereum",
    "bnb",
    "binance",
    "sol",
    "ton",
    "usdt",
    "usdc",
    "crypto",
    "altcoin",
    "market",
    "trading",
    "futures",
    "spot",
    "token",
    "blockchain",
    "airdrop",
    "volume",
    "retest",
    "confirmation",
}


def load_json_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {
            "ok": False,
            "error": f"File not found: {path}",
            "data": {},
        }

    try:
        return {
            "ok": True,
            "error": None,
            "data": json.loads(path.read_text(encoding="utf-8")),
        }
    except json.JSONDecodeError as ex:
        return {
            "ok": False,
            "error": f"Invalid JSON: {ex}",
            "data": {},
        }
    except OSError as ex:
        return {
            "ok": False,
            "error": f"Cannot read file: {ex}",
            "data": {},
        }


def parse_datetime_safe(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value

    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    return None


def select_analysis_now(messages: List[Dict[str, Any]]) -> datetime:
    parsed_dates = []

    for message in messages:
        created_at = parse_datetime_safe(message.get("created_at"))

        if created_at is not None:
            parsed_dates.append(created_at)

    if parsed_dates:
        return max(parsed_dates)

    return datetime.now()


def count_keyword_hits(text: str) -> int:
    lowered = str(text or "").lower()
    return sum(1 for keyword in CRYPTO_KEYWORDS if keyword in lowered)


def group_messages_by_channel(messages: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}

    for message in messages:
        channel = str(message.get("channel", "unknown")).strip() or "unknown"
        grouped.setdefault(channel, []).append(message)

    return grouped


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def calculate_channel_quality(
    channel: str,
    messages: List[Dict[str, Any]],
    analysis_now: datetime,
) -> Dict[str, Any]:
    message_count = len(messages)

    channel_title = ""
    channel_weight = 1.0
    authority_score = 50

    unique_tickers = set()
    ticker_hits: Dict[str, int] = {}
    keyword_hits = 0
    total_views = []
    total_forwards = []
    fresh_6h = 0
    fresh_24h = 0
    stale_over_24h = 0

    sample_messages = []

    for message in messages:
        channel_title = str(message.get("channel_title") or channel_title or channel)
        channel_weight = safe_float(message.get("channel_weight", channel_weight), channel_weight)
        authority_score = safe_int(message.get("authority_score", authority_score), authority_score)

        text = str(message.get("text", "")).strip()
        keyword_hits += count_keyword_hits(text)

        for ticker in extract_tickers(text, WATCHLIST):
            unique_tickers.add(ticker)
            ticker_hits[ticker] = ticker_hits.get(ticker, 0) + 1

        views = message.get("views")
        forwards = message.get("forwards")

        if views is not None:
            total_views.append(safe_int(views))

        if forwards is not None:
            total_forwards.append(safe_int(forwards))

        created_at = parse_datetime_safe(message.get("created_at"))

        if created_at is not None:
            age_hours = max(0.0, (analysis_now - created_at).total_seconds() / 3600)

            if age_hours <= 6:
                fresh_6h += 1

            if age_hours <= 24:
                fresh_24h += 1
            else:
                stale_over_24h += 1

        if len(sample_messages) < 3 and text:
            sample_messages.append({
                "created_at": message.get("created_at"),
                "text_preview": message.get("text_preview") or text[:300],
            })

    avg_views = round(mean(total_views), 2) if total_views else 0.0
    avg_forwards = round(mean(total_forwards), 2) if total_forwards else 0.0

    score = 0
    reasons: List[str] = []
    warnings: List[str] = []

    if message_count > 0:
        score += min(20, message_count * 4)
        reasons.append("has_messages")
    else:
        warnings.append("no_messages")

    if fresh_24h > 0:
        score += min(20, fresh_24h * 5)
        reasons.append("has_fresh_24h_messages")
    else:
        warnings.append("no_fresh_24h_messages")

    if unique_tickers:
        score += min(25, len(unique_tickers) * 7)
        reasons.append("has_watchlist_tickers")
    else:
        warnings.append("no_watchlist_tickers")

    if keyword_hits > 0:
        score += min(15, keyword_hits * 2)
        reasons.append("has_crypto_keywords")
    else:
        warnings.append("no_crypto_keywords")

    if authority_score >= 80:
        score += 10
        reasons.append("high_authority")
    elif authority_score >= 60:
        score += 6
        reasons.append("medium_authority")

    if channel_weight >= 1.3:
        score += 5
        reasons.append("high_channel_weight")
    elif channel_weight >= 1.0:
        score += 3
        reasons.append("normal_channel_weight")

    if stale_over_24h > 0 and fresh_24h == 0:
        score -= 15
        warnings.append("mostly_stale_messages")

    score = max(0, min(100, score))

    if score >= 70:
        recommendation = "keep"
    elif score >= 45:
        recommendation = "watch"
    else:
        recommendation = "disable"

    return {
        "channel": channel,
        "channel_title": channel_title or channel,
        "recommendation": recommendation,
        "quality_score": score,
        "messages": message_count,
        "fresh_messages_6h": fresh_6h,
        "fresh_messages_24h": fresh_24h,
        "stale_messages_over_24h": stale_over_24h,
        "unique_tickers": sorted(unique_tickers),
        "ticker_hits": dict(sorted(ticker_hits.items())),
        "keyword_hits": keyword_hits,
        "avg_views": avg_views,
        "avg_forwards": avg_forwards,
        "channel_weight": channel_weight,
        "authority_score": authority_score,
        "reasons": reasons,
        "warnings": warnings,
        "sample_messages": sample_messages,
    }


def build_not_ready_payload(error: str) -> Dict[str, Any]:
    return {
        "source": "telegram_channel_quality_report",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analytical_only": True,
        "orders_enabled": False,
        "trading_enabled": False,
        "telegram_messages_read": False,
        "safe_to_continue": False,
        "input_file": str(PREVIEW_PATH),
        "output_json": str(OUTPUT_JSON_PATH),
        "output_txt": str(OUTPUT_TXT_PATH),
        "channels_analyzed": 0,
        "channels_keep": 0,
        "channels_watch": 0,
        "channels_disable": 0,
        "channels": [],
        "blockers": ["preview_file_not_ready"],
        "warnings": [],
        "error": error,
        "disclaimer": (
            "This report is analytical only. It does not read Telegram, "
            "does not call Binance API, does not create orders, and does not start trading."
        ),
    }


def build_quality_payload() -> Dict[str, Any]:
    loaded = load_json_file(PREVIEW_PATH)

    if not loaded["ok"]:
        return build_not_ready_payload(str(loaded["error"]))

    preview_payload = loaded["data"]

    if not preview_payload.get("safe_to_continue"):
        return build_not_ready_payload("Preview payload is not safe to continue.")

    messages = preview_payload.get("messages", [])

    if not isinstance(messages, list):
        messages = []

    analysis_now = select_analysis_now(messages)
    grouped = group_messages_by_channel(messages)

    channels = [
        calculate_channel_quality(
            channel=channel,
            messages=channel_messages,
            analysis_now=analysis_now,
        )
        for channel, channel_messages in grouped.items()
    ]

    channels = sorted(
        channels,
        key=lambda item: int(item.get("quality_score", 0)),
        reverse=True,
    )

    channels_keep = sum(1 for item in channels if item.get("recommendation") == "keep")
    channels_watch = sum(1 for item in channels if item.get("recommendation") == "watch")
    channels_disable = sum(1 for item in channels if item.get("recommendation") == "disable")

    return {
        "source": "telegram_channel_quality_report",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "analysis_now": analysis_now.isoformat(timespec="seconds"),
        "analytical_only": True,
        "orders_enabled": False,
        "trading_enabled": False,
        "telegram_messages_read": False,
        "safe_to_continue": True,
        "input_file": str(PREVIEW_PATH),
        "output_json": str(OUTPUT_JSON_PATH),
        "output_txt": str(OUTPUT_TXT_PATH),
        "preview_created_at": preview_payload.get("created_at"),
        "preview_messages_collected": preview_payload.get("messages_collected"),
        "preview_channels_requested": preview_payload.get("channels_requested"),
        "preview_channels_ok": preview_payload.get("channels_ok"),
        "preview_skipped_old_messages": preview_payload.get("skipped_old_messages"),
        "preview_skipped_empty_messages": preview_payload.get("skipped_empty_messages"),
        "channels_analyzed": len(channels),
        "channels_keep": channels_keep,
        "channels_watch": channels_watch,
        "channels_disable": channels_disable,
        "channels": channels,
        "blockers": [],
        "warnings": preview_payload.get("warnings", []),
        "disclaimer": (
            "This report is analytical only. It does not read Telegram, "
            "does not call Binance API, does not create orders, and does not start trading."
        ),
    }


def save_json_report(payload: Dict[str, Any], path: Path = OUTPUT_JSON_PATH) -> Path:
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def build_text_report(payload: Dict[str, Any]) -> str:
    lines: List[str] = []

    lines.append("TELEGRAM CHANNEL QUALITY REPORT")
    lines.append("===============================")
    lines.append(f"Created at: {payload.get('created_at')}")
    lines.append("Mode: analytical only")
    lines.append(f"Safe to continue: {payload.get('safe_to_continue')}")
    lines.append("")
    lines.append("SUMMARY")
    lines.append("=======")
    lines.append(f"Channels analyzed: {payload.get('channels_analyzed')}")
    lines.append(f"Keep: {payload.get('channels_keep')}")
    lines.append(f"Watch: {payload.get('channels_watch')}")
    lines.append(f"Disable: {payload.get('channels_disable')}")
    lines.append(f"Preview messages collected: {payload.get('preview_messages_collected')}")
    lines.append(f"Preview skipped old messages: {payload.get('preview_skipped_old_messages')}")
    lines.append(f"Preview skipped empty messages: {payload.get('preview_skipped_empty_messages')}")
    lines.append("")

    lines.append("CHANNELS")
    lines.append("========")

    channels = payload.get("channels", [])

    if not channels:
        lines.append("No channels analyzed.")
    else:
        for item in channels:
            lines.append("")
            lines.append(f"@{item.get('channel')}")
            lines.append("-" * (len(str(item.get("channel"))) + 1))
            lines.append(f"Title: {item.get('channel_title')}")
            lines.append(f"Recommendation: {item.get('recommendation')}")
            lines.append(f"Quality score: {item.get('quality_score')}")
            lines.append(f"Messages: {item.get('messages')}")
            lines.append(f"Fresh 6h: {item.get('fresh_messages_6h')}")
            lines.append(f"Fresh 24h: {item.get('fresh_messages_24h')}")
            lines.append(f"Stale over 24h: {item.get('stale_messages_over_24h')}")
            lines.append(f"Tickers: {', '.join(item.get('unique_tickers', [])) or 'none'}")
            lines.append(f"Keyword hits: {item.get('keyword_hits')}")
            lines.append(f"Average views: {item.get('avg_views')}")
            lines.append(f"Average forwards: {item.get('avg_forwards')}")
            lines.append(f"Weight: {item.get('channel_weight')}")
            lines.append(f"Authority: {item.get('authority_score')}")

            if item.get("reasons"):
                lines.append("Reasons: " + ", ".join(str(x) for x in item.get("reasons", [])))

            if item.get("warnings"):
                lines.append("Warnings: " + ", ".join(str(x) for x in item.get("warnings", [])))

            samples = item.get("sample_messages", [])

            if samples:
                lines.append("Samples:")
                for sample in samples[:3]:
                    lines.append("- " + str(sample.get("text_preview")))

    lines.append("")
    lines.append("SAFETY")
    lines.append("======")
    lines.append("[OK] This report did not read Telegram.")
    lines.append("[OK] This report did not call Binance API.")
    lines.append("[OK] This report did not create orders.")
    lines.append("[OK] This report did not start trading bot.")
    lines.append("[OK] It only analyzed reports/telegram_real_messages_preview.json.")
    lines.append("")

    return "\n".join(lines)


def save_text_report(payload: Dict[str, Any], path: Path = OUTPUT_TXT_PATH) -> Path:
    path.parent.mkdir(exist_ok=True)
    path.write_text(build_text_report(payload), encoding="utf-8")
    return path


def print_summary(payload: Dict[str, Any], json_path: Path, txt_path: Path) -> None:
    print("TELEGRAM CHANNEL QUALITY REPORT")
    print("===============================")
    print("Mode: analytical only")
    print("Orders enabled:", payload.get("orders_enabled"))
    print("Trading enabled:", payload.get("trading_enabled"))
    print("Telegram messages read:", payload.get("telegram_messages_read"))
    print("Safe to continue:", payload.get("safe_to_continue"))
    print("JSON output:", json_path)
    print("TXT output:", txt_path)
    print()

    print("SUMMARY")
    print("=======")
    print("Channels analyzed:", payload.get("channels_analyzed"))
    print("Keep:", payload.get("channels_keep"))
    print("Watch:", payload.get("channels_watch"))
    print("Disable:", payload.get("channels_disable"))

    blockers = payload.get("blockers", [])
    warnings = payload.get("warnings", [])

    print("Blockers:", ", ".join(str(x) for x in blockers) if blockers else "none")
    print("Warnings:", ", ".join(str(x) for x in warnings) if warnings else "none")
    print()

    print("CHANNEL QUALITY")
    print("===============")

    channels = payload.get("channels", [])

    if not channels:
        print("No channels analyzed.")
    else:
        for item in channels:
            print(
                ("@" + str(item.get("channel"))).ljust(28),
                "recommendation=" + str(item.get("recommendation")),
                "score=" + str(item.get("quality_score")),
                "messages=" + str(item.get("messages")),
                "tickers=" + ",".join(item.get("unique_tickers", [])),
            )

    print()
    print("SAFETY")
    print("======")
    print("[OK] This report did not read Telegram.")
    print("[OK] This report did not call Binance API.")
    print("[OK] This report did not create orders.")
    print("[OK] This report only analyzed saved preview JSON.")


def main() -> None:
    payload = build_quality_payload()
    json_path = save_json_report(payload)
    txt_path = save_text_report(payload)
    print_summary(payload, json_path, txt_path)


if __name__ == "__main__":
    main()
