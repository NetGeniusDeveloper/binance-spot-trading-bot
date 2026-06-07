from typing import Any, Dict, List


MAX_TEXT_PREVIEW_LENGTH = 300


POSITIVE_NEWS_KEYWORDS = {
    "listing",
    "listed",
    "partnership",
    "mainnet",
    "upgrade",
    "burn",
    "etf",
    "integration",
    "launch",
    "airdrop",
    "ecosystem",
    "обновление",
    "листинг",
    "партнерство",
    "интеграция",
    "запуск",
    "экосистема",
}

WATCH_KEYWORDS = {
    "volume",
    "breakout",
    "retest",
    "accumulation",
    "confirmation",
    "active",
    "growing",
    "support",
    "resistance",
    "watch",
    "wait",
    "объем",
    "объём",
    "пробой",
    "ретест",
    "подтверждение",
    "активен",
    "растет",
    "растёт",
    "поддержка",
    "сопротивление",
    "наблюдать",
    "ждать",
}

RISK_WARNING_KEYWORDS = {
    "no entry",
    "without confirmation",
    "before confirmation",
    "wait for retest",
    "risky",
    "volatile",
    "avoid entry",
    "не входить",
    "без подтверждения",
    "до подтверждения",
    "ждать ретест",
    "риск",
    "волатильно",
    "опасно",
}

DANGER_FOMO_KEYWORDS = {
    "pump",
    "100x",
    "guaranteed",
    "moon",
    "urgent buy",
    "buy now",
    "insider",
    "signal group",
    "low cap gem",
    "next pepe",
    "x100",
    "иксы",
    "ракета",
    "срочно покупай",
    "покупай сейчас",
    "инсайд",
    "гарантия",
    "памп",
}

IGNORE_KEYWORDS = {
    "test message",
    "test messages",
    "тест",
    "проверка",
}


INTENT_SCORE_ADJUSTMENTS = {
    "ignore": -8.0,
    "neutral": 0.0,
    "watch_signal": 8.0,
    "possible_news": 10.0,
    "risk_warning": -4.0,
    "pump_fomo": -35.0,
}


def truncate_text(text: str, max_length: int = MAX_TEXT_PREVIEW_LENGTH) -> str:
    clean_text = " ".join(str(text).split())

    if len(clean_text) <= max_length:
        return clean_text

    return clean_text[:max_length].rstrip() + "..."


def count_keywords(text: str, keywords: set[str]) -> int:
    normalized = str(text).lower()
    count = 0

    for keyword in keywords:
        if keyword.lower() in normalized:
            count += 1

    return count


def contains_any_keyword(text: str, keywords: set[str]) -> bool:
    return count_keywords(text, keywords) > 0


