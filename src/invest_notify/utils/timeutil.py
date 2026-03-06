from __future__ import annotations

from datetime import datetime, timedelta


def now_utc() -> datetime:
    return datetime.utcnow()


def three_months_ago(now: datetime) -> datetime:
    return now - timedelta(days=90)
