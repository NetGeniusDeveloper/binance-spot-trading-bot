from statistics import mean
from typing import Any, Dict, List

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from requests.exceptions import RequestException

from config import BINANCE_API_TIMEOUT, WATCHLIST
from credentials import BINANCE_API_KEY, BINANCE_SECRET_KEY


DEFAULT_INTERVAL = "1m"
DEFAULT_LIMIT = 240


def create_binance_client() -> Client:
    """
    Create Binance public API client.

    This module is analytical only.
    It does not create orders and does not request private balances.
    """
    return Client(
        api_key=BINANCE_API_KEY,
        api_secret=BINANCE_SECRET_KEY,
        requests_params={"timeout": BINANCE_API_TIMEOUT},
    )


def build_pair(symbol: str, quote: str = "USDT") -> str:
    return str(symbol).upper() + str(quote).upper()


def safe_percent_change(old_value: float, new_value: float) -> float:
    if old_value == 0:
        return 0.0

    return round(((new_value - old_value) / old_value) * 100, 2)


def get_close_from_offset(closes: List[float], offset: int) -> float:
    if not closes:
        return 0.0

    if len(closes) > offset:
        return closes[-offset]

    return closes[0]


def estimate_spread_percent(client: Client, pair: str) -> float:
    """
    Estimate current spread from best bid/ask.

    If order book data is unavailable, returns 0.0 instead of crashing.
    """
    try:
        order_book = client.get_order_book(symbol=pair, limit=5)

        bids = order_book.get("bids", [])
        asks = order_book.get("asks", [])

        if not bids or not asks:
            return 0.0

        best_bid = float(bids[0][0])
        best_ask = float(asks[0][0])

        if best_ask <= 0:
            return 0.0

        mid_price = (best_bid + best_ask) / 2

        if mid_price <= 0:
            return 0.0

        return round(((best_ask - best_bid) / mid_price) * 100, 4)

    except Exception:
        return 0.0


def load_klines(
    client: Client,
    pair: str,
    interval: str = DEFAULT_INTERVAL,
    limit: int = DEFAULT_LIMIT,
) -> List[Any]:
    return client.get_klines(
        symbol=pair,
        interval=interval,
        limit=limit,
    )


def calculate_market_metrics_from_klines(
    klines: List[Any],
    spread_percent: float = 0.0,
) -> Dict[str, Any]:
    """
    Calculate market metrics for social scanner rating.

    Expected Binance kline format:
    [
      open_time,
      open,
      high,
      low,
      close,
      volume,
      ...
    ]
    """
    if not klines:
        return {
            "current_price": 0.0,
            "price_change_5m_percent": 0.0,
            "price_change_15m_percent": 0.0,
            "price_change_1h_percent": 0.0,
            "price_change_4h_percent": 0.0,
            "volume_24h_usdt": 0.0,
            "volume_change_ratio": 1.0,
            "high_24h": 0.0,
            "low_24h": 0.0,
            "distance_from_local_high_percent": 0.0,
            "estimated_spread_percent": spread_percent,
            "has_retest": False,
        }

    highs = [float(item[2]) for item in klines]
    lows = [float(item[3]) for item in klines]
    closes = [float(item[4]) for item in klines]
    volumes = [float(item[5]) for item in klines]

    current_price = closes[-1]
    high_local = max(highs)
    low_local = min(lows)

    close_5m = get_close_from_offset(closes, 5)
    close_15m = get_close_from_offset(closes, 15)
    close_1h = get_close_from_offset(closes, 60)
    close_4h = get_close_from_offset(closes, 240)

    quote_volumes = [
        float(close) * float(volume)
        for close, volume in zip(closes, volumes)
    ]

    volume_24h_usdt = round(sum(quote_volumes), 2)

    recent_volume = mean(quote_volumes[-15:]) if len(quote_volumes) >= 15 else mean(quote_volumes)
    previous_volume = mean(quote_volumes[-60:-15]) if len(quote_volumes) >= 60 else recent_volume

    volume_change_ratio = 1.0

    if previous_volume > 0:
        volume_change_ratio = round(recent_volume / previous_volume, 2)

    distance_from_high = 0.0

    if high_local > 0:
        distance_from_high = round(((high_local - current_price) / high_local) * 100, 2)

    has_retest = detect_simple_retest(closes, highs, lows)

    return {
        "current_price": round(current_price, 8),
        "price_change_5m_percent": safe_percent_change(close_5m, current_price),
        "price_change_15m_percent": safe_percent_change(close_15m, current_price),
        "price_change_1h_percent": safe_percent_change(close_1h, current_price),
        "price_change_4h_percent": safe_percent_change(close_4h, current_price),
        "volume_24h_usdt": volume_24h_usdt,
        "volume_change_ratio": volume_change_ratio,
        "high_24h": round(high_local, 8),
        "low_24h": round(low_local, 8),
        "distance_from_local_high_percent": distance_from_high,
        "estimated_spread_percent": spread_percent,
        "has_retest": has_retest,
    }


