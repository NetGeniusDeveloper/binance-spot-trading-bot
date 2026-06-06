import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


DATA_DIR = Path("data")
DB_PATH = DATA_DIR / "social_scanner.db"


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    return connection


def init_scanner_storage() -> None:
    """
    Initialize SQLite storage for analytical social scanner signals.

    This database is separate from trading_journal.db.
    It stores scanner analytics only and does not represent trade orders.
    """
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS scanner_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                ticker TEXT NOT NULL,
                pair TEXT NOT NULL,
                telegram_score REAL NOT NULL,
                market_score REAL NOT NULL,
                risk_adjustment REAL NOT NULL,
                final_score REAL NOT NULL,
                status TEXT NOT NULL,
                risk_flags TEXT NOT NULL,
                raw_signal_json TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_scanner_signals_created_at
            ON scanner_signals(created_at)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_scanner_signals_pair
            ON scanner_signals(pair)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_scanner_signals_status
            ON scanner_signals(status)
            """
        )


def serialize_signal(signal: Dict[str, Any]) -> str:
    return json.dumps(
        signal,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )


def save_scanner_signal(
    signal: Dict[str, Any],
    created_at: datetime | None = None,
) -> int:
    """
    Save one analytical scanner signal.

    This function does not create orders and does not affect trading logic.
    """
    init_scanner_storage()

    if created_at is None:
        created_at = datetime.now()

    risk_flags = signal.get("risk_flags", [])

    if isinstance(risk_flags, list):
        risk_flags_text = ",".join(str(item) for item in risk_flags)
    else:
        risk_flags_text = str(risk_flags)

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO scanner_signals (
                created_at,
                ticker,
                pair,
                telegram_score,
                market_score,
                risk_adjustment,
                final_score,
                status,
                risk_flags,
                raw_signal_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at.isoformat(timespec="seconds"),
                str(signal.get("ticker", "")),
                str(signal.get("pair", "")),
                float(signal.get("telegram_score", 0.0)),
                float(signal.get("market_score", 0.0)),
                float(signal.get("risk_adjustment", 0.0)),
                float(signal.get("final_score", 0.0)),
                str(signal.get("status", "")),
                risk_flags_text,
                serialize_signal(signal),
            ),
        )

        return int(cursor.lastrowid)


def save_scanner_signals(
    signals: List[Dict[str, Any]],
    created_at: datetime | None = None,
) -> List[int]:
    ids = []

    for signal in signals:
        ids.append(save_scanner_signal(signal, created_at=created_at))

    return ids


def list_recent_scanner_signals(limit: int = 20) -> List[Tuple[Any, ...]]:
    init_scanner_storage()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT
                id,
                created_at,
                pair,
                status,
                telegram_score,
                market_score,
                risk_adjustment,
                final_score,
                risk_flags
            FROM scanner_signals
            ORDER BY id DESC
            LIMIT ?
            """,
            (int(limit),),
        )

        return cursor.fetchall()


def print_recent_scanner_signals(limit: int = 20) -> None:
    rows = list_recent_scanner_signals(limit=limit)

    print("RECENT SCANNER SIGNALS")
    print("======================")

    if not rows:
        print("No scanner signals found.")
        return

    for row in rows:
        (
            signal_id,
            created_at,
            pair,
            status,
            telegram_score,
            market_score,
            risk_adjustment,
            final_score,
            risk_flags,
        ) = row

        print(
            "#" + str(signal_id),
            created_at,
            pair,
            "status=" + str(status),
            "telegram=" + str(telegram_score),
            "market=" + str(market_score),
            "risk_adjustment=" + str(risk_adjustment),
            "final=" + str(final_score),
            "risk_flags=" + (str(risk_flags) or "none"),
        )


if __name__ == "__main__":
    init_scanner_storage()
    print("Scanner storage initialized:", DB_PATH)
    print_recent_scanner_signals(limit=10)
