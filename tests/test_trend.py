import pandas as pd

from invest_notify.analysis.trend import build_trend_frame


def test_build_trend_frame_adds_ma() -> None:
    df = pd.DataFrame(
        {
            "symbol": ["2330", "2330", "2330"],
            "ts": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "close": [100.0, 120.0, 110.0],
            "source": ["mock", "mock", "mock"],
        }
    )

    out = build_trend_frame(df)
    assert "ma_5" in out.columns
    assert round(float(out.iloc[-1]["ma_5"]), 2) == 110.00
