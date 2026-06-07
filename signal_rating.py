from typing import Any, Dict, List


POSITIVE_KEYWORDS = {
    "listing",
    "listed",
    "partnership",
    "mainnet",
    "upgrade",
    "burn",
    "etf",
    "integration",
    "binance",
    "coinbase",
    "okx",
    "bybit",
    "kucoin",
    "launch",
    "breakout",
    "accumulation",
    "volume",
    "retest",
    "confirmation",
    "support",
    "trend",
    "growth",
    "liquidity",
    "spot",
    "news",
    "update",
    "ecosystem",
    "funding",
    "approval",
    "запуск",
    "листинг",
    "обновление",
    "партнерство",
    "ретест",
    "объем",
    "подтверждение",
}

DANGER_KEYWORDS = {
    "pump",
    "100x",
    "guaranteed",
    "moon",
    "urgent buy",
    "insider",
    "signal group",
    "low cap gem",
    "next pepe",
    "ape now",
    "buy now",
    "no risk",
    "free money",
    "gem call",
    "alpha group",
    "иксы",
    "ракета",
    "срочно",
    "инсайд",
    "гарантия",
    "памп",
    "залетай",
    "без риска",
    "сигнал",
    "туземун",
}

RETEST_KEYWORDS = {
    "retest",
    "pullback",
    "confirmation",
    "support",
    "confirmed",
    "wait",
    "подтверждение",
    "ретест",
    "откат",
    "поддержка",
    "ждать",
}

NEGATIVE_KEYWORDS = {
    "hack",
    "exploit",
    "lawsuit",
    "delist",
    "delisting",
    "ban",
    "sec",
    "investigation",
    "rug",
    "scam",
    "dump",
    "взлом",
    "скам",
    "делистинг",
    "бан",
    "расследование",
    "дамп",
}


def clamp_score(value: float) -> float:
    return round(max(0.0, min(100.0, float(value))), 2)


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


def count_keywords(text: str, keywords: set[str]) -> int:
    normalized = str(text or "").lower()
    count = 0

    for keyword in keywords:
        if keyword.lower() in normalized:
            count += 1

    return count


def join_sample_texts(social_signal: Dict[str, Any]) -> str:
    texts = social_signal.get("sample_texts", [])

    if not isinstance(texts, list):
        texts = []

    return " ".join(str(item) for item in texts)


def calculate_telegram_score(social_signal: Dict[str, Any]) -> float:
    """
    Calculate Telegram/social signal score from 0 to 100.

    This score is analytical only.
    It is not a trading entry and does not allow order execution.
    """
    mentions_15m = safe_int(social_signal.get("mentions_15m", 0))
    unique_channels = safe_int(social_signal.get("unique_channels", 0))
    weighted_mentions = safe_float(social_signal.get("weighted_mentions", 0.0))
    mention_growth_factor = safe_float(social_signal.get("mention_growth_factor", 0.0))
    social_signal_enabled = bool(social_signal.get("social_signal", False))

    joined_text = join_sample_texts(social_signal)

    positive_keyword_count = count_keywords(joined_text, POSITIVE_KEYWORDS)
    danger_keyword_count = count_keywords(joined_text, DANGER_KEYWORDS)
    negative_keyword_count = count_keywords(joined_text, NEGATIVE_KEYWORDS)
    retest_keyword_count = count_keywords(joined_text, RETEST_KEYWORDS)

    score = 0.0

    score += min(22.0, mentions_15m * 5.5)
    score += min(18.0, unique_channels * 6.0)
    score += min(18.0, mention_growth_factor * 5.0)
    score += min(14.0, weighted_mentions * 2.5)

    if social_signal_enabled:
        score += 12.0

    score += min(10.0, positive_keyword_count * 2.0)
    score += min(6.0, retest_keyword_count * 2.0)

    score -= min(28.0, danger_keyword_count * 7.0)
    score -= min(18.0, negative_keyword_count * 6.0)

    if unique_channels <= 1 and mentions_15m <= 2:
        score -= 8.0

    if mention_growth_factor >= 6.0 and unique_channels <= 1:
        score -= 10.0

    classification_summary = social_signal.get("message_classification_summary", {})

    if isinstance(classification_summary, dict):
        message_adjustment = safe_float(classification_summary.get("score_adjustment", 0.0))
        score += max(-40.0, min(25.0, message_adjustment))

        primary_intent = str(classification_summary.get("primary_intent", ""))

        if primary_intent == "possible_news":
            score += 5.0

        if primary_intent == "watch_signal":
            score += 3.0

        if primary_intent == "pump_fomo":
            score -= 18.0

    return clamp_score(score)


