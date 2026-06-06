from scanner_storage import DB_PATH, get_connection, init_scanner_storage


def count_scanner_signals() -> int:
    init_scanner_storage()

    with get_connection() as connection:
        cursor = connection.execute("SELECT COUNT(*) FROM scanner_signals")
        row = cursor.fetchone()

    return int(row[0]) if row else 0


def clear_scanner_signals() -> int:
    """
    Clear analytical scanner demo history only.

    This does not touch trading_journal.db and does not affect trading logic.
    """
    init_scanner_storage()

    before_count = count_scanner_signals()

    with get_connection() as connection:
        connection.execute("DELETE FROM scanner_signals")
        connection.execute("DELETE FROM sqlite_sequence WHERE name = 'scanner_signals'")

    return before_count


def main() -> None:
    print("CLEAR SCANNER DEMO HISTORY")
    print("==========================")
    print("DB:", DB_PATH)
    print()
    print("This will clear only scanner_signals from data/social_scanner.db.")
    print("It will NOT touch trading_journal.db.")
    print("It will NOT create orders.")
    print()

    before_count = count_scanner_signals()
    print("Rows before:", before_count)

    deleted_count = clear_scanner_signals()

    after_count = count_scanner_signals()
    print("Rows deleted:", deleted_count)
    print("Rows after:", after_count)

    if after_count == 0:
        print("[OK] Scanner demo history cleared.")
    else:
        print("[WARN] Scanner demo history was not fully cleared.")


if __name__ == "__main__":
    main()
