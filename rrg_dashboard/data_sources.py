from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parents[1]
YFINANCE_CACHE_DIR = PROJECT_ROOT / ".cache" / "py-yfinance"
YFINANCE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
yf.set_tz_cache_location(str(YFINANCE_CACHE_DIR))


def _extract_close_frame(frame: pd.DataFrame, symbol_hint: str | None = None) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()

    if isinstance(frame.columns, pd.MultiIndex):
        if "Close" in frame.columns.get_level_values(0):
            close_frame = frame["Close"].copy()
        else:
            close_frame = frame.xs("Close", axis=1, level=-1, drop_level=False)
    else:
        close_frame = frame[["Close"]].rename(columns={"Close": symbol_hint or "Close"})

    close_frame = close_frame.dropna(how="all")
    close_frame.index = pd.to_datetime(close_frame.index).tz_localize(None)
    close_frame = close_frame.sort_index()

    if isinstance(close_frame, pd.Series):
        close_frame = close_frame.to_frame(name=symbol_hint or "Close")

    return close_frame


def fetch_price_history(symbols: list[str], period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    unique_symbols = list(dict.fromkeys([symbol for symbol in symbols if symbol]))
    if not unique_symbols:
        return pd.DataFrame()

    try:
        frame = yf.download(
            tickers=unique_symbols,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,
            threads=False,
            group_by="column",
        )
        close_frame = _extract_close_frame(frame, symbol_hint=unique_symbols[0])
    except Exception:
        close_frame = pd.DataFrame()

    missing_symbols = [symbol for symbol in unique_symbols if symbol not in close_frame.columns] if not close_frame.empty else unique_symbols

    if missing_symbols:
        fallback_frames: list[pd.DataFrame] = []
        for symbol in missing_symbols:
            try:
                single_frame = yf.download(
                    tickers=symbol,
                    period=period,
                    interval=interval,
                    auto_adjust=True,
                    progress=False,
                    threads=False,
                    group_by="column",
                )
                single_close = _extract_close_frame(single_frame, symbol_hint=symbol)
                if not single_close.empty:
                    fallback_frames.append(single_close.rename(columns={single_close.columns[0]: symbol}))
            except Exception:
                continue

        if fallback_frames:
            fallback_close_frame = pd.concat(fallback_frames, axis=1).dropna(how="all")
            if close_frame.empty:
                close_frame = fallback_close_frame
            else:
                close_frame = pd.concat([close_frame, fallback_close_frame], axis=1)
                close_frame = close_frame.loc[:, ~close_frame.columns.duplicated()]

    return close_frame.dropna(how="all")


def latest_available_date(price_frame: pd.DataFrame) -> date | None:
    if price_frame.empty:
        return None
    return price_frame.index.max().date()
