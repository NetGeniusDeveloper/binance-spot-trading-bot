from collections import Counter
from trading_journal import get_connection, init_trading_journal_db


def fetch_all_rows():
    init_trading_journal_db()

    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                id,
                created_at,
                symbol,
                side,
                action,
                price,
                quantity,
                volume_usdt,
                confidence,
                reason,
                dry_run,
                order_id,
                status
            FROM trading_decisions
            ORDER BY id ASC
            """
        )

        return cursor.fetchall()


def print_counter(title, counter):
    print()
    print(title)
    print("-" * len(title))

    if not counter:
        print("Нет данных")
        return

    for key, value in counter.most_common():
        print(str(key) + ": " + str(value))


def main():
    rows = fetch_all_rows()

    print("TRADING JOURNAL REPORT")
    print("======================")
    print("Всего записей:", len(rows))

    actions = Counter(row[4] for row in rows)
    symbols = Counter(row[2] for row in rows)
    statuses = Counter(row[12] for row in rows)
    dry_run_counter = Counter("DRY_RUN" if row[10] else "REAL" for row in rows)

    print_counter("По action", actions)
    print_counter("По symbol", symbols)
    print_counter("По status", statuses)
    print_counter("DRY_RUN / REAL", dry_run_counter)

    risk_reasons = Counter()

    for row in rows:
        action = row[4]
        reason = row[9] or ""

        if action == "RISK_REJECTED":
            clean_reason = reason.replace("Risk manager result:", "").strip()
            parts = [item.strip() for item in clean_reason.split(",") if item.strip()]

            for part in parts:
                risk_reasons[part] += 1

    print_counter("Причины RISK_REJECTED", risk_reasons)

    print()
    print("Последние 10 записей")
    print("-------------------")

    for row in rows[-10:]:
        (
            row_id,
            created_at,
            symbol,
            side,
            action,
            price,
            quantity,
            volume_usdt,
            confidence,
            reason,
            dry_run,
            order_id,
            status,
        ) = row

        print(
            "#" + str(row_id),
            created_at,
            symbol,
            side,
            action,
            "price=" + str(price),
            "confidence=" + str(confidence),
            "dry_run=" + str(dry_run),
            "status=" + str(status),
            "reason=" + str(reason),
        )


if __name__ == "__main__":
    main()
