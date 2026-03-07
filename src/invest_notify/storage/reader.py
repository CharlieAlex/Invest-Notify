from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd


def read_prices(raw_csv_path: Path) -> pd.DataFrame:
    if not raw_csv_path.exists():
        return pd.DataFrame(columns=["symbol", "ts", "close", "source"])

    df = pd.read_csv(raw_csv_path, dtype={"symbol": "string", "source": "string"})

    # Backward compatibility: old schema used `price`.
    if "close" not in df.columns and "price" in df.columns:
        df = df.rename(columns={"price": "close"})

    if "symbol" in df.columns:
        df["symbol"] = (
            df["symbol"]
            .astype(str)
            .str.strip()
            .apply(lambda x: x.zfill(4) if x.isdigit() and len(x) < 4 else x)
        )
    if "ts" in df.columns:
        df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
    if "close" in df.columns:
        df["close"] = pd.to_numeric(df["close"], errors="coerce")

    return df


def filter_since(df: pd.DataFrame, since: datetime) -> pd.DataFrame:
    if df.empty:
        return df
    return df[df["ts"] >= since].copy()
