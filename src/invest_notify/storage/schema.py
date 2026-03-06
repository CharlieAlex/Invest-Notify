from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class PriceRecord:
    symbol: str
    ts: datetime
    close: float
    source: str
