import sqlite3
from datetime import datetime
from pathlib import Path

from invest_notify.storage.schema import PriceRecord
from invest_notify.storage.sqlite_store import upsert_records


def test_upsert_records_insert_and_update(tmp_path: Path) -> None:
    db_path = tmp_path / "prices.sqlite"

    inserted = upsert_records(
        [
            PriceRecord(symbol="0050", ts=datetime(2026, 3, 1, 13, 30), close=100.0, source="twse"),
            PriceRecord(symbol="0050", ts=datetime(2026, 3, 2, 13, 30), close=101.0, source="twse"),
        ],
        db_path,
    )
    assert inserted == 2

    updated = upsert_records(
        [
            PriceRecord(symbol="0050", ts=datetime(2026, 3, 2, 13, 30), close=111.0, source="twse"),
        ],
        db_path,
    )
    assert updated == 1

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT symbol, ts, close, source FROM prices ORDER BY ts"
        ).fetchall()

    assert len(rows) == 2
    assert rows[0][0] == "0050"
    assert rows[0][2] == 100.0
    assert rows[1][2] == 111.0
