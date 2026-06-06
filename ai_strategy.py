import logging
from statistics import mean
from typing import Dict, List, Any

from trading_journal import log_trade_decision
from config import ALLOW_BEARISH_REVERSAL_BUY as CONFIG_ALLOW_BEARISH_REVERSAL_BUY, TRADING_INTERVAL


STRATEGY_OPTIONS = {
    "allow_bearish_reversal_buy": CONFIG_ALLOW_BEARISH_REVERSAL_BUY,
}


def set_strategy_options(allow_bearish_reversal_buy=None):
    if allow_bearish_reversal_buy is not None:
        STRATEGY_OPTIONS["allow_bearish_reversal_buy"] = bool(allow_bearish_reversal_buy)


def get_strategy_options():
    return dict(STRATEGY_OPTIONS)


def calculate_rsi(closes: List[float], period: int = 14) -> float:
    if len(closes) <= period:
        return 50.0

    gains = []
    losses = []

    recent = closes[-(period + 1):]

    for index in range(1, len(recent)):
        change = recent[index] - recent[index - 1]

        if change > 0:
            gains.append(change)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(change))

    average_gain = mean(gains) if gains else 0.0
    average_loss = mean(losses) if losses else 0.0

    if average_loss == 0:
        return 100.0

    relative_strength = average_gain / average_loss
    rsi = 100 - (100 / (1 + relative_strength))

    return round(rsi, 2)



def calculate_sma(values: List[float], period: int) -> float:
    if not values:
        return 0.0

    clean_values = [float(value) for value in values]

    if len(clean_values) < period:
        return mean(clean_values)

    return mean(clean_values[-period:])


def detect_trend_filter(closes: List[float]) -> str:
    if len(closes) < 50:
        return "neutral"

    sma_fast = calculate_sma(closes, 20)
    sma_slow = calculate_sma(closes, 50)

    if sma_fast > sma_slow:
        return "bullish"

    if sma_fast < sma_slow:
        return "bearish"

    return "neutral"


def detect_short_trend(closes: List[float]) -> str:
    if len(closes) < 5:
        return "flat"

    last = closes[-1]
    previous = closes[-5]

    change_percent = ((last - previous) / previous) * 100 if previous else 0.0

    if change_percent > 1.0:
        return "up"

    if change_percent < -1.0:
        return "down"

    return "flat"


def detect_reversal_signal(closes: List[float]) -> bool:
    """
    Simple reversal detector for oversold markets.

    True when price shows early recovery after a local low:
    - last close is higher than previous close;
    - recent low happened in the last few candles;
    - price bounced from recent low at least 1%.
    """
    if len(closes) < 6:
        return False

    recent = [float(value) for value in closes[-6:]]

    last = recent[-1]
    previous = recent[-2]
    recent_low = min(recent[:-1])

    last_close_is_up = last > previous
    bounced_from_low = ((last - recent_low) / recent_low) * 100 >= 1.0 if recent_low else False
    low_was_recent = recent.index(recent_low) >= 1

    return last_close_is_up and bounced_from_low and low_was_recent


def get_recent_klines(binance_spot_api, symbol: str, interval: str = TRADING_INTERVAL, limit: int = 50) -> List[Any]:
    pair = symbol + "USDT"

    logging.info("loading recent klines for " + pair)

    return binance_spot_api.get_klines(
        symbol=pair,
        interval=interval,
        limit=limit,
    )


def build_market_features(binance_spot_api, symbol: str) -> Dict[str, Any]:
    klines = get_recent_klines(binance_spot_api, symbol)

    closes = [float(item[4]) for item in klines]
    volumes = [float(item[5]) for item in klines]

    current_price = closes[-1] if closes else 0.0
    rsi = calculate_rsi(closes)
    trend = detect_short_trend(closes)
    reversal_signal = detect_reversal_signal(closes)
    trend_filter = detect_trend_filter(closes)

    average_volume = mean(volumes[-14:]) if len(volumes) >= 14 else mean(volumes) if volumes else 0.0
    last_volume = volumes[-1] if volumes else 0.0

    volume_state = "normal"

    if average_volume > 0 and last_volume > average_volume * 1.5:
        volume_state = "high"

    if average_volume > 0 and last_volume < average_volume * 0.6:
        volume_state = "low"

    return {
        "symbol": symbol,
        "pair": symbol + "USDT",
        "current_price": current_price,
        "rsi": rsi,
        "trend": trend,
        "reversal_signal": reversal_signal,
        "trend_filter": trend_filter,
        "last_volume": last_volume,
        "average_volume": average_volume,
        "volume_state": volume_state,
        "closes_count": len(closes),
    }


