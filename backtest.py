from binance.client import Client

from ai_strategy import analyze_closes
from config import BINANCE_API_TIMEOUT, MIN_AI_CONFIDENCE, MAX_TRADE_USDT
from credentials import BINANCE_API_KEY, BINANCE_SECRET_KEY


TAKE_PROFIT_PERCENT = 2.0
STOP_LOSS_PERCENT = 2.0
FEE_PERCENT = 0.1


BACKTEST_OPTIONS = {
    "take_profit_percent": TAKE_PROFIT_PERCENT,
    "stop_loss_percent": STOP_LOSS_PERCENT,
    "fee_percent": FEE_PERCENT,
}


def set_backtest_options(
    take_profit_percent=None,
    stop_loss_percent=None,
    fee_percent=None,
):
    if take_profit_percent is not None:
        BACKTEST_OPTIONS["take_profit_percent"] = float(take_profit_percent)

    if stop_loss_percent is not None:
        BACKTEST_OPTIONS["stop_loss_percent"] = float(stop_loss_percent)

    if fee_percent is not None:
        BACKTEST_OPTIONS["fee_percent"] = float(fee_percent)


def get_backtest_options():
    return dict(BACKTEST_OPTIONS)


def load_klines(client, symbol: str, interval: str = "1h", limit: int = 300):
    pair = symbol + "USDT"

    return client.get_klines(
        symbol=pair,
        interval=interval,
        limit=limit,
    )


def apply_fee(amount: float) -> float:
    fee_percent = BACKTEST_OPTIONS["fee_percent"]
    return amount * (1 - fee_percent / 100)


