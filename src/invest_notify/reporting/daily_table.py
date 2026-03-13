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
    symbol_name: str
    trade_date: datetime
    close: float
    low_window: float
    high_window: float
    is_lower_or_equal_low_window: bool
    is_higher_or_equal_high_window: bool


def write_daily_snapshot_table(
    trend_df: pd.DataFrame,
    market_map: dict[str, str],
    table_dir: Path,
    name_map: dict[str, str] | None = None,
    low_days: int = 20,
    high_days: int = 20,
) -> Path | None:
    if trend_df.empty:
        return None

    rows = _build_daily_rows(trend_df, market_map, name_map, low_days, high_days)
    if not rows:
        return None

    latest_date = max(r.trade_date for r in rows).date()
    month_file = table_dir / f"{latest_date:%Y-%m}.md"
    table_dir.mkdir(parents=True, exist_ok=True)

    section = _render_section(latest_date.strftime("%Y-%m-%d"), rows, low_days, high_days)
    _upsert_section(month_file, latest_date.strftime("%Y-%m-%d"), section)
    return month_file


def _build_daily_rows(
    trend_df: pd.DataFrame,
    market_map: dict[str, str],
    name_map: dict[str, str] | None = None,
    low_days: int = 20,
    high_days: int = 20,
) -> list[DailyRow]:
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

        low_start = latest_ts - timedelta(days=low_days)
        recent_low = symbol_df[symbol_df["ts"] >= low_start]
        if recent_low.empty:
            recent_low = symbol_df.tail(max(1, low_days))

        high_start = latest_ts - timedelta(days=high_days)
        recent_high = symbol_df[symbol_df["ts"] >= high_start]
        if recent_high.empty:
            recent_high = symbol_df.tail(max(1, high_days))

        low_window = float(recent_low["close"].min())
        high_window = float(recent_high["close"].max())
        rows.append(
            DailyRow(
                market=market_map.get(symbol, "unknown"),
                symbol=symbol,
                symbol_name=name_map.get(symbol, "").strip() if name_map else "",
                trade_date=latest_ts,
                close=latest_close,
                low_window=low_window,
                high_window=high_window,
                is_lower_or_equal_low_window=latest_close <= low_window,
                is_higher_or_equal_high_window=latest_close >= high_window,
            )
        )

    return rows


def _render_section(date_text: str, rows: list[DailyRow], low_days: int, high_days: int) -> str:
    header = [
        f"## {date_text}",
        "",
        f"| 市場 | 股票 | 股票名稱 | 當天收盤價 | {low_days}天最低價 | {high_days}天最高價 | 建議賣出 | 建議買入 |",  # noqa: E501
        "|---|---|---|---:|---:|---:|:---:|:---:|",
    ]
    body = []
    for row in rows:
        sell_flag = "✅" if row.is_lower_or_equal_low_window else ""
        buy_flag = "✅" if row.is_higher_or_equal_high_window else ""
        body.append(
            f"| {row.market} | {row.symbol} | {row.symbol_name} | {row.close:.2f} | {row.low_window:.2f} | {row.high_window:.2f} | {sell_flag} | {buy_flag} |"  # noqa: E501
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