def classify_message_text(text: str) -> Dict[str, Any]:
    """
    Classify one Telegram message for analytical scanner logic.

    Safety:
    - no trading decisions;
    - no order creation;
    - no external AI calls;
    - local rule-based classification only.
    """
    clean_text = " ".join(str(text).split())

    danger_count = count_keywords(clean_text, DANGER_FOMO_KEYWORDS)
    positive_news_count = count_keywords(clean_text, POSITIVE_NEWS_KEYWORDS)
    watch_count = count_keywords(clean_text, WATCH_KEYWORDS)
    risk_warning_count = count_keywords(clean_text, RISK_WARNING_KEYWORDS)
    ignore_count = count_keywords(clean_text, IGNORE_KEYWORDS)

    flags: List[str] = []
    reasons: List[str] = []

    if ignore_count > 0:
        intent = "ignore"
        quality_score = 10.0
        flags.append("message_ignore")
        reasons.append("ignore_keyword_detected")

    elif danger_count >= 2:
        intent = "pump_fomo"
        quality_score = 5.0
        flags.append("message_pump_fomo")
        flags.append("message_low_quality")
        reasons.append("danger_fomo_keywords_detected")

    elif danger_count == 1 and watch_count == 0 and positive_news_count == 0:
        intent = "pump_fomo"
        quality_score = 15.0
        flags.append("message_pump_fomo")
        reasons.append("single_danger_keyword_without_context")

    elif risk_warning_count > 0 and watch_count > 0:
        intent = "watch_signal"
        quality_score = 70.0
        flags.append("message_wait_confirmation")
        reasons.append("watch_signal_with_risk_warning")

    elif risk_warning_count > 0:
        intent = "risk_warning"
        quality_score = 55.0
        flags.append("message_risk_warning")
        reasons.append("risk_warning_keywords_detected")

    elif positive_news_count > 0:
        intent = "possible_news"
        quality_score = 75.0
        flags.append("message_possible_news")
        reasons.append("positive_news_keywords_detected")

    elif watch_count > 0:
        intent = "watch_signal"
        quality_score = 65.0
        flags.append("message_watch_signal")
        reasons.append("watch_keywords_detected")

    else:
        intent = "neutral"
        quality_score = 45.0
        reasons.append("no_strong_signal_keywords")

    score_adjustment = INTENT_SCORE_ADJUSTMENTS.get(intent, 0.0)

    return {
        "intent": intent,
        "quality_score": quality_score,
        "score_adjustment": score_adjustment,
        "positive_news_keyword_count": positive_news_count,
        "watch_keyword_count": watch_count,
        "risk_warning_keyword_count": risk_warning_count,
        "danger_fomo_keyword_count": danger_count,
        "ignore_keyword_count": ignore_count,
        "flags": flags,
        "reasons": reasons,
        "text_preview": truncate_text(clean_text),
    }


def summarize_message_classifications(
    classifications: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Aggregate message classifications for one ticker.

    The result is later used by signal_rating.py to adjust telegram_score
    and risk flags.
    """
    if not classifications:
        return {
            "primary_intent": "neutral",
            "items_count": 0,
            "avg_quality_score": 0.0,
            "score_adjustment": 0.0,
            "counts_by_intent": {},
            "flags": [],
            "reasons": [],
        }

    counts_by_intent: Dict[str, int] = {}
    all_flags: List[str] = []
    all_reasons: List[str] = []
    total_quality = 0.0
    total_adjustment = 0.0

    for item in classifications:
        intent = str(item.get("intent", "neutral"))
        counts_by_intent[intent] = counts_by_intent.get(intent, 0) + 1

        total_quality += float(item.get("quality_score", 0.0))
        total_adjustment += float(item.get("score_adjustment", 0.0))

        for flag in item.get("flags", []):
            flag = str(flag)
            if flag not in all_flags:
                all_flags.append(flag)

        for reason in item.get("reasons", []):
            reason = str(reason)
            if reason not in all_reasons:
                all_reasons.append(reason)

    primary_intent = max(
        counts_by_intent,
        key=lambda key: counts_by_intent[key],
    )

    if "pump_fomo" in counts_by_intent:
        primary_intent = "pump_fomo"
    elif "possible_news" in counts_by_intent:
        primary_intent = "possible_news"
    elif "watch_signal" in counts_by_intent:
        primary_intent = "watch_signal"
    elif "risk_warning" in counts_by_intent:
        primary_intent = "risk_warning"

    avg_quality = round(total_quality / len(classifications), 2)

    # Keep the AI/rule-based layer influential but not dominant.
    score_adjustment = round(max(-40.0, min(25.0, total_adjustment)), 2)

    return {
        "primary_intent": primary_intent,
        "items_count": len(classifications),
        "avg_quality_score": avg_quality,
        "score_adjustment": score_adjustment,
        "counts_by_intent": counts_by_intent,
        "flags": all_flags,
        "reasons": all_reasons,
    }


if __name__ == "__main__":
    samples = [
        "BTCUSDT market is quiet today",
        "#TON looks active, but no entry before confirmation",
        "SOL/USDT volume is growing, but wait for retest",
        "urgent buy now 100x moon guaranteed pump",
        "Binance listing rumor for AVAX ecosystem upgrade",
        "Test messages",
    ]

    print("TELEGRAM MESSAGE CLASSIFIER")
    print("===========================")

    for sample in samples:
        print()
        print(sample)
        print(classify_message_text(sample))
