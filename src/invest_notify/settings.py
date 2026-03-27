from __future__ import annotations

import csv
import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator


class DataSettings(BaseModel):
    raw_file: Path
    sqlite_file: Path
    curated_file: Path
    plot_dir: Path
    table_dir: Path


class SourceSettings(BaseModel):
    provider: str = Field(pattern="^(mock|twse|live)$")


class SchedulerSettings(BaseModel):
    interval_minutes: int = Field(ge=1)


class WindowSettings(BaseModel):
    low_days: int = Field(default=20, ge=1)
    high_days: int = Field(default=20, ge=1)


class LineSettings(BaseModel):
    channel_secret: str
    access_token: str
    user_id: str


class AppSettings(BaseModel):
    app_name: str
    log_level: str
    data: DataSettings
    source: SourceSettings
    scheduler: SchedulerSettings
    window: WindowSettings
    line: LineSettings | None = None


class StockSettings(BaseModel):
    twse_stock: list[str] = Field(default_factory=list)
    tpex_stock: list[str] = Field(default_factory=list)
    esb_stock: list[str] = Field(default_factory=list)
    nasdaq_stock: list[str] = Field(default_factory=list)
    stocks: list[str] = Field(default_factory=list)
    line_notification: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_and_validate(self) -> StockSettings:
        # Backward compatibility: old format uses `stocks` only.
        if (
            self.stocks
            and not self.twse_stock
            and not self.tpex_stock
            and not self.esb_stock
            and not self.nasdaq_stock
        ):
            self.twse_stock = self.stocks

        self.twse_stock = [_normalize_tw_symbol(s) for s in self.twse_stock]
        self.tpex_stock = [_normalize_tw_symbol(s) for s in self.tpex_stock]
        self.esb_stock = [_normalize_tw_symbol(s) for s in self.esb_stock]
        self.nasdaq_stock = [_normalize_us_symbol(s) for s in self.nasdaq_stock]
        self.line_notification = [_normalize_any_symbol(s) for s in self.line_notification]

        total = (
            len(self.twse_stock)
            + len(self.tpex_stock)
            + len(self.esb_stock)
            + len(self.nasdaq_stock)
        )
        if total == 0:
            raise ValueError("At least one stock must be configured")
        return self


def _normalize_tw_symbol(value: str) -> str:
    raw = str(value).strip()
    if raw.isdigit() and len(raw) < 4:
        return raw.zfill(4)
    return raw


def _normalize_us_symbol(value: str) -> str:
    return str(value).strip().upper()


def _normalize_any_symbol(value: str) -> str:
    raw = str(value).strip()
    if raw.isdigit():
        return _normalize_tw_symbol(raw)
    return _normalize_us_symbol(raw)


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        content = yaml.safe_load(f) or {}
    if not isinstance(content, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return content


def load_app_settings(config_path: str | Path = "config/app.yaml") -> AppSettings:
    path = Path(config_path)
    data = _load_yaml(path)

    # Manually load .env if it exists
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

    # Load Line settings from environment and id.md if available
    line_secret = os.getenv("CHANNEL_SECRET")
    line_token = os.getenv("ACCESS_TOKEN")
    user_id = 'U1fe3c5e0fa911a447738a7387a5fcc95'

    if line_secret and line_token and user_id:
        data["line"] = {
            "channel_secret": line_secret,
            "access_token": line_token,
            "user_id": user_id,
        }

    try:
        return AppSettings.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Invalid app settings in {path}: {exc}") from exc


def load_stock_settings(config_path: str | Path = "config/stocks.yaml") -> StockSettings:
    path = Path(config_path)
    data = _load_yaml(path)
    try:
        return StockSettings.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Invalid stock settings in {path}: {exc}") from exc


def load_stock_name_map(config_path: str | Path = "config/stock.csv") -> dict[str, str]:
    path = Path(config_path)
    if not path.exists():
        return {}

    rows: list[list[str]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or all(not str(cell).strip() for cell in row):
                continue
            rows.append([str(cell).strip() for cell in row])

    if not rows:
        return {}

    header = [cell.lower() for cell in rows[0]]
    symbol_idx = 0
    name_idx = 1
    if any(
        key in header
        for key in {"symbol", "code", "ticker", "代碼", "股票代碼", "id"}
    ):
        # Use header mapping if present.
        header_map = {cell: idx for idx, cell in enumerate(header)}
        for key in ("symbol", "code", "ticker", "代碼", "股票代碼", "id"):
            if key in header_map:
                symbol_idx = header_map[key]
                break
        for key in ("name", "名稱", "股票名稱"):
            if key in header_map:
                name_idx = header_map[key]
                break
        data_rows = rows[1:]
    else:
        data_rows = rows

    name_map: dict[str, str] = {}
    for row in data_rows:
        if len(row) <= max(symbol_idx, name_idx):
            continue
        symbol = _normalize_any_symbol(row[symbol_idx])
        name = row[name_idx].strip()
        if symbol:
            name_map[symbol] = name
    return name_map
