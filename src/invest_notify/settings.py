from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError


class DataSettings(BaseModel):
    raw_file: Path
    curated_file: Path
    plot_dir: Path


class SourceSettings(BaseModel):
    provider: str = Field(pattern="^(mock|twse)$")


class SchedulerSettings(BaseModel):
    interval_minutes: int = Field(ge=1)


class AppSettings(BaseModel):
    app_name: str
    log_level: str
    data: DataSettings
    source: SourceSettings
    scheduler: SchedulerSettings


class StockSettings(BaseModel):
    stocks: list[str]


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
        parsed = StockSettings.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Invalid stock settings in {path}: {exc}") from exc

    if not parsed.stocks:
        raise ValueError("stocks list cannot be empty")
    return parsed
