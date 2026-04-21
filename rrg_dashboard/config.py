from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
EXPORTS_DIR = OUTPUTS_DIR / "exports"


@dataclass(frozen=True)
class RRGConfig:
    benchmark_symbol: str = "^NSEI"
    tail_periods: int = 10
    roc_period: int = 14
    zscore_window: int = 20
    ma_window: int = 200
    breakout_window: int = 55


DEFAULT_CONFIG = RRGConfig()


SECTOR_INDEX_UNIVERSE = {
    "Nifty Bank": "^NSEBANK",
    "Nifty IT": "^NSEIT",
    "Nifty Auto": "^NSEAUTO",
    "Nifty FMCG": "^NSEFMCG",
    "Nifty Pharma": "^NSEPHARMA",
}


SECTOR_STOCK_UNIVERSE = {
    "^NSEBANK": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS", "KOTAKBANK.NS", "INDUSINDBK.NS"],
    "^NSEIT": ["INFY.NS", "TCS.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS", "LTIM.NS"],
    "^NSEAUTO": ["MARUTI.NS", "TATAMOTORS.NS", "M&M.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS", "HEROMOTOCO.NS"],
    "^NSEFMCG": ["HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS", "BRITANNIA.NS", "DABUR.NS", "GODREJCP.NS"],
    "^NSEPHARMA": ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "LUPIN.NS", "TORNTPHARM.NS"],
}


NIFTY_STOCK_SEARCH_UNIVERSE = [
    "ADANIENT.NS",
    "ADANIPORTS.NS",
    "APOLLOHOSP.NS",
    "ASIANPAINT.NS",
    "AXISBANK.NS",
    "BAJAJ-AUTO.NS",
    "BAJAJFINSV.NS",
    "BAJFINANCE.NS",
    "BEL.NS",
    "BHARTIARTL.NS",
    "CIPLA.NS",
    "COALINDIA.NS",
    "DRREDDY.NS",
    "EICHERMOT.NS",
    "ETERNAL.NS",
    "GRASIM.NS",
    "HCLTECH.NS",
    "HDFCBANK.NS",
    "HDFCLIFE.NS",
    "HINDALCO.NS",
    "HINDUNILVR.NS",
    "ICICIBANK.NS",
    "INDIGO.NS",
    "INFY.NS",
    "ITC.NS",
    "JSWSTEEL.NS",
    "KOTAKBANK.NS",
    "LT.NS",
    "M&M.NS",
    "MARUTI.NS",
    "NESTLEIND.NS",
    "NTPC.NS",
    "ONGC.NS",
    "POWERGRID.NS",
    "RELIANCE.NS",
    "SBIN.NS",
    "SHRIRAMFIN.NS",
    "SUNPHARMA.NS",
    "TATACONSUM.NS",
    "TCS.NS",
    "TECHM.NS",
    "TITAN.NS",
    "TRENT.NS",
    "ULTRACEMCO.NS",
    "WIPRO.NS",
]


def build_stock_to_sector_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for sector_symbol, symbols in SECTOR_STOCK_UNIVERSE.items():
        for symbol in symbols:
            mapping[symbol] = sector_symbol
    return mapping


STOCK_TO_SECTOR = build_stock_to_sector_map()
