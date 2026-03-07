from __future__ import annotations

import csv
import io
import logging
from datetime import date, datetime, time, timedelta
from random import Random

import requests

from invest_notify.storage.schema import PriceRecord

LOGGER = logging.getLogger(__name__)


def normalize_tw_symbol(symbol: str) -> str:
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


def fetch_mock_recent_closes(symbols: list[str], lookback_days: int = 90) -> list[PriceRecord]:
    normalized = [normalize_tw_symbol(s) for s in symbols]
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=lookback_days)
    trade_dates = _iter_business_dates(start_date, end_date)

    records: list[PriceRecord] = []
    for symbol in normalized:
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


def _parse_roc_date(roc_date: str) -> date | None:
    try:
        roc_year, month, day = roc_date.split("/")
        year = int(roc_year) + 1911
        return date(year, int(month), int(day))
    except (ValueError, AttributeError):
        return None


def _parse_row_to_record(row: list, symbol: str, source_label: str) -> PriceRecord | None:
    if not isinstance(row, list) or len(row) < 7:
        return None

    day = _parse_roc_date(str(row[0]))
    close_value = str(row[6]).replace(",", "").strip()
    if day is None or close_value in {"", "-", "--"}:
        return None

    try:
        close = float(close_value)
    except ValueError:
        return None

    return PriceRecord(
        symbol=symbol,
        ts=datetime.combine(day, time(13, 30)),
        close=close,
        source=source_label,
    )


def _fetch_monthly_from_endpoint(
    symbol: str,
    year: int,
    month: int,
    url: str,
    data_key: str,
    source_label: str,
    endpoint_label: str,
) -> list[PriceRecord]:
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        content_type = (response.headers.get("content-type") or "").lower()
        if "json" not in content_type:
            LOGGER.warning(
                "%s monthly endpoint returned non-JSON for %s %04d-%02d. status=%s content_type=%s",
                endpoint_label,
                symbol,
                year,
                month,
                response.status_code,
                content_type,
            )
            return []

        payload = response.json()
    except requests.RequestException as exc:
        LOGGER.warning(
            "%s monthly request failed for %s %04d-%02d: %s",
            endpoint_label,
            symbol,
            year,
            month,
            exc,
        )
        return []
    except ValueError as exc:
        LOGGER.warning(
            "%s monthly JSON parse failed for %s %04d-%02d: %s",
            endpoint_label,
            symbol,
            year,
            month,
            exc,
        )
        return []

    data = payload.get(data_key, [])
    if not isinstance(data, list):
        return []

    records: list[PriceRecord] = []
    for row in data:
        parsed = _parse_row_to_record(row, symbol=symbol, source_label=source_label)
        if parsed is not None:
            records.append(parsed)
    return records


def _fetch_monthly_close_from_twse(symbol: str, year: int, month: int) -> list[PriceRecord]:
    url = (
        "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY"
        f"?date={year}{month:02d}01&stockNo={symbol}&response=json"
    )
    return _fetch_monthly_from_endpoint(
        symbol=symbol,
        year=year,
        month=month,
        url=url,
        data_key="data",
        source_label="twse",
        endpoint_label="TWSE",
    )


def _fetch_monthly_close_from_tpex(symbol: str, year: int, month: int) -> list[PriceRecord]:
    roc_year = year - 1911
    url = (
        "https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/st43_result.php"
        f"?l=zh-tw&d={roc_year}/{month:02d}&stkno={symbol}&s=0,asc,0"
    )
    return _fetch_monthly_from_endpoint(
        symbol=symbol,
        year=year,
        month=month,
        url=url,
        data_key="aaData",
        source_label="tpex",
        endpoint_label="TPEx",
    )


def _fetch_monthly_close_from_esb(symbol: str, year: int, month: int) -> list[PriceRecord]:
    roc_year = year - 1911
    url = (
        "https://www.tpex.org.tw/web/emergingstock/single_historical/history_result.php"
        f"?l=zh-tw&d={roc_year}/{month:02d}&stkno={symbol}&s=0,asc,0"
    )
    return _fetch_monthly_from_endpoint(
        symbol=symbol,
        year=year,
        month=month,
        url=url,
        data_key="aaData",
        source_label="esb",
        endpoint_label="ESB",
    )


def _fetch_from_stooq_taiwan(
    symbol: str, lookback_days: int, source_label: str
) -> list[PriceRecord]:
    url = f"https://stooq.com/q/d/l/?s={symbol}.tw&i=d"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        LOGGER.warning("Stooq fallback failed for %s: %s", symbol, exc)
        return []

    raw = response.text.strip()
    if not raw or "Date,Open,High,Low,Close,Volume" not in raw:
        return []

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=lookback_days)
    records: list[PriceRecord] = []

    reader = csv.DictReader(io.StringIO(raw))
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
                symbol=symbol,
                ts=datetime.combine(day, time(13, 30)),
                close=close,
                source=source_label,
            )
        )
    return records


