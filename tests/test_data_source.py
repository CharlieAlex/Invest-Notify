from invest_notify.data_source.tw_stock import PriceProvider


def test_mock_fetch_returns_3_month_history_with_padded_symbol() -> None:
    provider = PriceProvider(provider="mock")
    records = provider.fetch_recent_closes(["50", "2330"], lookback_days=90)

    assert len(records) > 100
    symbols = {r.symbol for r in records}
    assert "0050" in symbols
    assert "2330" in symbols
    assert all(r.close > 0 for r in records)
