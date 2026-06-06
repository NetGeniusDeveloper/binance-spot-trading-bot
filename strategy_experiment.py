import csv
from datetime import datetime
from pathlib import Path

from ai_strategy import set_strategy_options, get_strategy_options
from backtest import (
    run_backtest,
    set_backtest_options,
    get_backtest_options,
)


DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

CSV_PATH = DATA_DIR / "strategy_experiments.csv"


EXPERIMENTS = [
    {
        "name": "safe_tp15_sl10",
        "allow_bearish_reversal_buy": False,
        "take_profit_percent": 1.5,
        "stop_loss_percent": 1.0,
        "fee_percent": 0.1,
    },
    {
        "name": "safe_tp20_sl15",
        "allow_bearish_reversal_buy": False,
        "take_profit_percent": 2.0,
        "stop_loss_percent": 1.5,
        "fee_percent": 0.1,
    },
    {
        "name": "safe_tp20_sl20",
        "allow_bearish_reversal_buy": False,
        "take_profit_percent": 2.0,
        "stop_loss_percent": 2.0,
        "fee_percent": 0.1,
    },
    {
        "name": "safe_tp30_sl15",
        "allow_bearish_reversal_buy": False,
        "take_profit_percent": 3.0,
        "stop_loss_percent": 1.5,
        "fee_percent": 0.1,
    },
    {
        "name": "bearish_tp20_sl20",
        "allow_bearish_reversal_buy": True,
        "take_profit_percent": 2.0,
        "stop_loss_percent": 2.0,
        "fee_percent": 0.1,
    },
]


TESTS = [
    {"symbol": "BTC", "interval": "1h", "limit": 300},
    {"symbol": "ETH", "interval": "1h", "limit": 300},
    {"symbol": "BTC", "interval": "4h", "limit": 300},
    {"symbol": "ETH", "interval": "4h", "limit": 300},
]


def print_experiment_summary(results):
    print()
    print("EXPERIMENT SUMMARY")
    print("==================")

    header = (
        "Experiment".ljust(20) +
        "Pair".ljust(10) +
        "Interval".ljust(10) +
        "Profit %".rjust(10) +
        "Trades".rjust(10) +
        "BUY".rjust(8) +
        "SELL".rjust(8) +
        "Win %".rjust(10) +
        "TP".rjust(8) +
        "SL".rjust(8) +
        "Open".rjust(8)
    )

    print(header)
    print("-" * len(header))

    for item in results:
        row = (
            item["experiment"].ljust(20) +
            item["pair"].ljust(10) +
            item["interval"].ljust(10) +
            str(item["profit_percent"]).rjust(10) +
            str(item["trades"]).rjust(10) +
            str(item["buy_count"]).rjust(8) +
            str(item["sell_count"]).rjust(8) +
            str(item["win_rate"]).rjust(10) +
            str(item["take_profit_percent"]).rjust(8) +
            str(item["stop_loss_percent"]).rjust(8) +
            str(item["open_position"]).rjust(8)
        )
        print(row)


def save_results_to_csv(results):
    file_exists = CSV_PATH.exists()

    fieldnames = [
        "created_at",
        "experiment",
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
            }
            writer.writerow(row)

    print()
    print("CSV saved:", CSV_PATH)


def main():
    print("STRATEGY EXPERIMENT")
    print("===================")

    all_results = []

    for experiment in EXPERIMENTS:
        print()
        print("#" * 70)
        print("EXPERIMENT:", experiment["name"])
        print("#" * 70)

        set_strategy_options(
            allow_bearish_reversal_buy=experiment["allow_bearish_reversal_buy"]
        )

        set_backtest_options(
            take_profit_percent=experiment["take_profit_percent"],
            stop_loss_percent=experiment["stop_loss_percent"],
            fee_percent=experiment["fee_percent"],
        )

        print("Strategy options:", get_strategy_options())
        print("Backtest options:", get_backtest_options())

        for test in TESTS:
            print()
            print(
                "Running",
                experiment["name"],
                test["symbol"] + "USDT",
                test["interval"],
            )

            result = run_backtest(
                symbol=test["symbol"],
                interval=test["interval"],
                limit=test["limit"],
            )

            result["experiment"] = experiment["name"]
            result["allow_bearish_reversal_buy"] = experiment["allow_bearish_reversal_buy"]
            result["take_profit_percent"] = experiment["take_profit_percent"]
            result["stop_loss_percent"] = experiment["stop_loss_percent"]
            result["fee_percent"] = experiment["fee_percent"]

            all_results.append(result)

    print_experiment_summary(all_results)
    save_results_to_csv(all_results)

    set_strategy_options(allow_bearish_reversal_buy=False)
    set_backtest_options(take_profit_percent=2.0, stop_loss_percent=2.0, fee_percent=0.1)

    print()
    print("Restored strategy options:", get_strategy_options())
    print("Restored backtest options:", get_backtest_options())


if __name__ == "__main__":
    main()