def calculate_market_score(metrics: Dict[str, Any]) -> float:
    """
    Calculate market score from 0 to 100 using simplified market metrics.

    This is only analytical market confirmation.
    It does not create signals for automatic entry.
    """
    price_change_5m = safe_float(metrics.get("price_change_5m_percent", 0.0))
    price_change_15m = safe_float(metrics.get("price_change_15m_percent", 0.0))
    price_change_1h = safe_float(metrics.get("price_change_1h_percent", 0.0))
    price_change_4h = safe_float(metrics.get("price_change_4h_percent", 0.0))
    volume_24h = safe_float(metrics.get("volume_24h_usdt", 0.0))
    volume_change_ratio = safe_float(metrics.get("volume_change_ratio", 1.0))
    spread = safe_float(metrics.get("estimated_spread_percent", 0.2))
    distance_from_high = safe_float(metrics.get("distance_from_local_high_percent", 0.0))
    has_retest = bool(metrics.get("has_retest", False))

    score = 0.0

    # Short momentum: reward controlled movement, not vertical pumps.
    if 0.2 <= price_change_5m <= 2.5:
        score += 6.0
    elif 2.5 < price_change_5m <= 5.0:
        score += 3.0
    elif price_change_5m > 5.0:
        score -= 6.0

    if 0.5 <= price_change_15m <= 4.0:
        score += 14.0
    elif 0.0 < price_change_15m < 0.5:
        score += 5.0
    elif 4.0 < price_change_15m <= 7.0:
        score += 6.0
    elif price_change_15m > 7.0:
        score -= 4.0
    elif price_change_15m < -2.0:
        score -= 8.0

    if 1.0 <= price_change_1h <= 7.0:
        score += 15.0
    elif 0.0 < price_change_1h < 1.0:
        score += 5.0
    elif 7.0 < price_change_1h <= 12.0:
        score += 6.0
    elif price_change_1h > 12.0:
        score -= 6.0
    elif price_change_1h < -3.0:
        score -= 10.0

    if -3.0 <= price_change_4h <= 12.0:
        score += 10.0
    elif 12.0 < price_change_4h <= 22.0:
        score += 4.0
    elif price_change_4h > 22.0:
        score -= 8.0
    elif price_change_4h < -8.0:
        score -= 10.0

    # Liquidity.
    if volume_24h >= 100_000_000:
        score += 20.0
    elif volume_24h >= 50_000_000:
        score += 18.0
    elif volume_24h >= 10_000_000:
        score += 13.0
    elif volume_24h >= 5_000_000:
        score += 8.0
    elif volume_24h >= 1_000_000:
        score += 3.0
    else:
        score -= 12.0

    # Volume impulse.
    if 1.3 <= volume_change_ratio <= 3.5:
        score += 10.0
    elif 3.5 < volume_change_ratio <= 6.0:
        score += 5.0
    elif volume_change_ratio > 6.0:
        score -= 6.0
    elif volume_change_ratio < 0.8:
        score -= 4.0

    # Spread.
    if spread <= 0.05:
        score += 10.0
    elif spread <= 0.15:
        score += 7.0
    elif spread <= 0.3:
        score += 2.0
    elif spread > 0.5:
        score -= 12.0
    else:
        score -= 6.0

    # Distance from local high.
    if distance_from_high >= 3.0:
        score += 9.0
    elif distance_from_high >= 1.5:
        score += 5.0
    elif distance_from_high < 0.8 and price_change_1h > 3.0:
        score -= 8.0

    if has_retest:
        score += 12.0

    return clamp_score(score)


