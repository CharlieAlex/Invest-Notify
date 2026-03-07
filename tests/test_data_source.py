from invest_notify.data_source.tw_stock import fetch_mock_recent_closes
from invest_notify.data_source.us_stock import fetch_us_recent_closes


def test_mock_fetch_returns_3_month_history_with_padded_symbol() -> None:
    records = fetch_mock_recent_closes(["50", "2330"], lookback_days=90)

    assert len(records) > 100
    symbols = {r.symbol for r in records}
    assert "0050" in symbols
    assert "2330" in symbols
    assert all(r.close > 0 for r in records)


def test_us_mock_fetch_returns_history() -> None:
    records = fetch_us_recent_closes(["qqq"], lookback_days=90, use_mock=True)

    assert len(records) > 40
    assert all(r.symbol == "QQQ" for r in records)
    assert all(r.close > 0 for r in records)
