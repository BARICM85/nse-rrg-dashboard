from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from .rrg import build_rrg_snapshot


def compute_ma_filter(price_frame: pd.DataFrame, window: int = 200) -> pd.Series:
    moving_average = price_frame.rolling(window=window, min_periods=max(20, window // 4)).mean()
    latest_close = price_frame.iloc[-1]
    latest_ma = moving_average.iloc[-1]
    return latest_close > latest_ma


def compute_breakout_flags(price_frame: pd.DataFrame, window: int = 55) -> pd.Series:
    breakout_ceiling = price_frame.shift(1).rolling(window=window, min_periods=max(20, window // 3)).max()
    latest_close = price_frame.iloc[-1]
    latest_ceiling = breakout_ceiling.iloc[-1]
    return latest_close >= latest_ceiling


def build_sector_stock_snapshot(sector_symbol: str, sector_prices: pd.DataFrame, config) -> pd.DataFrame:
    if sector_prices.empty or sector_symbol not in sector_prices.columns:
        return pd.DataFrame()

    snapshot = build_rrg_snapshot(
        price_frame=sector_prices,
        benchmark_symbol=sector_symbol,
        tail_periods=config.tail_periods,
        roc_period=config.roc_period,
        zscore_window=config.zscore_window,
    )
    if snapshot.empty:
        return snapshot

    stock_only = sector_prices.drop(columns=[sector_symbol], errors="ignore").dropna(axis=1, how="all")
    if stock_only.empty:
        return snapshot.iloc[0:0]

    ma_filter = compute_ma_filter(stock_only, window=config.ma_window)
    breakout_flags = compute_breakout_flags(stock_only, window=config.breakout_window)

    snapshot["above_200dma"] = snapshot["symbol"].map(lambda symbol: bool(ma_filter.get(symbol, False)))
    snapshot["breakout"] = snapshot["symbol"].map(lambda symbol: bool(breakout_flags.get(symbol, False)))
    snapshot["sector_symbol"] = sector_symbol
    return snapshot


def rank_top_stock_candidates(
    sector_snapshot: pd.DataFrame,
    sector_price_fetcher: Callable[[str], pd.DataFrame],
    stock_universe: dict[str, list[str]],
    config,
    limit: int = 5,
) -> pd.DataFrame:
    if sector_snapshot.empty:
        return pd.DataFrame()

    leading_sectors = sector_snapshot.loc[sector_snapshot["quadrant"] == "Leading"].sort_values("score", ascending=False)
    candidates: list[pd.DataFrame] = []

    for _, sector_row in leading_sectors.iterrows():
        sector_symbol = sector_row["symbol"]
        if not stock_universe.get(sector_symbol):
            continue

        prices = sector_price_fetcher(sector_symbol)
        stock_snapshot = build_sector_stock_snapshot(sector_symbol=sector_symbol, sector_prices=prices, config=config)
        if stock_snapshot.empty:
            continue

        stock_snapshot = stock_snapshot.assign(
            sector_name=sector_row["label"],
            sector_quadrant=sector_row["quadrant"],
        )
        candidates.append(stock_snapshot)

    if not candidates:
        return pd.DataFrame()

    candidate_frame = pd.concat(candidates, ignore_index=True)
    filtered = candidate_frame.loc[
        candidate_frame["quadrant"].isin(["Leading", "Improving"])
        & candidate_frame["above_200dma"]
    ].copy()
    if filtered.empty:
        filtered = candidate_frame.copy()

    filtered["score"] = (
        filtered["rs_ratio"] * 0.6
        + filtered["rs_momentum"] * 0.4
        + filtered["breakout"].astype(int) * 2.0
        + filtered["above_200dma"].astype(int) * 1.0
    )

    return filtered.sort_values("score", ascending=False).head(limit).reset_index(drop=True)


def filter_snapshot_for_watchlist(snapshot: pd.DataFrame, watchlist_symbols: list[str]) -> pd.DataFrame:
    if snapshot.empty or not watchlist_symbols:
        return pd.DataFrame()
    symbol_set = set(watchlist_symbols)
    return snapshot.loc[snapshot["symbol"].isin(symbol_set)].reset_index(drop=True)