def analyze_rating_risks(
    social_signal: Dict[str, Any],
    market_metrics: Dict[str, Any],
) -> Dict[str, Any]:
    price_change_5m = safe_float(market_metrics.get("price_change_5m_percent", 0.0))
    price_change_15m = safe_float(market_metrics.get("price_change_15m_percent", 0.0))
    price_change_1h = safe_float(market_metrics.get("price_change_1h_percent", 0.0))
    price_change_4h = safe_float(market_metrics.get("price_change_4h_percent", 0.0))
    spread = safe_float(market_metrics.get("estimated_spread_percent", 0.2))
    volume_24h = safe_float(market_metrics.get("volume_24h_usdt", 0.0))
    volume_change_ratio = safe_float(market_metrics.get("volume_change_ratio", 1.0))
    distance_from_high = safe_float(market_metrics.get("distance_from_local_high_percent", 0.0))
    has_retest = bool(market_metrics.get("has_retest", False))

    mentions_15m = safe_int(social_signal.get("mentions_15m", 0))
    unique_channels = safe_int(social_signal.get("unique_channels", 0))
    telegram_score = safe_float(social_signal.get("telegram_score", 0.0))

    joined_text = join_sample_texts(social_signal)

    danger_keyword_count = count_keywords(joined_text, DANGER_KEYWORDS)
    positive_keyword_count = count_keywords(joined_text, POSITIVE_KEYWORDS)
    retest_keyword_count = count_keywords(joined_text, RETEST_KEYWORDS)
    negative_keyword_count = count_keywords(joined_text, NEGATIVE_KEYWORDS)

    classification_summary = social_signal.get("message_classification_summary", {})
    message_flags: List[str] = []
    primary_intent = ""

    if isinstance(classification_summary, dict):
        primary_intent = str(classification_summary.get("primary_intent", ""))

        message_flags = [
            str(item)
            for item in classification_summary.get("flags", [])
        ]

        if primary_intent == "possible_news":
            positive_keyword_count += 1

        if primary_intent == "watch_signal":
            positive_keyword_count += 1

        if primary_intent == "pump_fomo":
            danger_keyword_count += 2

    pump_risk = (
        price_change_5m > 6.0
        or price_change_15m > 10.0
        or price_change_1h > 15.0
        or price_change_4h > 35.0
        or danger_keyword_count >= 2
        or volume_change_ratio > 8.0
    )

    dangerous_fomo = (
        danger_keyword_count >= 2
        or primary_intent == "pump_fomo"
        or "message_pump_fomo" in message_flags
    )

    late_entry = (
        price_change_1h > 7.0
        and distance_from_high < 1.5
        and not has_retest
    )

    very_close_to_high = (
        price_change_1h > 3.0
        and distance_from_high < 0.8
        and not has_retest
    )

    low_liquidity = volume_24h < 5_000_000
    thin_liquidity = 5_000_000 <= volume_24h < 10_000_000
    wide_spread = spread > 0.15
    very_wide_spread = spread > 0.5

    weak_market_structure = (
        price_change_15m < -1.5
        and price_change_1h < 0.0
        and not has_retest
    )

    no_market_confirmation = (
        price_change_15m <= 0.0
        or price_change_1h <= 0.0
        or volume_24h < 5_000_000
        or spread > 0.3
    )

    weak_social_confirmation = (
        unique_channels <= 1
        and mentions_15m <= 2
        and telegram_score < 65.0
    )

    needs_retest = (
        not has_retest
        and telegram_score >= 55.0
        and (
            price_change_1h > 2.0
            or price_change_15m > 1.0
            or positive_keyword_count > 0
            or retest_keyword_count > 0
        )
    )

    negative_news_risk = negative_keyword_count > 0

    flags: List[str] = []

    if pump_risk:
        flags.append("pump_risk")

    if dangerous_fomo:
        flags.append("dangerous_fomo")

    if late_entry:
        flags.append("late_entry")

    if very_close_to_high:
        flags.append("very_close_to_high")

    if low_liquidity:
        flags.append("low_liquidity")

    if thin_liquidity:
        flags.append("thin_liquidity")

    if wide_spread:
        flags.append("wide_spread")

    if very_wide_spread:
        flags.append("very_wide_spread")

    if weak_market_structure:
        flags.append("weak_market_structure")

    if no_market_confirmation:
        flags.append("no_market_confirmation")

    if weak_social_confirmation:
        flags.append("weak_social_confirmation")

    if needs_retest:
        flags.append("needs_retest")

    if negative_news_risk:
        flags.append("negative_news_risk")

    for message_flag in message_flags:
        if message_flag not in flags:
            flags.append(message_flag)

    return {
        "pump_risk": pump_risk,
        "dangerous_fomo": dangerous_fomo,
        "late_entry": late_entry,
        "very_close_to_high": very_close_to_high,
        "low_liquidity": low_liquidity,
        "thin_liquidity": thin_liquidity,
        "wide_spread": wide_spread,
        "very_wide_spread": very_wide_spread,
        "weak_market_structure": weak_market_structure,
        "no_market_confirmation": no_market_confirmation,
        "weak_social_confirmation": weak_social_confirmation,
        "needs_retest": needs_retest,
        "negative_news_risk": negative_news_risk,
        "has_retest": has_retest,
        "danger_keyword_count": danger_keyword_count,
        "positive_keyword_count": positive_keyword_count,
        "retest_keyword_count": retest_keyword_count,
        "negative_keyword_count": negative_keyword_count,
        "message_flags": message_flags,
        "flags": flags,
    }


