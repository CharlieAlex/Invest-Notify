from __future__ import annotations

import argparse
import logging

from invest_notify.analysis.trend import build_trend_frame
from invest_notify.data_source.tw_stock import PriceProvider
from invest_notify.scheduler import run_interval_job
from invest_notify.settings import load_app_settings, load_stock_settings
from invest_notify.storage.reader import filter_since, read_prices
from invest_notify.storage.writer import replace_records, save_curated
from invest_notify.utils.logger import setup_logger
from invest_notify.utils.timeutil import now_utc, three_months_ago
from invest_notify.visualization.trend_plot import plot_price, plot_trends

LOGGER = logging.getLogger(__name__)


def run_fetch() -> None:
    app = load_app_settings()
    stocks = load_stock_settings()

    provider = PriceProvider(provider=app.source.provider)
    records = provider.fetch_recent_closes(stocks.stocks, lookback_days=90)
    replace_records(records, app.data.raw_file)

    LOGGER.info(
        "Fetched %d close records for %d stocks from provider=%s",
        len(records),
        len(stocks.stocks),
        app.source.provider,
    )


def run_plot() -> None:
    app = load_app_settings()

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
        symbol_path = plot_price(trend_df, symbol=symbol, output_dir=app.data.plot_dir)
        LOGGER.info("Per-stock plot generated: %s", symbol_path)


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
