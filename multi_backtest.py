import csv
from datetime import datetime
from pathlib import Path

from backtest import run_backtest, TAKE_PROFIT_PERCENT, STOP_LOSS_PERCENT, FEE_PERCENT
from config import ALLOW_BEARISH_REVERSAL_BUY, MIN_AI_CONFIDENCE, MAX_TRADE_USDT


DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

CSV_PATH = DATA_DIR / "backtest_results.csv"


TESTS = [
    {"symbol": "BTC", "interval": "1h", "limit": 300},
    {"symbol": "ETH", "interval": "1h", "limit": 300},
    {"symbol": "BTC", "interval": "4h", "limit": 300},
    {"symbol": "ETH", "interval": "4h", "limit": 300},
]


def print_summary_table(results):
    print()
    print("SUMMARY TABLE")
    print("=============")

    header = (
        "Symbol".ljust(10) +
        "Interval".ljust(10) +
        "Profit %".rjust(10) +
        "Profit USDT".rjust(14) +
        "Trades".rjust(10) +
        "BUY".rjust(8) +
        "SELL".rjust(8) +
        "Win %".rjust(10) +
        "Open".rjust(8)
    )

    print(header)
    print("-" * len(header))

    for item in results:
        row = (
            item["pair"].ljust(10) +
            item["interval"].ljust(10) +
            str(item["profit_percent"]).rjust(10) +
            str(item["profit_usdt"]).rjust(14) +
            str(item["trades"]).rjust(10) +
            str(item["buy_count"]).rjust(8) +
            str(item["sell_count"]).rjust(8) +
            str(item["win_rate"]).rjust(10) +
            str(item["open_position"]).rjust(8)
        )

        print(row)


def save_results_to_csv(results):
    file_exists = CSV_PATH.exists()

    fieldnames = [
        "created_at",
        "pair",
        "interval",
        "candles",
        "window_size",
        "initial_balance_usdt",
        "final_balance_usdt",
        "profit_usdt",
        "profit_percent",
        "trades",
        "buy_count",
        "sell_count",
        "win_rate",
        "open_position",
        "final_asset_balance",
        "final_price",
        "allow_bearish_reversal_buy",
        "min_ai_confidence",
        "max_trade_usdt",
        "take_profit_percent",
        "stop_loss_percent",
        "fee_percent",
    ]

    with CSV_PATH.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        created_at = datetime.now().isoformat(timespec="seconds")

        for item in results:
            row = {
                "created_at": created_at,
                **{key: item.get(key) for key in fieldnames if key != "created_at"},
                "allow_bearish_reversal_buy": ALLOW_BEARISH_REVERSAL_BUY,
                "min_ai_confidence": MIN_AI_CONFIDENCE,
                "max_trade_usdt": MAX_TRADE_USDT,
                "take_profit_percent": TAKE_PROFIT_PERCENT,
                "stop_loss_percent": STOP_LOSS_PERCENT,
                "fee_percent": FEE_PERCENT,
            }
            writer.writerow(row)

    print()
    print("CSV saved:", CSV_PATH)


def main():
    print("MULTI BACKTEST")
    print("==============")

    results = []

    for index, test in enumerate(TESTS, start=1):
        print()
        print("=" * 60)
        print(
            "TEST",
            index,
            test["symbol"] + "USDT",
            "interval=" + test["interval"],
            "limit=" + str(test["limit"]),
        )
        print("=" * 60)

        result = run_backtest(
            symbol=test["symbol"],
            interval=test["interval"],
            limit=test["limit"],
        )

        results.append(result)

    print_summary_table(results)
    save_results_to_csv(results)


if __name__ == "__main__":
    main()