def calculate_risk_adjustment(risk_flags: Dict[str, Any]) -> float:
    adjustment = 72.0

    if risk_flags.get("pump_risk"):
        adjustment -= 45.0

    if risk_flags.get("dangerous_fomo"):
        adjustment -= 28.0

    if risk_flags.get("late_entry"):
        adjustment -= 25.0

    if risk_flags.get("very_close_to_high"):
        adjustment -= 12.0

    if risk_flags.get("low_liquidity"):
        adjustment -= 24.0

    if risk_flags.get("thin_liquidity"):
        adjustment -= 10.0

    if risk_flags.get("wide_spread"):
        adjustment -= 15.0

    if risk_flags.get("very_wide_spread"):
        adjustment -= 18.0

    if risk_flags.get("weak_market_structure"):
        adjustment -= 18.0

    if risk_flags.get("no_market_confirmation"):
        adjustment -= 10.0

    if risk_flags.get("weak_social_confirmation"):
        adjustment -= 8.0

    if risk_flags.get("needs_retest"):
        adjustment -= 8.0

    if risk_flags.get("negative_news_risk"):
        adjustment -= 18.0

    if risk_flags.get("has_retest"):
        adjustment += 15.0

    return clamp_score(adjustment)


def calculate_final_score(
    telegram_score: float,
    market_score: float,
    risk_adjustment: float,
) -> float:
    final_score = (
        float(market_score) * 0.58
        + float(telegram_score) * 0.24
        + float(risk_adjustment) * 0.18
    )

    return clamp_score(final_score)


