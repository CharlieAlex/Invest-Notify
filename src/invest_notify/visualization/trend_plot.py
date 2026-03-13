from __future__ import annotations

import math
from datetime import timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib import rcParams

sns.set_theme(style="whitegrid")
rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Noto Sans CJK TC', 'Noto Sans CJK JP']
rcParams['axes.unicode_minus'] = True


def _plot_empty(output_path: Path, message: str) -> Path:
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.text(0.5, 0.5, message, ha="center", va="center")
    ax.set_axis_off()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_trends(df: pd.DataFrame, output_dir: Path, filename: str = "trend_3m.png") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename

    if df.empty:
        return _plot_empty(output_path, "No data to plot")

    fig, ax = plt.subplots(figsize=(12, 6))

    sns.lineplot(data=df, x="ts", y="close", hue="symbol", ax=ax, linewidth=1.6)
    if "ma_5" in df.columns:
        sns.lineplot(
            data=df,
            x="ts",
            y="ma_5",
            hue="symbol",
            ax=ax,
            linewidth=2.2,
            linestyle="--",
            legend=False,
        )

    ax.set_title("Taiwan Stock 3-Month Close Trend")
    ax.set_xlabel("Time")
    ax.set_ylabel("Close")
    fig.autofmt_xdate()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_price(
    df: pd.DataFrame,
    symbol: str,
    output_dir: Path,
    days_back: int = 60,
    name_map: dict[str, str] | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"price_{symbol}.png"

    symbol_df = df[df["symbol"].astype(str) == symbol].copy()
    if symbol_df.empty:
        return _plot_empty(output_path, f"No data for {symbol}")

    symbol_df["ts"] = pd.to_datetime(symbol_df["ts"], errors="coerce")
    symbol_df = symbol_df.dropna(subset=["ts", "close"]).sort_values("ts")
    if symbol_df.empty:
        return _plot_empty(output_path, f"No valid data for {symbol}")

    if days_back is not None:
        cutoff = symbol_df["ts"].max() - pd.Timedelta(days=days_back)
        symbol_df = symbol_df[symbol_df["ts"] >= cutoff]
        if symbol_df.empty:
            return _plot_empty(output_path, f"No data within last {days_back} days for {symbol}")

    fig, ax = plt.subplots(figsize=(12, 6))
    sns.scatterplot(data=symbol_df, x="ts", y="close", ax=ax, color="#1f77b4")
    sns.lineplot(data=symbol_df, x="ts", y="close", ax=ax, color="#1f77b4", linewidth=2.0)

    latest_row = symbol_df.iloc[-1]
    latest_date = latest_row["ts"]
    latest_close = float(latest_row["close"])

    cutoff_date = latest_date - timedelta(days=20)
    ax.axvline(cutoff_date, color="#6c757d", linestyle="--", linewidth=1.4)

    recent_20_df = symbol_df[symbol_df["ts"] >= cutoff_date].copy()
    if recent_20_df.empty:
        recent_20_df = symbol_df.tail(20).copy()

    low_idx = recent_20_df["close"].idxmin()
    low_row = recent_20_df.loc[low_idx]
    low_date = low_row["ts"]
    low_close = float(low_row["close"])

    high_idx = recent_20_df["close"].idxmax()
    high_row = recent_20_df.loc[high_idx]
    high_date = high_row["ts"]
    high_close = float(high_row["close"])

    ax.scatter([low_date], [low_close], color="#d62728", s=55, zorder=5)
    ax.scatter([high_date], [high_close], color="#9467bd", s=55, zorder=5)
    ax.scatter([latest_date], [latest_close], color="#2ca02c", s=55, zorder=5)

    # ax.annotate(
    #     f"20D Low: {low_date:%Y-%m-%d}\nClose: {low_close:.2f}",
    #     xy=(low_date, low_close),
    #     xytext=(12, 12),
    #     textcoords="offset points",
    #     color="#d62728",
    #     fontsize=10,
    #     bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "#d62728", "alpha": 0.9},
    # )
    # ax.annotate(
    #     f"Latest: {latest_date:%Y-%m-%d}\nClose: {latest_close:.2f}",
    #     xy=(latest_date, latest_close),
    #     xytext=(12, -35),
    #     textcoords="offset points",
    #     color="#2ca02c",
    #     fontsize=10,
    #     bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "#2ca02c", "alpha": 0.9},
    # )

    def _add_corner_annotations(ax, annotations: list[dict]) -> None:
        """
        將所有標注框統一放在圖的右下角，由下往上堆疊。
        annotations: [{"text": str, "color": str}, ...]
        """
        fig = ax.get_figure()
        fig.canvas.draw()  # 確保 renderer 已初始化

        x_pos = 0.98  # 靠右
        y_start = 0.04  # 從底部開始
        y_padding = 0.01
        current_y = y_start

        for ann in annotations:
            t = ax.annotate(
                ann["text"],
                xy=(1, 0),
                xycoords="axes fraction",
                xytext=(x_pos, current_y),
                textcoords="axes fraction",
                ha="right",
                va="bottom",
                color=ann["color"],
                fontsize=10,
                bbox={
                    "boxstyle": "round,pad=0.25",
                    "fc": "white",
                    "ec": ann["color"],
                    "alpha": 0.9,
                },
                annotation_clip=False,
            )

            # 取得這個框的高度，決定下一個框的 y 位置
            fig.canvas.draw()
            bbox = t.get_bbox_patch().get_window_extent(fig.canvas.get_renderer())
            ax_bbox = ax.get_window_extent(fig.canvas.get_renderer())
            box_height_fraction = bbox.height / ax_bbox.height

            current_y += box_height_fraction + y_padding

    # 使用方式
    lp, hp, np = low_close, high_close, latest_close
    _add_corner_annotations(
        ax,
        [
            {"text": f"20D Low: {low_date:%Y-%m-%d}\nClose: {lp:.2f}", "color": "#d62728"},
            {"text": f"20D High: {high_date:%Y-%m-%d}\nClose: {hp:.2f}", "color": "#9467bd"},
            {"text": f"Latest: {latest_date:%Y-%m-%d}\nClose: {np:.2f}", "color": "#2ca02c"},
        ],
    )

    display_name = ""
    if name_map:
        display_name = name_map.get(symbol, "").strip()
    if display_name:
        ax.set_title(f"{symbol} {display_name} Close Price")
    else:
        ax.set_title(f"{symbol} Close Price")
    ax.set_xlabel("Date")
    ax.set_ylabel("Close")
    ax.grid(True, alpha=0.25)
    fig.autofmt_xdate()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_market_grid(
    df: pd.DataFrame,
    symbols: list[str],
    market_name: str,
    output_dir: Path,
    ncols: int = 3,
    name_map: dict[str, str] | None = None,
) -> Path | None:
    output_dir.mkdir(parents=True, exist_ok=True)

    market_symbols = [s for s in symbols if s in df["symbol"].astype(str).unique().tolist()]
    if not market_symbols:
        return None

    nrows = max(1, math.ceil(len(market_symbols) / ncols))
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(18, 4.8 * nrows))
    axes_list = list(axes.flatten()) if hasattr(axes, "flatten") else [axes]

    for idx, symbol in enumerate(market_symbols):
        ax = axes_list[idx]
        symbol_df = df[df["symbol"].astype(str) == symbol].copy()
        symbol_df["ts"] = pd.to_datetime(symbol_df["ts"], errors="coerce")
        symbol_df = symbol_df.dropna(subset=["ts", "close"]).sort_values("ts")
        if symbol_df.empty:
            ax.set_axis_off()
            continue

        sns.scatterplot(data=symbol_df, x="ts", y="close", ax=ax, color="#1f77b4", s=18, alpha=0.75)
        sns.lineplot(data=symbol_df, x="ts", y="close", ax=ax, color="#1f77b4", linewidth=1.6)

        latest_row = symbol_df.iloc[-1]
        latest_ts = latest_row["ts"]
        latest_close = float(latest_row["close"])

        cutoff_20d = latest_ts - timedelta(days=20)
        recent_20 = symbol_df[symbol_df["ts"] >= cutoff_20d].copy()
        if recent_20.empty:
            recent_20 = symbol_df.tail(20).copy()

        low_idx = recent_20["close"].idxmin()
        low_row = recent_20.loc[low_idx]
        low_ts = low_row["ts"]
        low_close = float(low_row["close"])

        high_idx = recent_20["close"].idxmax()
        high_row = recent_20.loc[high_idx]
        high_ts = high_row["ts"]
        high_close = float(high_row["close"])

        is_latest_20d_low = latest_close <= low_close
        latest_color = "#d62728" if is_latest_20d_low else "#2ca02c"

        ax.scatter([low_ts], [low_close], color="#ff7f0e", s=70, zorder=6)
        ax.scatter([high_ts], [high_close], color="#9467bd", s=70, zorder=6)
        ax.scatter([latest_ts], [latest_close], color=latest_color, s=85, zorder=7)
        ax.axvline(cutoff_20d, color="#6c757d", linestyle="--", linewidth=1.4)

        low_flag = "LOW20" if is_latest_20d_low else ""
        display_name = ""
        if name_map:
            display_name = name_map.get(symbol, "").strip()
        title_parts = [symbol]
        if display_name:
            title_parts.append(display_name)
        if low_flag:
            title_parts.append(low_flag)
        ax.set_title(" ".join(title_parts))
        ax.set_xlabel("Date")
        ax.set_ylabel("Close")
        ax.tick_params(axis="x", rotation=30)

    for idx in range(len(market_symbols), len(axes_list)):
        axes_list[idx].set_axis_off()

    fig.suptitle(f"{market_name.upper()} - 3M Close Price Grid", fontsize=16)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    output_path = output_dir / f"market_{market_name}.png"
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path
