from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

RRG_SNAPSHOT_COLUMNS = [
    "symbol",
    "label",
    "rs_ratio",
    "rs_momentum",
    "quadrant",
    "score",
    "tail_x",
    "tail_y",
    "tail_dates",
    "close",
]


def compute_relative_strength(asset_prices: pd.DataFrame, benchmark_series: pd.Series) -> pd.DataFrame:
    aligned_prices, aligned_benchmark = asset_prices.align(benchmark_series, join="inner", axis=0)
    return aligned_prices.divide(aligned_benchmark, axis=0).replace([np.inf, -np.inf], np.nan)


def compute_rs_momentum(rs_frame: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    return rs_frame.pct_change(period)


def rolling_zscore(frame: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    rolling_mean = frame.rolling(window=window, min_periods=max(5, window // 2)).mean()
    rolling_std = frame.rolling(window=window, min_periods=max(5, window // 2)).std(ddof=0)
    z = (frame - rolling_mean) / rolling_std.replace(0, np.nan)
    return z.replace([np.inf, -np.inf], np.nan)


def classify_quadrant(rs_ratio: float, rs_momentum: float) -> str:
    if rs_ratio >= 0 and rs_momentum >= 0:
        return "Leading"
    if rs_ratio >= 0 and rs_momentum < 0:
        return "Weakening"
    if rs_ratio < 0 and rs_momentum < 0:
        return "Lagging"
    return "Improving"


def build_rrg_snapshot(
    price_frame: pd.DataFrame,
    benchmark_symbol: str,
    tail_periods: int = 10,
    roc_period: int = 14,
    zscore_window: int = 20,
    labels: dict[str, str] | None = None,
) -> pd.DataFrame:
    if price_frame.empty or benchmark_symbol not in price_frame.columns:
        return pd.DataFrame()

    working = price_frame.dropna(how="all")
    benchmark = working[benchmark_symbol].dropna()
    assets = working.drop(columns=[benchmark_symbol], errors="ignore")
    assets = assets.dropna(axis=1, how="all")
    if assets.empty:
        return pd.DataFrame()

    rs = compute_relative_strength(assets, benchmark)
    momentum = compute_rs_momentum(rs, period=roc_period)
    rs_ratio = rolling_zscore(rs, window=zscore_window)
    rs_momentum = rolling_zscore(momentum, window=zscore_window)

    rows: list[dict] = []
    for symbol in assets.columns:
        ratio_series = rs_ratio[symbol].dropna()
        momentum_series = rs_momentum[symbol].dropna()
        common_index = ratio_series.index.intersection(momentum_series.index)
        if len(common_index) < max(4, tail_periods):
            continue

        ratio_series = ratio_series.loc[common_index]
        momentum_series = momentum_series.loc[common_index]
        tail_index = common_index[-tail_periods:]
        latest_x = float(ratio_series.iloc[-1])
        latest_y = float(momentum_series.iloc[-1])

        rows.append(
            {
                "symbol": symbol,
                "label": labels.get(symbol, symbol) if labels else symbol,
                "rs_ratio": latest_x,
                "rs_momentum": latest_y,
                "quadrant": classify_quadrant(latest_x, latest_y),
                "score": latest_x + latest_y,
                "tail_x": ratio_series.loc[tail_index].tolist(),
                "tail_y": momentum_series.loc[tail_index].tolist(),
                "tail_dates": [index.strftime("%Y-%m-%d") for index in tail_index],
                "close": float(assets[symbol].dropna().iloc[-1]),
            }
        )

    if not rows:
        return pd.DataFrame(columns=RRG_SNAPSHOT_COLUMNS)

    return pd.DataFrame(rows, columns=RRG_SNAPSHOT_COLUMNS).sort_values(
        ["quadrant", "score"], ascending=[True, False]
    ).reset_index(drop=True)
