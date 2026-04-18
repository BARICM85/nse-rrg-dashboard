from __future__ import annotations

import os
from dataclasses import dataclass

import pandas as pd


try:
    from kiteconnect import KiteConnect
except Exception:  # pragma: no cover - optional dependency at runtime
    KiteConnect = None


@dataclass
class KiteGateway:
    mode: str
    note: str
    client: object | None = None
    api_key: str | None = None

    @classmethod
    def from_environment(cls) -> "KiteGateway":
        return cls.from_credentials(
            api_key=os.getenv("KITE_API_KEY", "").strip(),
            access_token=os.getenv("KITE_ACCESS_TOKEN", "").strip(),
        )

    @classmethod
    def from_credentials(cls, api_key: str = "", access_token: str = "") -> "KiteGateway":
        api_key = api_key.strip()
        access_token = access_token.strip()

        if not api_key or not access_token or KiteConnect is None:
            return cls(
                mode="mock",
                note="Kite SDK or credentials unavailable; dashboard stays in analytics-first mode.",
                client=None,
                api_key=api_key or None,
            )

        client = KiteConnect(api_key=api_key)
        client.set_access_token(access_token)
        return cls(
            mode="live",
            note="Live Kite session available for future portfolio-linked extensions.",
            client=client,
            api_key=api_key,
        )

    def describe(self) -> dict:
        payload = {
            "mode": self.mode,
            "note": self.note,
        }
        if self.mode == "live":
            payload["capabilities"] = [
                "holdings context",
                "positions context",
                "future live workflow integration",
            ]
        else:
            payload["capabilities"] = [
                "mock watchlist context",
                "analytics without broker dependency",
            ]
        return payload

    def fetch_holdings(self) -> pd.DataFrame:
        if self.mode != "live" or self.client is None:
            return pd.DataFrame()

        try:
            holdings = self.client.holdings() or []
        except Exception:
            return pd.DataFrame()

        rows = []
        for item in holdings:
            symbol = str(item.get("tradingsymbol") or "").strip().upper()
            exchange = str(item.get("exchange") or "NSE").strip().upper() or "NSE"
            if not symbol:
                continue

            rows.append(
                {
                    "symbol": symbol,
                    "exchange": exchange,
                    "yfinance_symbol": to_yfinance_symbol(symbol, exchange),
                    "quantity": float(item.get("quantity") or 0),
                    "average_price": float(item.get("average_price") or 0),
                    "last_price": float(item.get("last_price") or item.get("close_price") or 0),
                    "pnl": float(item.get("pnl") or 0),
                    "product": item.get("product") or "",
                    "isin": item.get("isin") or "",
                    "company_name": item.get("tradingsymbol") or symbol,
                }
            )

        return pd.DataFrame(rows)


def to_yfinance_symbol(symbol: str, exchange: str = "NSE") -> str:
    normalized_symbol = str(symbol or "").strip().upper()
    normalized_exchange = str(exchange or "NSE").strip().upper()
    if not normalized_symbol:
        return ""
    if normalized_exchange == "BSE":
        return f"{normalized_symbol}.BO"
    return f"{normalized_symbol}.NS"
