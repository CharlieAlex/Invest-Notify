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


def markdown_table_to_line_friendly(text: str) -> str:
    lines = text.strip().splitlines()

    # 先找出「表格開始的那一行：有 | 市場 | 股票 | ...」
    table_start_idx = None
    header_line = None
    for i, line in enumerate(lines):
        if "市場" in line and "|" in line:
            table_start_idx = i
            header_line = line
            break

    if table_start_idx is None:
        # 沒有找到表格，直接回傳原始文字
        return text.strip()

    # 前面不是表格的部分，就當成標題 / header 保留下來
    header_text = "\n".join(lines[:table_start_idx]).strip()
    table_lines = lines[table_start_idx:]

    # 從表格行中取出欄位名稱（header）
    header = [x.strip() for x in header_line.split("|") if x.strip()]
    keys = header

    # 解析資料行
    data_lines = [
        ln for ln in table_lines
        if "|" in ln and "市場" not in ln and "---" not in ln
    ]
    records = []
    for line in data_lines:
        values = [x.strip() for x in line.split("|") if x.strip()]
        row = dict(zip(keys, values, strict=False))
        records.append(row)

    # 轉成 LINE 友善格式
    result_lines = []
    for r in records:
        high, low, now = float(r['10天最高價']), float(r['20天最低價']), float(r['當天收盤價'])

        if low < now and now < high:
            continue

        result_lines.append(f"市場 : {r['市場']}")
        result_lines.append(f"股票 : {r['股票']}")
        result_lines.append(f"股票名稱 : {r['股票名稱']}")
        result_lines.append(f"當天收盤價 : {now}")
        result_lines.append(f"20天最低價 : {low}")
        result_lines.append(f"10天最高價 : {high}")
        if now <= low:
            result_lines.append("建議賣出!!")
        if now >= high:
            result_lines.append("建議買入!!")
        result_lines.append("")

    # 加上原始標題
    line_friendly_table = "\n".join(result_lines).strip()
    if header_text:
        return f"{header_text}\n\n{line_friendly_table}"
    else:
        return line_friendly_table
