from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List

from config import WATCHLIST
from ticker_extractor import extract_tickers


DEFAULT_SOCIAL_FILTERS = {
    "min_mentions_15m": 3,
    "mention_growth_factor": 2.0,
    "min_unique_channels": 2,
}


WINDOWS = {
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
    "24h": timedelta(hours=24),
}


def parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        return datetime.fromisoformat(value)

    raise ValueError("Unsupported datetime value: " + str(value))


def normalize_message(raw_message: Dict[str, Any]) -> Dict[str, Any]:
    created_at = parse_datetime(raw_message["created_at"])
    text = str(raw_message.get("text", ""))
    channel = str(raw_message.get("channel", "unknown"))
    channel_weight = float(raw_message.get("channel_weight", 1.0))

    tickers = raw_message.get("tickers")

    if tickers is None:
        tickers = extract_tickers(text, WATCHLIST)

    return {
        "channel": channel,
        "text": text,
        "created_at": created_at,
        "channel_weight": channel_weight,
        "tickers": list(tickers),
    }


def filter_messages_by_window(
    messages: Iterable[Dict[str, Any]],
    ticker: str,
    now: datetime,
    window: timedelta,
) -> List[Dict[str, Any]]:
    result = []
    since = now - window

    for message in messages:
        if message["created_at"] < since:
            continue

        if ticker not in message["tickers"]:
            continue

        result.append(message)

    return result


def count_mentions(
    messages: Iterable[Dict[str, Any]],
    ticker: str,
    now: datetime,
    window: timedelta,
) -> int:
    return len(filter_messages_by_window(messages, ticker, now, window))


def count_unique_channels(messages: Iterable[Dict[str, Any]]) -> int:
    return len({message["channel"] for message in messages})


def calculate_weighted_mentions(messages: Iterable[Dict[str, Any]]) -> float:
    total = 0.0

    for message in messages:
        total += float(message.get("channel_weight", 1.0))

    return round(total, 2)


def calculate_mention_growth_factor(
    messages: Iterable[Dict[str, Any]],
    ticker: str,
    now: datetime,
) -> float:
    current_since = now - timedelta(minutes=15)
    previous_since = now - timedelta(minutes=60)

    current_count = 0
    previous_count = 0

    for message in messages:
        if ticker not in message["tickers"]:
            continue

        created_at = message["created_at"]

        if created_at >= current_since:
            current_count += 1
        elif previous_since <= created_at < current_since:
            previous_count += 1

    if current_count == 0:
        return 0.0

    if previous_count == 0:
        return float(current_count)

    return round(current_count / previous_count, 2)


def analyze_social_signals(
    raw_messages: List[Dict[str, Any]],
    filters: Dict[str, Any] | None = None,
    now: datetime | None = None,
) -> List[Dict[str, Any]]:
    """
    Analyze social mentions for tickers from WATCHLIST.

    This is an analytical layer only.
    It does not create trade orders and does not approve entries.
    """
    if filters is None:
        filters = DEFAULT_SOCIAL_FILTERS

    if now is None:
        now = datetime.now()

    messages = [normalize_message(message) for message in raw_messages]

    discovered_tickers = sorted({
        ticker
        for message in messages
        for ticker in message["tickers"]
    })

    results = []

    for ticker in discovered_tickers:
        messages_5m = filter_messages_by_window(messages, ticker, now, WINDOWS["5m"])
        messages_15m = filter_messages_by_window(messages, ticker, now, WINDOWS["15m"])
        messages_1h = filter_messages_by_window(messages, ticker, now, WINDOWS["1h"])
        messages_4h = filter_messages_by_window(messages, ticker, now, WINDOWS["4h"])
        messages_24h = filter_messages_by_window(messages, ticker, now, WINDOWS["24h"])

        mentions_5m = len(messages_5m)
        mentions_15m = len(messages_15m)
        mentions_1h = len(messages_1h)
        mentions_4h = len(messages_4h)
        mentions_24h = len(messages_24h)

        unique_channels = count_unique_channels(messages_15m)
        weighted_mentions = calculate_weighted_mentions(messages_15m)
        mention_growth_factor = calculate_mention_growth_factor(messages, ticker, now)

        social_signal = (
            mentions_15m >= int(filters["min_mentions_15m"])
            and mention_growth_factor >= float(filters["mention_growth_factor"])
            and unique_channels >= int(filters["min_unique_channels"])
        )

        results.append({
            "ticker": ticker,
            "mentions_5m": mentions_5m,
            "mentions_15m": mentions_15m,
            "mentions_1h": mentions_1h,
            "mentions_4h": mentions_4h,
            "mentions_24h": mentions_24h,
            "unique_channels": unique_channels,
            "weighted_mentions": weighted_mentions,
            "mention_growth_factor": mention_growth_factor,
            "social_signal": social_signal,
            "status": "social_impulse" if social_signal else "watch_only",
        })

    return results


def build_demo_messages(now: datetime) -> List[Dict[str, Any]]:
    return [
        {
            "channel": "crypto_news_alpha",
            "text": "$TON volume is rising after ecosystem update",
            "created_at": now - timedelta(minutes=3),
            "channel_weight": 1.5,
        },
        {
            "channel": "market_watch",
            "text": "TON/USDT showing strong mentions today",
            "created_at": now - timedelta(minutes=7),
            "channel_weight": 1.2,
        },
        {
            "channel": "trading_notes",
            "text": "#TON breakout discussion is growing",
            "created_at": now - timedelta(minutes=12),
            "channel_weight": 1.1,
        },
        {
            "channel": "old_news",
            "text": "Toncoin was quiet earlier",
            "created_at": now - timedelta(minutes=45),
            "channel_weight": 1.0,
        },
        {
            "channel": "crypto_news_alpha",
            "text": "Bitcoin and Ethereum are still under pressure",
            "created_at": now - timedelta(minutes=10),
            "channel_weight": 1.5,
        },
        {
            "channel": "low_quality_pump",
            "text": "urgent 100x moon guaranteed buy now",
            "created_at": now - timedelta(minutes=5),
            "channel_weight": 0.2,
        },
        {
            "channel": "altcoin_watch",
            "text": "LINKUSDT volume is rising slowly",
            "created_at": now - timedelta(hours=2),
            "channel_weight": 1.0,
        },
    ]


def print_social_report(results: List[Dict[str, Any]]) -> None:
    print("SOCIAL SIGNAL REPORT")
    print("====================")

    if not results:
        print("No social signals found.")
        return

    for item in results:
        print()
        print("Ticker:", item["ticker"])
        print("Status:", item["status"])
        print("Mentions 5m:", item["mentions_5m"])
        print("Mentions 15m:", item["mentions_15m"])
        print("Mentions 1h:", item["mentions_1h"])
        print("Mentions 4h:", item["mentions_4h"])
        print("Mentions 24h:", item["mentions_24h"])
        print("Unique channels:", item["unique_channels"])
        print("Weighted mentions:", item["weighted_mentions"])
        print("Mention growth factor:", item["mention_growth_factor"])
        print("Social signal:", item["social_signal"])


if __name__ == "__main__":
    current_time = datetime.now()
    demo_messages = build_demo_messages(current_time)

    social_results = analyze_social_signals(
        raw_messages=demo_messages,
        now=current_time,
    )

    print_social_report(social_results)
