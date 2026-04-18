from __future__ import annotations

from datetime import date

import pandas as pd
import yfinance as yf


def fetch_price_history(symbols: list[str], period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    unique_symbols = list(dict.fromkeys([symbol for symbol in symbols if symbol]))
    if not unique_symbols:
        return pd.DataFrame()

    frame = yf.download(
        tickers=unique_symbols,
        period=period,
        interval=interval,
        auto_adjust=True,
        progress=False,
        threads=True,
    )

    if frame.empty:
        return pd.DataFrame()

    if isinstance(frame.columns, pd.MultiIndex):
      if "Close" in frame.columns.get_level_values(0):
          close_frame = frame["Close"].copy()
      else:
          close_frame = frame.xs("Close", axis=1, level=-1, drop_level=False)
    else:
      close_frame = frame[["Close"]].rename(columns={"Close": unique_symbols[0]})

    close_frame = close_frame.dropna(how="all")
    close_frame.index = pd.to_datetime(close_frame.index).tz_localize(None)
    close_frame = close_frame.sort_index()

    if isinstance(close_frame, pd.Series):
        close_frame = close_frame.to_frame(name=unique_symbols[0])

    return close_frame


def latest_available_date(price_frame: pd.DataFrame) -> date | None:
    if price_frame.empty:
        return None
    return price_frame.index.max().date()
