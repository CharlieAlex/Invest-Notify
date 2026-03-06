from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pandas as pd

from invest_notify.storage.schema import PriceRecord


def replace_records(records: list[PriceRecord], raw_csv_path: Path) -> pd.DataFrame:
    raw_csv_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame([asdict(r) for r in records])
    if df.empty:
        df = pd.DataFrame(columns=["symbol", "ts", "close", "source"])
    else:
        df["symbol"] = df["symbol"].astype(str)
        df = df.sort_values(["symbol", "ts"]).reset_index(drop=True)

    df = df.drop_duplicates()
    df.to_csv(raw_csv_path, index=False)
    return df


def save_curated(df: pd.DataFrame, curated_csv_path: Path) -> None:
    curated_csv_path.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    if "symbol" in out.columns:
        out["symbol"] = out["symbol"].astype(str)
    out.to_csv(curated_csv_path, index=False)