def detect_simple_retest(
    closes: List[float],
    highs: List[float],
    lows: List[float],
) -> bool:
    """
    Simple retest detector.

    It returns True when:
    - recent local high happened before the last few candles;
    - price pulled back at least 1%;
    - current close recovered above the pullback zone.

    This is only an analytical approximation.
    """
    if len(closes) < 30:
        return False

    recent_high = max(highs[-30:])
    recent_low_after_high = min(lows[-10:])
    current_price = closes[-1]

    if recent_high <= 0:
        return False

    pullback_percent = ((recent_high - recent_low_after_high) / recent_high) * 100
    recovered_percent = ((current_price - recent_low_after_high) / recent_low_after_high) * 100 if recent_low_after_high else 0.0

    return pullback_percent >= 1.0 and recovered_percent >= 0.5 and current_price < recent_high


def get_market_metrics_for_symbol(
    client: Client,
    symbol: str,
    quote: str = "USDT",
    interval: str = DEFAULT_INTERVAL,
    limit: int = DEFAULT_LIMIT,
) -> Dict[str, Any]:
    pair = build_pair(symbol, quote=quote)
    spread_percent = estimate_spread_percent(client, pair)
    klines = load_klines(client, pair=pair, interval=interval, limit=limit)
    metrics = calculate_market_metrics_from_klines(
        klines=klines,
        spread_percent=spread_percent,
    )

    metrics["symbol"] = str(symbol).upper()
    metrics["pair"] = pair
    metrics["interval"] = interval
    metrics["candles"] = len(klines)

    return metrics


def get_market_metrics_for_watchlist(
    symbols: List[str] | None = None,
    quote: str = "USDT",
    interval: str = DEFAULT_INTERVAL,
    limit: int = DEFAULT_LIMIT,
) -> Dict[str, Dict[str, Any]]:
    if symbols is None:
        symbols = WATCHLIST

    client = create_binance_client()
    results: Dict[str, Dict[str, Any]] = {}

    for symbol in symbols:
        symbol = str(symbol).upper()
        pair = build_pair(symbol, quote=quote)

        try:
            metrics = get_market_metrics_for_symbol(
                client=client,
                symbol=symbol,
                quote=quote,
                interval=interval,
                limit=limit,
            )
            results[symbol] = metrics

        except (RequestException, BinanceRequestException, BinanceAPIException, TimeoutError, OSError) as ex:
            results[symbol] = {
                "symbol": symbol,
                "pair": pair,
                "error": str(ex),
            }

        except Exception as ex:
            results[symbol] = {
                "symbol": symbol,
                "pair": pair,
                "error": "Unexpected error: " + str(ex),
            }

    return results


def print_market_metrics_report(results: Dict[str, Dict[str, Any]]) -> None:
    print("SCANNER MARKET DATA REPORT")
    print("==========================")
    print("Mode: analytical only")
    print("Orders: disabled")
    print()

    if not results:
        print("No market metrics.")
        return

    header = (
        "Pair".ljust(12)
        + "Price".rjust(14)
        + "15m %".rjust(10)
        + "1h %".rjust(10)
        + "4h %".rjust(10)
        + "Vol USDT".rjust(16)
        + "Vol x".rjust(10)
        + "Spread %".rjust(10)
        + "HighDist %".rjust(12)
        + "Retest".rjust(9)
    )

    print(header)
    print("-" * len(header))

    for symbol in sorted(results):
        item = results[symbol]

        if item.get("error"):
            print(item.get("pair", symbol).ljust(12), "ERROR:", item["error"])
            continue

        row = (
            str(item.get("pair")).ljust(12)
            + str(item.get("current_price")).rjust(14)
            + str(item.get("price_change_15m_percent")).rjust(10)
            + str(item.get("price_change_1h_percent")).rjust(10)
            + str(item.get("price_change_4h_percent")).rjust(10)
            + str(round(float(item.get("volume_24h_usdt", 0.0)), 2)).rjust(16)
            + str(item.get("volume_change_ratio")).rjust(10)
            + str(item.get("estimated_spread_percent")).rjust(10)
            + str(item.get("distance_from_local_high_percent")).rjust(12)
            + str(item.get("has_retest")).rjust(9)
        )

        print(row)


def main() -> None:
    results = get_market_metrics_for_watchlist(
        symbols=WATCHLIST,
        quote="USDT",
        interval=DEFAULT_INTERVAL,
        limit=DEFAULT_LIMIT,
    )
    print_market_metrics_report(results)


if __name__ == "__main__":
    main()
