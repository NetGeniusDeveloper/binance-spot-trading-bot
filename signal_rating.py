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
    "иксы",
    "ракета",
    "срочно",
    "инсайд",
    "гарантия",
}


def clamp_score(value: float) -> float:
    return round(max(0.0, min(100.0, float(value))), 2)


def count_keywords(text: str, keywords: set[str]) -> int:
    normalized = text.lower()
    count = 0

    for keyword in keywords:
        if keyword.lower() in normalized:
            count += 1

    return count


def calculate_telegram_score(social_signal: Dict[str, Any]) -> float:
    """
    Calculate Telegram/social signal score from 0 to 100.

    This score is not a trading entry.
    It only shows how strong the social/news impulse is.
    """
    mentions_15m = int(social_signal.get("mentions_15m", 0))
    unique_channels = int(social_signal.get("unique_channels", 0))
    weighted_mentions = float(social_signal.get("weighted_mentions", 0.0))
    mention_growth_factor = float(social_signal.get("mention_growth_factor", 0.0))
    social_signal_enabled = bool(social_signal.get("social_signal", False))

    score = 0.0

    score += min(25.0, mentions_15m * 6.0)
    score += min(20.0, unique_channels * 7.0)
    score += min(20.0, mention_growth_factor * 6.0)
    score += min(15.0, weighted_mentions * 3.0)

    if social_signal_enabled:
        score += 15.0

    classification_summary = social_signal.get("message_classification_summary", {})

    if isinstance(classification_summary, dict):
        message_adjustment = float(classification_summary.get("score_adjustment", 0.0))
        score += max(-40.0, min(25.0, message_adjustment))

    return clamp_score(score)


def calculate_market_score(metrics: Dict[str, Any]) -> float:
    """
    Calculate market score from 0 to 100 using simplified market metrics.

    Expected metrics keys:
    - price_change_15m_percent
    - price_change_1h_percent
    - price_change_4h_percent
    - volume_24h_usdt
    - volume_change_ratio
    - estimated_spread_percent
    - distance_from_local_high_percent
    """
    price_change_15m = float(metrics.get("price_change_15m_percent", 0.0))
    price_change_1h = float(metrics.get("price_change_1h_percent", 0.0))
    price_change_4h = float(metrics.get("price_change_4h_percent", 0.0))
    volume_24h = float(metrics.get("volume_24h_usdt", 0.0))
    volume_change_ratio = float(metrics.get("volume_change_ratio", 1.0))
    spread = float(metrics.get("estimated_spread_percent", 0.2))
    distance_from_high = float(metrics.get("distance_from_local_high_percent", 0.0))

    score = 0.0

    # Momentum, but avoid rewarding extreme pumps too much.
    if 0.5 <= price_change_15m <= 5.0:
        score += 15.0
    elif 0.0 < price_change_15m < 0.5:
        score += 6.0
    elif price_change_15m > 5.0:
        score += 8.0

    if 1.0 <= price_change_1h <= 8.0:
        score += 15.0
    elif 0.0 < price_change_1h < 1.0:
        score += 5.0
    elif price_change_1h > 8.0:
        score += 8.0

    if -5.0 <= price_change_4h <= 15.0:
        score += 10.0

    # Volume and liquidity.
    if volume_24h >= 50_000_000:
        score += 20.0
    elif volume_24h >= 10_000_000:
        score += 15.0
    elif volume_24h >= 5_000_000:
        score += 10.0
    elif volume_24h >= 1_000_000:
        score += 5.0

    if volume_change_ratio >= 3.0:
        score += 15.0
    elif volume_change_ratio >= 2.0:
        score += 10.0
    elif volume_change_ratio >= 1.2:
        score += 5.0

    # Spread.
    if spread <= 0.05:
        score += 10.0
    elif spread <= 0.15:
        score += 7.0
    elif spread <= 0.3:
        score += 3.0

    # Safer if price is not too close to local high.
    if distance_from_high >= 3.0:
        score += 10.0
    elif distance_from_high >= 1.5:
        score += 6.0

    return clamp_score(score)


