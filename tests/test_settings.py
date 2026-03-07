from pathlib import Path

import pytest

from invest_notify.settings import load_stock_settings


def test_load_stock_settings_ok_new_format(tmp_path: Path) -> None:
    cfg = tmp_path / "stocks.yaml"
    cfg.write_text(
        'twse_stock:\n  - "0050"\ntpex_stock:\n  - "6462"\nesb_stock:\n  - "5297"\n'
        'nasdaq_stock:\n  - "QQQ"\n',
        encoding="utf-8",
    )

    data = load_stock_settings(cfg)
    assert data.twse_stock == ["0050"]
    assert data.tpex_stock == ["6462"]
    assert data.esb_stock == ["5297"]
    assert data.nasdaq_stock == ["QQQ"]


def test_load_stock_settings_old_format_compatible(tmp_path: Path) -> None:
    cfg = tmp_path / "stocks.yaml"
    cfg.write_text('stocks:\n  - "2330"\n', encoding="utf-8")

    data = load_stock_settings(cfg)
    assert data.twse_stock == ["2330"]


def test_load_stock_settings_empty(tmp_path: Path) -> None:
    cfg = tmp_path / "stocks.yaml"
    cfg.write_text(
        "twse_stock: []\ntpex_stock: []\nesb_stock: []\nnasdaq_stock: []\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_stock_settings(cfg)
