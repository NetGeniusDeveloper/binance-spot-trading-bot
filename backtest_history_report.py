import csv
from collections import Counter, defaultdict
from pathlib import Path


CSV_PATH = Path("data") / "backtest_results.csv"


def to_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def load_rows():
    if not CSV_PATH.exists():
        print("CSV file not found:", CSV_PATH)
        return []

    with CSV_PATH.open("r", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def print_best_rows(rows, limit=10):
    print()
    print("BEST RESULTS BY PROFIT %")
    print("========================")

    sorted_rows = sorted(
        rows,
        key=lambda row: to_float(row.get("profit_percent")),
        reverse=True,
    )

    for row in sorted_rows[:limit]:
        print(
            row.get("created_at"),
            row.get("pair"),
            row.get("interval"),
            "profit%=" + str(row.get("profit_percent")),
            "profit_usdt=" + str(row.get("profit_usdt")),
            "trades=" + str(row.get("trades")),
            "win_rate=" + str(row.get("win_rate")),
            "bearish_buy=" + str(row.get("allow_bearish_reversal_buy")),
            "min_conf=" + str(row.get("min_ai_confidence")),
            "tp=" + str(row.get("take_profit_percent")),
            "sl=" + str(row.get("stop_loss_percent")),
        )


def print_group_summary(rows, group_key):
    grouped = defaultdict(list)

    for row in rows:
        grouped[row.get(group_key, "unknown")].append(row)

    print()
    print("SUMMARY BY " + group_key.upper())
    print("=" * (11 + len(group_key)))

    for key, items in grouped.items():
        profits = [to_float(item.get("profit_percent")) for item in items]
        trades = [int(to_float(item.get("trades"))) for item in items]

        avg_profit = sum(profits) / len(profits) if profits else 0.0
        best_profit = max(profits) if profits else 0.0
        total_trades = sum(trades)

        print(
            str(key).ljust(10),
            "runs=" + str(len(items)).rjust(3),
            "avg_profit%=" + str(round(avg_profit, 4)).rjust(8),
            "best_profit%=" + str(round(best_profit, 4)).rjust(8),
            "total_trades=" + str(total_trades).rjust(4),
        )


def main():
    rows = load_rows()

    print("BACKTEST HISTORY REPORT")
    print("=======================")
    print("CSV:", CSV_PATH)
    print("Rows:", len(rows))

    if not rows:
        return

    created_counter = Counter(row.get("created_at") for row in rows)

    print()
    print("Runs:", len(created_counter))

    print_best_rows(rows)
    print_group_summary(rows, "pair")
    print_group_summary(rows, "interval")
    print_group_summary(rows, "allow_bearish_reversal_buy")


if __name__ == "__main__":
    main()
