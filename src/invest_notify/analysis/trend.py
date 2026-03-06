from __future__ import annotations

import pandas as pd


def build_trend_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    trend_df = df.copy()
    trend_df["ts"] = pd.to_datetime(trend_df["ts"], errors="coerce")
    trend_df = trend_df.dropna(subset=["ts", "close", "symbol"])
    trend_df = trend_df.sort_values(["symbol", "ts"])

    trend_df["ma_5"] = (
        trend_df.groupby("symbol", group_keys=False)["close"]
        .rolling(window=5, min_periods=1)
        .mean()
        .reset_index(level=0, drop=True)
    )
    return trend_df
