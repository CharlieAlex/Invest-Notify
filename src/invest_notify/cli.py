from __future__ import annotations

import argparse
import logging

from invest_notify.analysis.trend import build_trend_frame
from invest_notify.data_source.tw_stock import (
    fetch_esb_recent_closes,
    fetch_mock_recent_closes,
    fetch_tpex_recent_closes,
    fetch_twse_recent_closes,
)
from invest_notify.data_source.us_stock import fetch_us_recent_closes
from invest_notify.reporting.daily_table import write_daily_snapshot_table
from invest_notify.scheduler import run_interval_job
from invest_notify.settings import load_app_settings, load_stock_name_map, load_stock_settings
from invest_notify.storage.reader import filter_since, read_prices
from invest_notify.storage.sqlite_store import upsert_records
from invest_notify.storage.writer import replace_records, save_curated
from invest_notify.utils.logger import setup_logger
from invest_notify.utils.timeutil import now_utc, three_months_ago
from invest_notify.visualization.trend_plot import plot_market_grid, plot_price, plot_trends

LOGGER = logging.getLogger(__name__)


def run_fetch() -> None:
    app = load_app_settings()
    stocks = load_stock_settings()

    provider = app.source.provider
    use_live = provider in {"twse", "live"}

    records = []
    if use_live:
        records.extend(fetch_twse_recent_closes(stocks.twse_stock, lookback_days=90))
        records.extend(fetch_tpex_recent_closes(stocks.tpex_stock, lookback_days=90))
        records.extend(fetch_esb_recent_closes(stocks.esb_stock, lookback_days=90))
        records.extend(
            fetch_us_recent_closes(stocks.nasdaq_stock, lookback_days=90, use_mock=False)
        )
    else:
        records.extend(fetch_mock_recent_closes(stocks.twse_stock, lookback_days=90))
        records.extend(fetch_mock_recent_closes(stocks.tpex_stock, lookback_days=90))
        records.extend(fetch_mock_recent_closes(stocks.esb_stock, lookback_days=90))
        records.extend(fetch_us_recent_closes(stocks.nasdaq_stock, lookback_days=90, use_mock=True))

    replace_records(records, app.data.raw_file)
    upserted = upsert_records(records, app.data.sqlite_file)

    total_stocks = (
        len(stocks.twse_stock)
        + len(stocks.tpex_stock)
        + len(stocks.esb_stock)
        + len(stocks.nasdaq_stock)
    )
    LOGGER.info(
        "Fetched %d close records for %d stocks from provider=%s (sqlite_upsert=%d)",
        len(records),
        total_stocks,
        provider,
        upserted,
    )


def run_plot() -> None:
    app = load_app_settings()
    stocks = load_stock_settings()
    name_map = load_stock_name_map()
    low_days = app.window.low_days
    high_days = app.window.high_days

    raw_df = read_prices(app.data.raw_file)
    since = three_months_ago(now_utc())
    latest_df = filter_since(raw_df, since)
    trend_df = build_trend_frame(latest_df)

    save_curated(trend_df, app.data.curated_file)
    plot_path = plot_trends(trend_df, app.data.plot_dir)
    LOGGER.info("Plot generated: %s", plot_path)

    if trend_df.empty:
        return

    for symbol in sorted(trend_df["symbol"].astype(str).unique().tolist()):
        symbol_path = plot_price(
            trend_df,
            symbol=symbol,
            output_dir=app.data.plot_dir,
            name_map=name_map,
            low_days=low_days,
            high_days=high_days,
        )
        LOGGER.info("Per-stock plot generated: %s", symbol_path)

    market_groups = {
        "twse": stocks.twse_stock,
        "tpex": stocks.tpex_stock,
        "esb": stocks.esb_stock,
        "nasdaq": stocks.nasdaq_stock,
    }
    for market_name, symbols in market_groups.items():
        grid_path = plot_market_grid(
            trend_df,
            symbols=symbols,
            market_name=market_name,
            output_dir=app.data.plot_dir,
            ncols=3,
            name_map=name_map,
            low_days=low_days,
            high_days=high_days,
        )
        if grid_path is not None:
            LOGGER.info("Market grid generated: %s", grid_path)

    market_map = {}
    for symbol in stocks.twse_stock:
        market_map[symbol] = "twse"
    for symbol in stocks.tpex_stock:
        market_map[symbol] = "tpex"
    for symbol in stocks.esb_stock:
        market_map[symbol] = "esb"
    for symbol in stocks.nasdaq_stock:
        market_map[symbol] = "nasdaq"

    table_path = write_daily_snapshot_table(
        trend_df=trend_df,
        market_map=market_map,
        table_dir=app.data.table_dir,
        name_map=name_map,
        low_days=low_days,
        high_days=high_days,
    )
    if table_path is not None:
        LOGGER.info("Daily table updated: %s", table_path)


def run_once() -> None:
    run_fetch()
    run_plot()


def run_scheduler() -> None:
    app = load_app_settings()
    run_interval_job(run_once, interval_minutes=app.scheduler.interval_minutes)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Invest Notify")
    parser.add_argument(
        "command",
        choices=["fetch", "plot", "run-once", "run-scheduler"],
        help="Command to execute",
    )
    return parser


def main() -> None:
    app = load_app_settings()
    setup_logger(level=app.log_level)

    parser = build_parser()
    args = parser.parse_args()

    if args.command == "fetch":
        run_fetch()
    elif args.command == "plot":
        run_plot()
    elif args.command == "run-once":
        run_once()
    elif args.command == "run-scheduler":
        run_scheduler()
    else:
        parser.print_help()
