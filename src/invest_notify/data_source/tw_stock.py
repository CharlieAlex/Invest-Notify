from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from random import Random

import requests

from invest_notify.storage.schema import PriceRecord

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class PriceProvider:
    provider: str

    def fetch_recent_closes(self, symbols: list[str], lookback_days: int = 90) -> list[PriceRecord]:
        normalized = [_normalize_symbol(s) for s in symbols]
        if self.provider == "twse":
            return _fetch_history_from_twse(normalized, lookback_days=lookback_days)
        return _fetch_history_from_mock(normalized, lookback_days=lookback_days)


def _normalize_symbol(symbol: str) -> str:
    value = symbol.strip()
    if value.isdigit() and len(value) < 4:
        return value.zfill(4)
    return value


def _iter_business_dates(start: date, end: date) -> list[date]:
    days: list[date] = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def _fetch_history_from_mock(symbols: list[str], lookback_days: int = 90) -> list[PriceRecord]:
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=lookback_days)
    trade_dates = _iter_business_dates(start_date, end_date)

    records: list[PriceRecord] = []
    for symbol in symbols:
        base = 100 + (sum(map(ord, symbol)) % 900)

        for idx, trade_date in enumerate(trade_dates):
            seed = int(f"{trade_date.strftime('%Y%m%d')}{sum(map(ord, symbol))}")
            rng = Random(seed)
            trend = idx * 0.08
            drift = rng.uniform(-2.5, 2.5)
            close = round(base + trend + drift, 2)
            records.append(
                PriceRecord(
                    symbol=symbol,
                    ts=datetime.combine(trade_date, time(13, 30)),
                    close=close,
                    source="mock",
                )
            )
    return records


def _month_keys(start: date, end: date) -> list[tuple[int, int]]:
    keys: list[tuple[int, int]] = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        keys.append((year, month))
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
    return keys


def _parse_twse_date(roc_date: str) -> date | None:
    try:
        roc_year, month, day = roc_date.split("/")
        year = int(roc_year) + 1911
        return date(year, int(month), int(day))
    except (ValueError, AttributeError):
        return None


def _fetch_monthly_close_from_twse(symbol: str, year: int, month: int) -> list[PriceRecord]:
    url = (
        "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY"
        f"?date={year}{month:02d}01&stockNo={symbol}&response=json"
    )

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        LOGGER.warning("TWSE monthly request failed for %s %04d-%02d: %s", symbol, year, month, exc)
        return []

    data = payload.get("data", [])
    if not isinstance(data, list):
        return []

    records: list[PriceRecord] = []
    for row in data:
        if not isinstance(row, list) or len(row) < 7:
            continue

        day = _parse_twse_date(str(row[0]))
        close_value = str(row[6]).replace(",", "").strip()
        if day is None or close_value in {"", "-", "--"}:
            continue

        try:
            close = float(close_value)
        except ValueError:
            continue

        records.append(
            PriceRecord(
                symbol=symbol,
                ts=datetime.combine(day, time(13, 30)),
                close=close,
                source="twse",
            )
        )

    return records


def _fetch_history_from_twse(symbols: list[str], lookback_days: int = 90) -> list[PriceRecord]:
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=lookback_days)
    months = _month_keys(start_date, end_date)

    all_records: list[PriceRecord] = []
    for symbol in symbols:
        symbol_records: list[PriceRecord] = []
        for year, month in months:
            symbol_records.extend(_fetch_monthly_close_from_twse(symbol, year, month))

        filtered = [r for r in symbol_records if start_date <= r.ts.date() <= end_date]
        if not filtered:
            LOGGER.warning("No TWSE history for %s, fallback to mock", symbol)
            all_records.extend(_fetch_history_from_mock([symbol], lookback_days=lookback_days))
            continue

        all_records.extend(filtered)

    return all_records
