import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "trading_journal.db"


def now_text() -> str:
    return datetime.now().isoformat(timespec="seconds")


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_trading_journal_db() -> None:
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS trading_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,

                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                action TEXT NOT NULL,

                price REAL,
                quantity REAL,
                volume_usdt REAL,

                confidence REAL,
                reason TEXT,

                dry_run INTEGER NOT NULL DEFAULT 1,
                order_id TEXT,
                status TEXT NOT NULL DEFAULT 'logged',

                raw_response TEXT
            )
            """
        )

        conn.commit()


def safe_json(value: Any) -> str:
    if value is None:
        return ""

    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def log_trade_decision(
    symbol: str,
    side: str,
    action: str,
    price: Optional[float] = None,
    quantity: Optional[float] = None,
    volume_usdt: Optional[float] = None,
    confidence: Optional[float] = None,
    reason: str = "",
    dry_run: bool = True,
    order_id: str = "",
    status: str = "logged",
    raw_response: Any = None,
) -> int:
    init_trading_journal_db()

    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO trading_decisions (
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
                raw_response
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now_text(),
                symbol,
                side,
                action,
                price,
                quantity,
                volume_usdt,
                confidence,
                reason,
                1 if dry_run else 0,
                order_id,
                status,
                safe_json(raw_response),
            ),
        )

        conn.commit()
        return int(cursor.lastrowid)


def list_recent_decisions(limit: int = 20):
    init_trading_journal_db()

    limit = max(1, min(int(limit or 20), 500))

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
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )

        rows = cursor.fetchall()

    return rows


if __name__ == "__main__":
    init_trading_journal_db()
    print("Trading journal DB:", DB_PATH)

    rows = list_recent_decisions(limit=10)

    if not rows:
        print("No trading decisions yet.")
    else:
        for row in rows:
            print(row)
