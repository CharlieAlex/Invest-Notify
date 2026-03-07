from __future__ import annotations

import sqlite3
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from invest_notify.storage.schema import PriceRecord


def upsert_records(records: list[PriceRecord], sqlite_path: Path) -> int:
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(sqlite_path) as conn:
        _init_table(conn)
        if not records:
            return 0

        now_text = datetime.now(UTC).isoformat()
        rows = []
        for record in records:
            payload = asdict(record)
            ts_text = payload["ts"].isoformat(sep=" ")
            rows.append(
                (
                    payload["symbol"],
                    ts_text,
                    float(payload["close"]),
                    payload["source"],
                    now_text,
                )
            )

        conn.executemany(
            """
            INSERT INTO prices (symbol, ts, close, source, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(symbol, ts) DO UPDATE SET
                close = excluded.close,
                source = excluded.source,
                updated_at = excluded.updated_at
            """,
            rows,
        )
        conn.commit()
    return len(rows)


def _init_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS prices (
            symbol TEXT NOT NULL,
            ts TEXT NOT NULL,
            close REAL NOT NULL,
            source TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (symbol, ts)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_prices_symbol_ts
        ON prices(symbol, ts)
        """
    )