def analyze_rating_risks(
    social_signal: Dict[str, Any],
    market_metrics: Dict[str, Any],
) -> Dict[str, Any]:
    price_change_1h = float(market_metrics.get("price_change_1h_percent", 0.0))
    price_change_4h = float(market_metrics.get("price_change_4h_percent", 0.0))
    spread = float(market_metrics.get("estimated_spread_percent", 0.2))
    volume_24h = float(market_metrics.get("volume_24h_usdt", 0.0))
    distance_from_high = float(market_metrics.get("distance_from_local_high_percent", 0.0))
    has_retest = bool(market_metrics.get("has_retest", False))

    texts = social_signal.get("sample_texts", [])
    joined_text = " ".join(str(item) for item in texts)

    danger_keyword_count = count_keywords(joined_text, DANGER_KEYWORDS)
    positive_keyword_count = count_keywords(joined_text, POSITIVE_KEYWORDS)

    classification_summary = social_signal.get("message_classification_summary", {})
    message_flags: List[str] = []

    if isinstance(classification_summary, dict):
        message_flags = [
            str(item)
            for item in classification_summary.get("flags", [])
        ]

        if classification_summary.get("primary_intent") == "possible_news":
            positive_keyword_count += 1

        if classification_summary.get("primary_intent") == "watch_signal":
            positive_keyword_count += 1

        if classification_summary.get("primary_intent") == "pump_fomo":
            danger_keyword_count += 2

    pump_risk = (
        price_change_1h > 15.0
        or price_change_4h > 35.0
        or danger_keyword_count >= 2
    )

    late_entry = (
        price_change_1h > 8.0
        and distance_from_high < 1.5
        and not has_retest
    )

    low_liquidity = volume_24h < 5_000_000
    wide_spread = spread > 0.15
    needs_retest = not has_retest and float(social_signal.get("telegram_score", 0.0)) >= 60.0
    dangerous_fomo = (
        danger_keyword_count >= 2
        or "message_pump_fomo" in message_flags
    )

    flags: List[str] = []

    if pump_risk:
        flags.append("pump_risk")

    if late_entry:
        flags.append("late_entry")

    if low_liquidity:
        flags.append("low_liquidity")

    if wide_spread:
        flags.append("wide_spread")

    if needs_retest:
        flags.append("needs_retest")

    if dangerous_fomo:
        flags.append("dangerous_fomo")

    for message_flag in message_flags:
        if message_flag not in flags:
            flags.append(message_flag)

    return {
        "pump_risk": pump_risk,
        "late_entry": late_entry,
        "low_liquidity": low_liquidity,
        "wide_spread": wide_spread,
        "needs_retest": needs_retest,
        "dangerous_fomo": dangerous_fomo,
        "has_retest": has_retest,
        "danger_keyword_count": danger_keyword_count,
        "positive_keyword_count": positive_keyword_count,
        "message_flags": message_flags,
        "flags": flags,
    }


def calculate_risk_adjustment(risk_flags: Dict[str, Any]) -> float:
    adjustment = 70.0

    if risk_flags.get("pump_risk"):
        adjustment -= 45.0

    if risk_flags.get("late_entry"):
        adjustment -= 25.0

    if risk_flags.get("low_liquidity"):
        adjustment -= 20.0

    if risk_flags.get("wide_spread"):
        adjustment -= 15.0

    if risk_flags.get("dangerous_fomo"):
        adjustment -= 20.0

    if risk_flags.get("needs_retest"):
        adjustment -= 8.0

    if risk_flags.get("has_retest"):
        adjustment += 15.0

    return clamp_score(adjustment)


def calculate_final_score(
    telegram_score: float,
    market_score: float,
    risk_adjustment: float,
) -> float:
    final_score = (
        float(market_score) * 0.60
        + float(telegram_score) * 0.25
        + float(risk_adjustment) * 0.15
    )

    return clamp_score(final_score)


def classify_signal(final_score: float, risk_flags: Dict[str, Any]) -> str:
    has_retest = bool(risk_flags.get("has_retest", False))

    if risk_flags.get("pump_risk"):
        return "опасный памп"

    if risk_flags.get("late_entry") and not has_retest:
        return "вход поздний"

    if final_score >= 75 and has_retest:
        return "движение возможно"

    if final_score >= 65 and not has_retest:
        return "ждать ретест"

    if final_score >= 55:
        return "только наблюдать"

    return "пропустить"


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

    return {
        "ticker": social_signal.get("ticker"),
        "pair": str(social_signal.get("ticker", "")) + "USDT",
        "telegram_score": telegram_score,
        "market_score": market_score,
        "risk_adjustment": risk_adjustment,
        "final_score": final_score,
        "status": status,
        "risk_flags": risk_flags["flags"],
        "risk_details": risk_flags,
        "social_signal": social_signal,
        "market_metrics": market_metrics,
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
        "mention_growth": social_signal.get("mention_growth_factor"),
        "unique_channels": social_signal.get("unique_channels"),
        "market_confirmation": signal.get("market_score", 0) >= 60,
        "risk_flags": signal.get("risk_flags", []),
        "suggested_status": signal.get("status"),
        "has_retest": risk_details.get("has_retest", False),
    }


def build_demo_market_metrics() -> Dict[str, Dict[str, Any]]:
    return {
        "TON": {
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

    if not signals:
        print("No rated signals.")
        return

    for signal in signals:
        print()
        print("Ticker:", signal["ticker"])
        print("Pair:", signal["pair"])
        print("Status:", signal["status"])
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

    # Extra demo: dangerous pump signal.
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