def classify_signal(final_score: float, risk_flags: Dict[str, Any]) -> str:
    has_retest = bool(risk_flags.get("has_retest", False))

    if risk_flags.get("dangerous_fomo") or risk_flags.get("pump_risk"):
        return "опасный памп"

    if risk_flags.get("negative_news_risk"):
        return "пропустить"

    if risk_flags.get("low_liquidity") and (
        risk_flags.get("wide_spread")
        or risk_flags.get("very_wide_spread")
    ):
        return "пропустить"

    if risk_flags.get("late_entry") and not has_retest:
        return "вход поздний"

    if risk_flags.get("weak_market_structure") and not has_retest:
        return "пропустить"

    if final_score >= 75 and has_retest and not risk_flags.get("no_market_confirmation"):
        return "движение возможно"

    if final_score >= 62 and not has_retest:
        return "ждать ретест"

    if final_score >= 52:
        return "только наблюдать"

    return "пропустить"


def calculate_risk_level(risk_flags: Dict[str, Any]) -> str:
    critical_flags = {
        "pump_risk",
        "dangerous_fomo",
        "low_liquidity",
        "very_wide_spread",
        "negative_news_risk",
    }

    medium_flags = {
        "late_entry",
        "very_close_to_high",
        "wide_spread",
        "weak_market_structure",
        "no_market_confirmation",
        "needs_retest",
        "thin_liquidity",
    }

    flags = set(risk_flags.get("flags", []))

    if flags.intersection(critical_flags):
        return "high"

    if flags.intersection(medium_flags):
        return "medium"

    return "low"


def build_action_hint(status: str, risk_flags: Dict[str, Any]) -> str:
    if status in {"опасный памп", "вход поздний", "пропустить"}:
        return "entry_forbidden"

    if risk_flags.get("needs_retest") or status == "ждать ретест":
        return "wait_retest_confirmation"

    if status == "движение возможно":
        return "manual_review_only"

    return "watch_only"


def build_signal_rating(
    social_signal: Dict[str, Any],
    market_metrics: Dict[str, Any],
) -> Dict[str, Any]:
    telegram_score = calculate_telegram_score(social_signal)

    enriched_social_signal = {
        **social_signal,
        "telegram_score": telegram_score,
    }

    market_score = calculate_market_score(market_metrics)
    risk_flags = analyze_rating_risks(enriched_social_signal, market_metrics)
    risk_adjustment = calculate_risk_adjustment(risk_flags)
    final_score = calculate_final_score(
        telegram_score=telegram_score,
        market_score=market_score,
        risk_adjustment=risk_adjustment,
    )
    status = classify_signal(final_score, risk_flags)
    risk_level = calculate_risk_level(risk_flags)
    action_hint = build_action_hint(status, risk_flags)

    return {
        "ticker": social_signal.get("ticker"),
        "pair": str(social_signal.get("ticker", "")) + "USDT",
        "telegram_score": telegram_score,
        "market_score": market_score,
        "risk_adjustment": risk_adjustment,
        "final_score": final_score,
        "status": status,
        "risk_level": risk_level,
        "action_hint": action_hint,
        "risk_flags": risk_flags["flags"],
        "risk_details": risk_flags,
        "social_signal": social_signal,
        "market_metrics": market_metrics,
        "analytical_only": True,
        "orders_enabled": False,
        "trading_enabled": False,
    }


def export_signal_for_agent(signal: Dict[str, Any]) -> Dict[str, Any]:
    social_signal = signal.get("social_signal", {})
    risk_details = signal.get("risk_details", {})

    return {
        "source": "telegram_scanner",
        "ticker": signal.get("ticker"),
        "pair": signal.get("pair"),
        "exchange": "Binance",
        "telegram_score": signal.get("telegram_score"),
        "market_score": signal.get("market_score"),
        "risk_adjustment": signal.get("risk_adjustment"),
        "final_score": signal.get("final_score"),
        "mention_growth": social_signal.get("mention_growth_factor"),
        "unique_channels": social_signal.get("unique_channels"),
        "market_confirmation": (
            signal.get("market_score", 0) >= 60
            and not risk_details.get("no_market_confirmation", False)
        ),
        "risk_level": signal.get("risk_level"),
        "action_hint": signal.get("action_hint"),
        "risk_flags": signal.get("risk_flags", []),
        "suggested_status": signal.get("status"),
        "has_retest": risk_details.get("has_retest", False),
        "analytical_only": True,
        "orders_enabled": False,
        "trading_enabled": False,
    }


