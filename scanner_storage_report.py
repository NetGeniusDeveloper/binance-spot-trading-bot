from collections import Counter, defaultdict
from typing import Any, Dict, List, Tuple

from scanner_storage import DB_PATH, get_connection, init_scanner_storage


def fetch_all_signals() -> List[Tuple[Any, ...]]:
    init_scanner_storage()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT
                id,
                created_at,
                ticker,
                pair,
                telegram_score,
                market_score,
                risk_adjustment,
                final_score,
                status,
                risk_flags
            FROM scanner_signals
            ORDER BY id ASC
            """
        )

        return cursor.fetchall()


def split_risk_flags(value: str) -> List[str]:
    if not value:
        return []

    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


def print_summary_by_status(rows: List[Tuple[Any, ...]]) -> None:
    print()
    print("SUMMARY BY STATUS")
    print("=================")

    counter = Counter(row[8] for row in rows)

    if not counter:
        print("No statuses found.")
        return

    for status, count in counter.most_common():
        print(str(status).ljust(20), "count=", count)


def print_summary_by_pair(rows: List[Tuple[Any, ...]]) -> None:
    print()
    print("SUMMARY BY PAIR")
    print("===============")

    grouped: Dict[str, List[Tuple[Any, ...]]] = defaultdict(list)

    for row in rows:
        pair = str(row[3])
        grouped[pair].append(row)

    if not grouped:
        print("No pairs found.")
        return

    for pair in sorted(grouped):
        items = grouped[pair]
        best_final = max(float(item[7]) for item in items)
        avg_final = sum(float(item[7]) for item in items) / len(items)

        print(
            pair.ljust(10),
            "signals=" + str(len(items)).rjust(4),
            "best_final=" + str(round(best_final, 2)).rjust(8),
            "avg_final=" + str(round(avg_final, 2)).rjust(8),
        )


def print_best_signals(rows: List[Tuple[Any, ...]], limit: int = 10) -> None:
    print()
    print("BEST SIGNALS BY FINAL SCORE")
    print("===========================")

    if not rows:
        print("No signals found.")
        return

    sorted_rows = sorted(
        rows,
        key=lambda item: float(item[7]),
        reverse=True,
    )

    for row in sorted_rows[:limit]:
        (
            signal_id,
            created_at,
            ticker,
            pair,
            telegram_score,
            market_score,
            risk_adjustment,
            final_score,
            status,
            risk_flags,
        ) = row

        print(
            "#" + str(signal_id),
            created_at,
            pair,
            "status=" + str(status),
            "final=" + str(final_score),
            "telegram=" + str(telegram_score),
            "market=" + str(market_score),
            "risks=" + (str(risk_flags) or "none"),
        )


def print_recent_signals(rows: List[Tuple[Any, ...]], limit: int = 10) -> None:
    print()
    print("RECENT SIGNALS")
    print("==============")

    if not rows:
        print("No signals found.")
        return

    for row in list(reversed(rows))[:limit]:
        (
            signal_id,
            created_at,
            ticker,
            pair,
            telegram_score,
            market_score,
            risk_adjustment,
            final_score,
            status,
            risk_flags,
        ) = row

        print(
            "#" + str(signal_id),
            created_at,
            pair,
            "status=" + str(status),
            "final=" + str(final_score),
            "risks=" + (str(risk_flags) or "none"),
        )


def print_risk_flags_summary(rows: List[Tuple[Any, ...]]) -> None:
    print()
    print("RISK FLAGS SUMMARY")
    print("==================")

    counter: Counter[str] = Counter()

    for row in rows:
        risk_flags = str(row[9] or "")
        counter.update(split_risk_flags(risk_flags))

    if not counter:
        print("No risk flags found.")
        return

    for flag, count in counter.most_common():
        print(flag.ljust(25), "count=", count)


def main() -> None:
    rows = fetch_all_signals()

    print("SCANNER STORAGE HISTORY REPORT")
    print("==============================")
    print("DB:", DB_PATH)
    print("Rows:", len(rows))

    print_summary_by_status(rows)
    print_summary_by_pair(rows)
    print_best_signals(rows, limit=10)
    print_recent_signals(rows, limit=10)
    print_risk_flags_summary(rows)


if __name__ == "__main__":
    main()