def run_backtest(
    symbol: str = "BTC",
    interval: str = "1h",
    limit: int = 300,
    window_size: int = 50,
    initial_balance_usdt: float = 1000.0,
):
    client = Client(
        api_key=BINANCE_API_KEY,
        api_secret=BINANCE_SECRET_KEY,
        requests_params={"timeout": BINANCE_API_TIMEOUT},
    )

    klines = load_klines(client, symbol=symbol, interval=interval, limit=limit)

    highs = [float(item[2]) for item in klines]
    lows = [float(item[3]) for item in klines]
    closes = [float(item[4]) for item in klines]
    volumes = [float(item[5]) for item in klines]

    usdt_balance = float(initial_balance_usdt)
    asset_balance = 0.0
    entry_price = None

    trades = []

    take_profit_percent = BACKTEST_OPTIONS["take_profit_percent"]
    stop_loss_percent = BACKTEST_OPTIONS["stop_loss_percent"]
    fee_percent = BACKTEST_OPTIONS["fee_percent"]

    for index in range(window_size, len(closes)):
        window_closes = closes[index - window_size:index]
        window_volumes = volumes[index - window_size:index]

        current_price = closes[index]
        current_high = highs[index]
        current_low = lows[index]

        decision = analyze_closes(
            symbol=symbol,
            closes=window_closes,
            volumes=window_volumes,
        )

        action = decision.get("action")
        confidence = float(decision.get("confidence") or 0.0)

        has_position = asset_balance > 0

        if has_position and entry_price:
            take_profit_price = entry_price * (1 + take_profit_percent / 100)
            stop_loss_price = entry_price * (1 - stop_loss_percent / 100)

            stop_loss_hit = current_low <= stop_loss_price
            take_profit_hit = current_high >= take_profit_price

            if stop_loss_hit:
                exit_price = stop_loss_price
                gross_usdt = asset_balance * exit_price
                net_usdt = apply_fee(gross_usdt)
                profit_percent = ((exit_price - entry_price) / entry_price) * 100

                trades.append({
                    "index": index,
                    "action": "STOP_LOSS_SELL",
                    "price": exit_price,
                    "quantity": asset_balance,
                    "trade_usdt": net_usdt,
                    "confidence": confidence,
                    "profit_percent": profit_percent,
                    "reason": "Stop loss triggered by candle low",
                })

                usdt_balance += net_usdt
                asset_balance = 0.0
                entry_price = None
                continue

            if take_profit_hit:
                exit_price = take_profit_price
                gross_usdt = asset_balance * exit_price
                net_usdt = apply_fee(gross_usdt)
                profit_percent = ((exit_price - entry_price) / entry_price) * 100

                trades.append({
                    "index": index,
                    "action": "TAKE_PROFIT_SELL",
                    "price": exit_price,
                    "quantity": asset_balance,
                    "trade_usdt": net_usdt,
                    "confidence": confidence,
                    "profit_percent": profit_percent,
                    "reason": "Take profit triggered by candle high",
                })

                usdt_balance += net_usdt
                asset_balance = 0.0
                entry_price = None
                continue

        if action == "BUY" and confidence >= MIN_AI_CONFIDENCE and not has_position and usdt_balance > 0:
            trade_usdt = min(MAX_TRADE_USDT, usdt_balance)
            net_trade_usdt = apply_fee(trade_usdt)
            quantity = net_trade_usdt / current_price

            usdt_balance -= trade_usdt
            asset_balance = quantity
            entry_price = current_price

            trades.append({
                "index": index,
                "action": "BUY",
                "price": current_price,
                "quantity": quantity,
                "trade_usdt": trade_usdt,
                "confidence": confidence,
                "profit_percent": 0.0,
                "reason": decision.get("reason"),
            })

        elif action == "SELL" and confidence >= MIN_AI_CONFIDENCE and has_position:
            gross_usdt = asset_balance * current_price
            net_usdt = apply_fee(gross_usdt)
            profit_percent = ((current_price - entry_price) / entry_price) * 100 if entry_price else 0.0

            trades.append({
                "index": index,
                "action": "AI_SELL",
                "price": current_price,
                "quantity": asset_balance,
                "trade_usdt": net_usdt,
                "confidence": confidence,
                "profit_percent": profit_percent,
                "reason": decision.get("reason"),
            })

            usdt_balance += net_usdt
            asset_balance = 0.0
            entry_price = None

    final_price = closes[-1]
    final_total_usdt = usdt_balance + asset_balance * final_price
    profit_usdt = final_total_usdt - initial_balance_usdt
    profit_percent = (profit_usdt / initial_balance_usdt) * 100

    buy_count = sum(1 for item in trades if item["action"] == "BUY")
    sell_count = sum(1 for item in trades if "SELL" in item["action"])

    closed_sells = [item for item in trades if "SELL" in item["action"]]
    winning_sells = [item for item in closed_sells if item.get("profit_percent", 0) > 0]
    win_rate = (len(winning_sells) / len(closed_sells) * 100) if closed_sells else 0.0

    print("BACKTEST REPORT")
    print("===============")
    print("Symbol:", symbol + "USDT")
    print("Interval:", interval)
    print("Candles:", len(closes))
    print("Window size:", window_size)
    print("Initial balance USDT:", round(initial_balance_usdt, 2))
    print("Final balance USDT:", round(final_total_usdt, 2))
    print("Profit USDT:", round(profit_usdt, 2))
    print("Profit %:", round(profit_percent, 2))
    print("Trades:", len(trades))
    print("BUY:", buy_count)
    print("SELL:", sell_count)
    print("Win rate %:", round(win_rate, 2))
    print("Open position:", asset_balance > 0)
    print("Final asset balance:", asset_balance)
    print("Final price:", final_price)
    print("Take profit %:", take_profit_percent)
    print("Stop loss %:", stop_loss_percent)
    print("Fee %:", fee_percent)

    print()
    print("LAST TRADES")
    print("-----------")

    for trade in trades[-20:]:
        print(
            trade["index"],
            trade["action"],
            "price=" + str(round(trade["price"], 4)),
            "qty=" + str(round(trade["quantity"], 8)),
            "usdt=" + str(round(trade["trade_usdt"], 2)),
            "confidence=" + str(trade["confidence"]),
            "profit%=" + str(round(trade.get("profit_percent", 0), 2)),
            "reason=" + str(trade["reason"]),
        )

    return {
        "symbol": symbol,
        "pair": symbol + "USDT",
        "interval": interval,
        "candles": len(closes),
        "window_size": window_size,
        "initial_balance_usdt": round(initial_balance_usdt, 2),
        "final_balance_usdt": round(final_total_usdt, 2),
        "profit_usdt": round(profit_usdt, 2),
        "profit_percent": round(profit_percent, 2),
        "trades": len(trades),
        "buy_count": buy_count,
        "sell_count": sell_count,
        "win_rate": round(win_rate, 2),
        "open_position": asset_balance > 0,
        "final_asset_balance": asset_balance,
        "final_price": final_price,
        "take_profit_percent": take_profit_percent,
        "stop_loss_percent": stop_loss_percent,
        "fee_percent": fee_percent,
    }


if __name__ == "__main__":
    run_backtest(symbol="BTC", interval="1h", limit=300)
