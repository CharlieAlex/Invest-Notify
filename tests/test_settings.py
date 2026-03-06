from pathlib import Path

import pytest

from invest_notify.settings import load_stock_settings


def test_load_stock_settings_ok(tmp_path: Path) -> None:
    cfg = tmp_path / "stocks.yaml"
    cfg.write_text('stocks:\n  - "2330"\n', encoding="utf-8")

    data = load_stock_settings(cfg)
    assert data.stocks == ["2330"]


def test_load_stock_settings_empty(tmp_path: Path) -> None:
    cfg = tmp_path / "stocks.yaml"
    cfg.write_text("stocks: []\n", encoding="utf-8")

    with pytest.raises(ValueError):
        load_stock_settings(cfg)