def _fetch_recent_from_finmind(
    symbol: str, lookback_days: int, source_label: str
) -> list[PriceRecord]:
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=lookback_days)
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {
        "dataset": "TaiwanStockPrice",
        "data_id": symbol,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }

    try:
        response = requests.get(url, params=params, timeout=12)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        LOGGER.warning("FinMind request failed for %s: %s", symbol, exc)
        return []

    rows = payload.get("data", [])
    if not isinstance(rows, list) or not rows:
        return []

    records: list[PriceRecord] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        day_text = str(row.get("date", "")).strip()
        close_value = row.get("close")
        if not day_text or close_value in {"", None, "-"}:
            continue

        try:
            day = datetime.strptime(day_text, "%Y-%m-%d").date()
            close = float(close_value)
        except ValueError:
            continue

        records.append(
            PriceRecord(
                symbol=symbol,
                ts=datetime.combine(day, time(13, 30)),
                close=close,
                source=source_label,
            )
        )
    return records


def _collect_with_monthly_fetch(
    symbols: list[str],
    lookback_days: int,
    fetch_monthly_fn,
    source_label: str,
    market_label: str,
    stooq_fallback: bool,
) -> list[PriceRecord]:
    normalized = [normalize_tw_symbol(s) for s in symbols]
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=lookback_days)
    months = _month_keys(start_date, end_date)

    all_records: list[PriceRecord] = []
    for symbol in normalized:
        symbol_records: list[PriceRecord] = []
        for year, month in months:
            symbol_records.extend(fetch_monthly_fn(symbol, year, month))

        filtered = [r for r in symbol_records if start_date <= r.ts.date() <= end_date]
        if filtered:
            all_records.extend(filtered)
            continue

        if stooq_fallback:
            stooq_rows = _fetch_from_stooq_taiwan(
                symbol,
                lookback_days=lookback_days,
                source_label=source_label,
            )
            if stooq_rows:
                all_records.extend(stooq_rows)
                continue

        LOGGER.warning("No %s history for %s, fallback to mock", market_label, symbol)
        all_records.extend(fetch_mock_recent_closes([symbol], lookback_days=lookback_days))

    return all_records


def fetch_twse_recent_closes(symbols: list[str], lookback_days: int = 90) -> list[PriceRecord]:
    normalized = [normalize_tw_symbol(s) for s in symbols]
    finmind_records: list[PriceRecord] = []
    monthly_fallback_symbols: list[str] = []
    for symbol in normalized:
        rows = _fetch_recent_from_finmind(symbol, lookback_days=lookback_days, source_label="twse")
        if rows:
            finmind_records.extend(rows)
        else:
            monthly_fallback_symbols.append(symbol)

    if not monthly_fallback_symbols:
        return finmind_records

    fallback_records = _collect_with_monthly_fetch(
        symbols=monthly_fallback_symbols,
        lookback_days=lookback_days,
        fetch_monthly_fn=_fetch_monthly_close_from_twse,
        source_label="twse",
        market_label="TWSE",
        stooq_fallback=True,
    )
    return finmind_records + fallback_records


def fetch_tpex_recent_closes(symbols: list[str], lookback_days: int = 90) -> list[PriceRecord]:
    normalized = [normalize_tw_symbol(s) for s in symbols]
    finmind_records: list[PriceRecord] = []
    monthly_fallback_symbols: list[str] = []
    for symbol in normalized:
        rows = _fetch_recent_from_finmind(symbol, lookback_days=lookback_days, source_label="tpex")
        if rows:
            finmind_records.extend(rows)
        else:
            monthly_fallback_symbols.append(symbol)

    if not monthly_fallback_symbols:
        return finmind_records

    fallback_records = _collect_with_monthly_fetch(
        symbols=monthly_fallback_symbols,
        lookback_days=lookback_days,
        fetch_monthly_fn=_fetch_monthly_close_from_tpex,
        source_label="tpex",
        market_label="TPEx",
        stooq_fallback=True,
    )
    return finmind_records + fallback_records


def fetch_esb_recent_closes(symbols: list[str], lookback_days: int = 90) -> list[PriceRecord]:
    normalized = [normalize_tw_symbol(s) for s in symbols]
    finmind_records: list[PriceRecord] = []
    monthly_fallback_symbols: list[str] = []
    for symbol in normalized:
        rows = _fetch_recent_from_finmind(symbol, lookback_days=lookback_days, source_label="esb")
        if rows:
            finmind_records.extend(rows)
        else:
            monthly_fallback_symbols.append(symbol)

    if not monthly_fallback_symbols:
        return finmind_records

    fallback_records = _collect_with_monthly_fetch(
        symbols=monthly_fallback_symbols,
        lookback_days=lookback_days,
        fetch_monthly_fn=_fetch_monthly_close_from_esb,
        source_label="esb",
        market_label="ESB",
        stooq_fallback=False,
    )
    return finmind_records + fallback_records