def make_ai_decision(features: Dict[str, Any]) -> Dict[str, Any]:
    symbol = features["symbol"]
    rsi = float(features["rsi"])
    trend = features["trend"]
    reversal_signal = bool(features.get("reversal_signal", False))
    trend_filter = features.get("trend_filter", "neutral")
    volume_state = features["volume_state"]

    action = "HOLD"
    confidence = 0.50
    reasons = []

    reasons.append("RSI=" + str(rsi))
    reasons.append("trend=" + trend)
    reasons.append("reversal=" + str(reversal_signal))
    reasons.append("trend_filter=" + str(trend_filter))
    reasons.append("volume=" + volume_state)

    if rsi < 30 and reversal_signal and trend_filter == "bullish":
        action = "BUY"
        confidence = 0.72
        reasons.append("RSI ниже 30, есть разворот вверх, тренд-фильтр bullish")

    elif rsi < 30 and reversal_signal and trend_filter == "neutral":
        action = "BUY"
        confidence = 0.64
        reasons.append("RSI ниже 30, есть разворот вверх, тренд-фильтр neutral")

    elif (
        STRATEGY_OPTIONS.get("allow_bearish_reversal_buy", False)
        and rsi < 25
        and reversal_signal
        and trend_filter == "bearish"
        and volume_state == "high"
    ):
        action = "BUY"
        confidence = 0.61
        reasons.append("RSI ниже 25, есть разворот вверх, bearish-тренд, высокий объём подтверждает отскок")

    elif rsi < 35 and trend == "up" and reversal_signal and trend_filter in ("bullish", "neutral"):
        action = "BUY"
        confidence = 0.62
        reasons.append("RSI низкий, тренд вверх, разворот подтверждён, тренд-фильтр не bearish")

    elif rsi > 70 and trend != "up":
        action = "SELL"
        confidence = 0.70
        reasons.append("RSI выше 70: актив может быть перекуплен")

    elif rsi > 65 and trend == "down":
        action = "SELL"
        confidence = 0.62
        reasons.append("RSI высокий и краткосрочный тренд вниз")

    else:
        action = "HOLD"
        confidence = 0.52
        reasons.append("Нет сильного сигнала для сделки")

    if volume_state == "low":
        confidence = max(0.40, confidence - 0.10)
        reasons.append("Объём ниже среднего: уверенность снижена")

    if volume_state == "high" and action != "HOLD":
        confidence = min(0.90, confidence + 0.05)
        reasons.append("Объём выше среднего: сигнал немного усилен")

    return {
        "symbol": symbol,
        "pair": features["pair"],
        "action": action,
        "side": action if action in ("BUY", "SELL") else "NONE",
        "confidence": round(confidence, 2),
        "reason": "; ".join(reasons),
        "features": features,
    }


def analyze_symbol(binance_spot_api, symbol: str, dry_run: bool = True) -> Dict[str, Any]:
    features = build_market_features(binance_spot_api, symbol)
    decision = make_ai_decision(features)

    log_trade_decision(
        symbol=decision["pair"],
        side=decision["side"],
        action="AI_" + decision["action"],
        price=float(features["current_price"]),
        quantity=None,
        volume_usdt=None,
        confidence=float(decision["confidence"]),
        reason=decision["reason"],
        dry_run=dry_run,
        order_id="",
        status="ai_decision",
        raw_response={
            "decision": decision,
            "features": features,
        },
    )

    logging.info(
        "AI decision for " + decision["pair"] +
        ": action=" + decision["action"] +
        ", confidence=" + str(decision["confidence"]) +
        ", reason=" + decision["reason"]
    )

    return decision


if __name__ == "__main__":
    from binance.client import Client
    from credentials import BINANCE_API_KEY, BINANCE_SECRET_KEY
    from config import BINANCE_API_TIMEOUT, DRY_RUN

    logging.basicConfig(level=logging.INFO)

    client = Client(
        api_key=BINANCE_API_KEY,
        api_secret=BINANCE_SECRET_KEY,
        requests_params={"timeout": BINANCE_API_TIMEOUT},
    )

    for item in ["BTC", "ETH"]:
        result = analyze_symbol(client, item, dry_run=DRY_RUN)
        print(result)


def analyze_closes(symbol: str, closes: List[float], volumes: List[float] | None = None) -> Dict[str, Any]:
    """
    Analyze historical close prices without calling Binance API.

    This function is used by backtest.py.
    It returns the same decision format as analyze_symbol().
    """
    if not closes:
        return {
            "symbol": symbol,
            "pair": symbol + "USDT",
            "action": "HOLD",
            "side": "NONE",
            "confidence": 0.0,
            "reason": "Нет данных для анализа",
            "features": {
                "symbol": symbol,
                "pair": symbol + "USDT",
                "current_price": 0.0,
                "rsi": 50.0,
                "trend": "flat",
                "reversal_signal": False,
                "last_volume": 0.0,
                "average_volume": 0.0,
                "volume_state": "normal",
                "closes_count": 0,
            },
        }

    clean_closes = [float(value) for value in closes]

    if volumes is None:
        clean_volumes = [0.0 for _ in clean_closes]
    else:
        clean_volumes = [float(value) for value in volumes]

    current_price = clean_closes[-1]
    rsi = calculate_rsi(clean_closes)
    trend = detect_short_trend(clean_closes)
    reversal_signal = detect_reversal_signal(clean_closes)
    trend_filter = detect_trend_filter(clean_closes)

    if clean_volumes:
        last_volume = clean_volumes[-1]
        recent_volumes = clean_volumes[-14:] if len(clean_volumes) >= 14 else clean_volumes
        average_volume = mean(recent_volumes) if recent_volumes else 0.0
    else:
        last_volume = 0.0
        average_volume = 0.0

    volume_state = "normal"

    if average_volume > 0 and last_volume > average_volume * 1.5:
        volume_state = "high"

    if average_volume > 0 and last_volume < average_volume * 0.6:
        volume_state = "low"

    features = {
        "symbol": symbol,
        "pair": symbol + "USDT",
        "current_price": current_price,
        "rsi": rsi,
        "trend": trend,
        "reversal_signal": reversal_signal,
        "trend_filter": trend_filter,
        "last_volume": last_volume,
        "average_volume": average_volume,
        "volume_state": volume_state,
        "closes_count": len(clean_closes),
    }

    decision = make_ai_decision(features)

    return decision
