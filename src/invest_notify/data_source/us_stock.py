from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, time, timedelta
from random import Random

import requests

from invest_notify.storage.schema import PriceRecord

LOGGER = logging.getLogger(__name__)


def normalize_us_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def _mock_us_recent_closes(symbols: list[str], lookback_days: int = 90) -> list[PriceRecord]:
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=lookback_days)

    records: list[PriceRecord] = []
    for symbol in [normalize_us_symbol(s) for s in symbols]:
        base = 50 + (sum(map(ord, symbol)) % 450)
        current = start_date
        idx = 0
        while current <= end_date:
            if current.weekday() < 5:
                seed = int(f"{current.strftime('%Y%m%d')}{sum(map(ord, symbol))}")
                rng = Random(seed)
                trend = idx * 0.1
                drift = rng.uniform(-3.0, 3.0)
                close = round(base + trend + drift, 2)
                records.append(
                    PriceRecord(
                        symbol=symbol,
                        ts=datetime.combine(current, time(16, 0)),
                        close=close,
                        source="mock",
                    )
                )
                idx += 1
            current += timedelta(days=1)
    return records


def _fetch_single_us_from_stooq(symbol: str, lookback_days: int) -> list[PriceRecord]:
    norm = normalize_us_symbol(symbol)
    url = f"https://stooq.com/q/d/l/?s={norm.lower()}.us&i=d"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        LOGGER.warning("US request failed for %s: %s", norm, exc)
        return []

    raw = response.text.strip()
    if not raw or "Date,Open,High,Low,Close,Volume" not in raw:
        return []

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=lookback_days)

    reader = csv.DictReader(io.StringIO(raw))
    records: list[PriceRecord] = []
    for row in reader:
        date_text = (row.get("Date") or "").strip()
        close_text = (row.get("Close") or "").strip()
        if not date_text or close_text in {"", "-", "null"}:
            continue

        try:
            day = datetime.strptime(date_text, "%Y-%m-%d").date()
            close = float(close_text)
        except ValueError:
            continue

        if not (start_date <= day <= end_date):
            continue

        records.append(
            PriceRecord(
                symbol=norm,
                ts=datetime.combine(day, time(16, 0)),
                close=close,
                source="us",
            )
        )

    return records


def fetch_us_recent_closes(
    symbols: list[str], lookback_days: int = 90, use_mock: bool = False
) -> list[PriceRecord]:
    normalized = [normalize_us_symbol(s) for s in symbols]
    if use_mock:
        return _mock_us_recent_closes(normalized, lookback_days=lookback_days)

    all_records: list[PriceRecord] = []
    for symbol in normalized:
        rows = _fetch_single_us_from_stooq(symbol, lookback_days=lookback_days)
        if not rows:
            LOGGER.warning("No US history for %s, fallback to mock", symbol)
            rows = _mock_us_recent_closes([symbol], lookback_days=lookback_days)
        all_records.extend(rows)
    return all_records