def build_demo_market_metrics() -> Dict[str, Dict[str, Any]]:
    return {
        "TON": {
            "price_change_5m_percent": 0.4,
            "price_change_15m_percent": 1.2,
            "price_change_1h_percent": 4.5,
            "price_change_4h_percent": 8.0,
            "volume_24h_usdt": 35_000_000,
            "volume_change_ratio": 2.4,
            "estimated_spread_percent": 0.08,
            "distance_from_local_high_percent": 2.0,
            "has_retest": False,
        },
        "ETH": {
            "price_change_5m_percent": 0.1,
            "price_change_15m_percent": 0.2,
            "price_change_1h_percent": 0.7,
            "price_change_4h_percent": -2.0,
            "volume_24h_usdt": 500_000_000,
            "volume_change_ratio": 1.1,
            "estimated_spread_percent": 0.03,
            "distance_from_local_high_percent": 5.0,
            "has_retest": False,
        },
        "BTC": {
            "price_change_5m_percent": 0.1,
            "price_change_15m_percent": 0.1,
            "price_change_1h_percent": 0.4,
            "price_change_4h_percent": -1.0,
            "volume_24h_usdt": 1_000_000_000,
            "volume_change_ratio": 1.0,
            "estimated_spread_percent": 0.02,
            "distance_from_local_high_percent": 4.0,
            "has_retest": False,
        },
        "LINK": {
            "price_change_5m_percent": 0.2,
            "price_change_15m_percent": 0.4,
            "price_change_1h_percent": 1.1,
            "price_change_4h_percent": 2.0,
            "volume_24h_usdt": 8_000_000,
            "volume_change_ratio": 1.2,
            "estimated_spread_percent": 0.14,
            "distance_from_local_high_percent": 3.0,
            "has_retest": False,
        },
        "PUMP": {
            "price_change_5m_percent": 12.0,
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


def print_rating_report(signals: List[Dict[str, Any]]) -> None:
    print("SIGNAL RATING REPORT")
    print("====================")
    print("Mode: analytical only")
    print("Orders: disabled")
    print("Trading: disabled")

    if not signals:
        print("No rated signals.")
        return

    for signal in signals:
        print()
        print("Ticker:", signal["ticker"])
        print("Pair:", signal["pair"])
        print("Status:", signal["status"])
        print("Risk level:", signal["risk_level"])
        print("Action hint:", signal["action_hint"])
        print("Telegram Score:", signal["telegram_score"])
        print("Market Score:", signal["market_score"])
        print("Risk Adjustment:", signal["risk_adjustment"])
        print("Final Score:", signal["final_score"])
        print("Risk Flags:", ", ".join(signal["risk_flags"]) or "none")
        print("Agent export:", export_signal_for_agent(signal))


if __name__ == "__main__":
    from datetime import datetime
    from social_signal_engine import (
        analyze_social_signals,
        build_demo_messages,
    )

    now = datetime.now()
    demo_messages = build_demo_messages(now)
    social_results = analyze_social_signals(demo_messages, now=now)
    demo_market = build_demo_market_metrics()

    rated_signals = []

    for social_signal in social_results:
        ticker = social_signal["ticker"]
        market_metrics = demo_market.get(ticker, {})
        rated_signals.append(build_signal_rating(social_signal, market_metrics))

    pump_social = {
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
    }
    rated_signals.append(
        build_signal_rating(
            pump_social,
            demo_market["PUMP"],
        )
    )

    print_rating_report(rated_signals)
