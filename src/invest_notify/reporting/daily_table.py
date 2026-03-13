from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


@dataclass(slots=True)
class DailyRow:
    market: str
    symbol: str
    trade_date: datetime
    close: float
    low_20d: float
    high_20d: float
    is_lower_or_equal_20d_low: bool
    is_higher_or_equal_20d_high: bool


def write_daily_snapshot_table(
    trend_df: pd.DataFrame,
    market_map: dict[str, str],
    table_dir: Path,
) -> Path | None:
    if trend_df.empty:
        return None

    rows = _build_daily_rows(trend_df, market_map)
    if not rows:
        return None

    latest_date = max(r.trade_date for r in rows).date()
    month_file = table_dir / f"{latest_date:%Y-%m}.md"
    table_dir.mkdir(parents=True, exist_ok=True)

    section = _render_section(latest_date.strftime("%Y-%m-%d"), rows)
    _upsert_section(month_file, latest_date.strftime("%Y-%m-%d"), section)
    return month_file


def _build_daily_rows(trend_df: pd.DataFrame, market_map: dict[str, str]) -> list[DailyRow]:
    df = trend_df.copy()
    df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
    df = df.dropna(subset=["ts", "close", "symbol"]).sort_values(["symbol", "ts"])

    rows: list[DailyRow] = []
    for symbol in sorted(df["symbol"].astype(str).unique().tolist()):
        symbol_df = df[df["symbol"].astype(str) == symbol].copy()
        if symbol_df.empty:
            continue

        latest = symbol_df.iloc[-1]
        latest_ts = latest["ts"]
        latest_close = float(latest["close"])

        window_start = latest_ts - timedelta(days=20)
        recent = symbol_df[symbol_df["ts"] >= window_start]
        if recent.empty:
            recent = symbol_df.tail(20)

        low_20d = float(recent["close"].min())
        high_20d = float(recent["close"].max())
        rows.append(
            DailyRow(
                market=market_map.get(symbol, "unknown"),
                symbol=symbol,
                trade_date=latest_ts,
                close=latest_close,
                low_20d=low_20d,
                high_20d=high_20d,
                is_lower_or_equal_20d_low=latest_close <= low_20d,
                is_higher_or_equal_20d_high=latest_close >= high_20d,
            )
        )

    return rows


def _render_section(date_text: str, rows: list[DailyRow]) -> str:
    header = [
        f"## {date_text}",
        "",
        "| 市場 | 股票 | 當天收盤價 | 20天最低價 | 當天是否更低 | 當天是否更高 |",
        "|---|---|---:|---:|:---:|:---:|",
    ]
    body = []
    for row in rows:
        checked = "✅" if row.is_lower_or_equal_20d_low else ""
        checked_high = "✅" if row.is_higher_or_equal_20d_high else ""
        body.append(
            f"| {row.market} | {row.symbol} | {row.close:.2f} | {row.low_20d:.2f} | {checked} | {checked_high} |"  # noqa: E501
        )
    return "\n".join(header + body) + "\n"


def _upsert_section(month_file: Path, date_text: str, section_text: str) -> None:
    if month_file.exists():
        content = month_file.read_text(encoding="utf-8")
    else:
        content = f"# {month_file.stem}\n\n"

    pattern = re.compile(rf"(?ms)^## {re.escape(date_text)}\n.*?(?=^## |\Z)")
    if pattern.search(content):
        updated = pattern.sub(section_text + "\n", content)
    else:
        if not content.endswith("\n"):
            content += "\n"
        updated = content + section_text + "\n"

    month_file.write_text(updated, encoding="utf-8")
