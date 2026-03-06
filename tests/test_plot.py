from pathlib import Path

import pandas as pd

from invest_notify.visualization.trend_plot import plot_price, plot_trends


def test_plot_trends_generates_png(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "symbol": ["2330", "2330"],
            "ts": pd.to_datetime(["2026-01-01", "2026-01-02"]),
            "close": [100.0, 101.0],
            "ma_5": [100.0, 100.5],
        }
    )
    output = plot_trends(df, tmp_path)

    assert output.exists()
    assert output.suffix == ".png"


def test_plot_price_generates_single_stock_png(tmp_path: Path) -> None:
    dates = pd.bdate_range(start="2026-01-01", periods=45)
    df = pd.DataFrame(
        {
            "symbol": ["2330"] * len(dates),
            "ts": dates,
            "close": [100 + i * 0.4 for i in range(len(dates))],
        }
    )

    output = plot_price(df, symbol="2330", output_dir=tmp_path)
    assert output.exists()
    assert output.name == "price_2330.png"
