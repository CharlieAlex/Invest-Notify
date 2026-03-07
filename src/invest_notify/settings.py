from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator


class DataSettings(BaseModel):
    raw_file: Path
    curated_file: Path
    plot_dir: Path


class SourceSettings(BaseModel):
    provider: str = Field(pattern="^(mock|twse|live)$")


class SchedulerSettings(BaseModel):
    interval_minutes: int = Field(ge=1)


class AppSettings(BaseModel):
    app_name: str
    log_level: str
    data: DataSettings
    source: SourceSettings
    scheduler: SchedulerSettings


class StockSettings(BaseModel):
    twse_stock: list[str] = Field(default_factory=list)
    tpex_stock: list[str] = Field(default_factory=list)
    esb_stock: list[str] = Field(default_factory=list)
    nasdaq_stock: list[str] = Field(default_factory=list)
    stocks: list[str] = Field(default_factory=list)

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


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        content = yaml.safe_load(f) or {}
    if not isinstance(content, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return content


def load_app_settings(config_path: str | Path = "config/app.yaml") -> AppSettings:
    path = Path(config_path)
    data = _load_yaml(path)
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
