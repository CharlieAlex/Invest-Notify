from pathlib import Path

import pandas as pd

from invest_notify.reporting.daily_table import write_daily_snapshot_table


def test_write_daily_snapshot_table_creates_month_file(tmp_path: Path) -> None:
    dates = pd.bdate_range(start="2026-03-01", periods=25)
    df = pd.DataFrame(
        {
            "symbol": ["0050"] * len(dates) + ["QQQ"] * len(dates),
            "ts": list(dates) + list(dates),
            "close": [50 + i * 0.1 for i in range(len(dates))]
            + [100 + i * 0.2 for i in range(len(dates))],
        }
    )

    market_map = {"0050": "twse", "QQQ": "nasdaq"}
    output = write_daily_snapshot_table(df, market_map, tmp_path)

    assert output is not None
    assert output.name == "2026-04.md"

    text = output.read_text(encoding="utf-8")
    assert "## 2026-04-03" in text
    assert "| twse | 0050 |" in text
    assert "| nasdaq | QQQ |" in text
