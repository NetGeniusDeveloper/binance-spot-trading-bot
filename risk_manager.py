from datetime import datetime

from config import (
    DRY_RUN,
    MAX_DAILY_TRADES,
    MAX_TRADE_USDT,
    MIN_AI_CONFIDENCE,
    ACTIVE_TRADING_SYMBOLS,
)
from trading_journal import get_connection, init_trading_journal_db


def get_allowed_symbols() -> set[str]:
    return {
        item["symbol"]
        for item in ACTIVE_TRADING_SYMBOLS
        if item.get("symbol")
    }


def count_today_trade_actions() -> int:
    init_trading_journal_db()

    today = datetime.now().strftime("%Y-%m-%d")

    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM trading_decisions
            WHERE created_at LIKE ?
            AND action IN (
                'DRY_RUN_BUY',
                'DRY_RUN_SELL',
                'REAL_BUY',
                'REAL_SELL'
            )
            """,
            (today + "%",),
        )

        row = cursor.fetchone()

    return int(row[0] or 0)


def validate_ai_trade(
    symbol: str,
    action: str,
    confidence: float,
    volume_usdt: float,
) -> dict:
    reasons = []

    allowed_symbols = get_allowed_symbols()

    if symbol not in allowed_symbols:
        reasons.append("symbol_not_allowed")

    if action not in ("BUY", "SELL"):
        reasons.append("action_is_not_trade")

    if confidence < MIN_AI_CONFIDENCE:
        reasons.append("confidence_too_low")

    if action == "BUY":
        if volume_usdt <= 0:
            reasons.append("volume_usdt_is_zero")

        if volume_usdt > MAX_TRADE_USDT:
            reasons.append("volume_usdt_exceeds_max_trade_limit")

    today_trades = count_today_trade_actions()

    if today_trades >= MAX_DAILY_TRADES:
        reasons.append("max_daily_trades_reached")

    approved = len(reasons) == 0

    return {
        "approved": approved,
        "dry_run": DRY_RUN,
        "symbol": symbol,
        "action": action,
        "confidence": confidence,
        "volume_usdt": volume_usdt,
        "today_trades": today_trades,
        "reasons": reasons,
    }


if __name__ == "__main__":
    tests = [
        ("BTC", "BUY", 0.70, 5.0),
        ("ETH", "HOLD", 0.52, 0.0),
        ("DOGE", "BUY", 0.80, 5.0),
        ("BTC", "BUY", 0.40, 5.0),
        ("BTC", "BUY", 0.80, 100.0),
    ]

    for item in tests:
        print(validate_ai_trade(*item))
