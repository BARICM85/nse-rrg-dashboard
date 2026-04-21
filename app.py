from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Iterable

import pandas as pd
import streamlit as st

from rrg_dashboard.charts import build_rrg_figure
from rrg_dashboard.config import (
    DEFAULT_CONFIG,
    EXPORTS_DIR,
    NIFTY_STOCK_SEARCH_UNIVERSE,
    OUTPUTS_DIR,
    SECTOR_INDEX_UNIVERSE,
    SECTOR_STOCK_UNIVERSE,
    STOCK_TO_SECTOR,
)
from rrg_dashboard.data_sources import fetch_price_history
from rrg_dashboard.exports import save_dataframe_as_pdf, save_dataframe_as_png
from rrg_dashboard.kite_adapter import KiteGateway
from rrg_dashboard.rrg import build_rrg_snapshot
from rrg_dashboard.screening import (
    build_sector_stock_snapshot,
    compute_breakout_flags,
    compute_ma_filter,
    filter_snapshot_for_watchlist,
    rank_top_stock_candidates,
)


st.set_page_config(page_title="NSE RRG Dashboard", layout="wide")


@st.cache_data(show_spinner=False, ttl=60 * 30)
def load_prices(symbols: list[str], period: str) -> pd.DataFrame:
    return fetch_price_history(symbols, period=period)


def save_chart(fig, filename: str) -> Path:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUTS_DIR / filename
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    return output_path


def unique_preserve_order(items: Iterable[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def bootstrap_state() -> None:
    st.session_state.setdefault("rrg_holdings", pd.DataFrame())
    st.session_state.setdefault("rrg_watchlist_symbols", [])
    st.session_state.setdefault("rrg_export_messages", [])


def display_symbol(symbol: str) -> str:
    if not symbol:
        return ""
    if symbol.startswith("^"):
        return symbol.replace("^", "")
    for suffix in (".NS", ".BO"):
        if symbol.endswith(suffix):
            return symbol[: -len(suffix)]
    return symbol


def build_equal_weight_basket(price_frame: pd.DataFrame, symbols: list[str], basket_symbol: str = "__SECTOR_BASKET__") -> pd.DataFrame:
    basket_parts: list[pd.Series] = []
    for symbol in symbols:
        if symbol not in price_frame.columns:
            continue
        series = price_frame[symbol].dropna()
        if len(series) < 2:
            continue
        basket_parts.append((series / float(series.iloc[0])).rename(symbol))

    if not basket_parts:
        return pd.DataFrame()

    basket_frame = pd.concat(basket_parts, axis=1).dropna(how="all")
    basket_series = basket_frame.mean(axis=1).rename(basket_symbol)
    return pd.concat([price_frame[symbols], basket_series], axis=1).dropna(how="all")


def render_status_card(title: str, value: str, note: str) -> None:
    st.markdown(
        f"""
        <div style="padding:0.9rem 1rem;border:1px solid rgba(15,23,42,0.12);border-radius:18px;background:#f8fafc;">
          <div style="font-size:0.78rem;text-transform:uppercase;letter-spacing:0.12em;color:#64748b;">{title}</div>
          <div style="margin-top:0.4rem;font-size:1.3rem;font-weight:700;color:#0f172a;">{value}</div>
          <div style="margin-top:0.3rem;font-size:0.88rem;color:#475569;">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    bootstrap_state()
    st.title("NSE Relative Rotation Graph Dashboard")
    st.caption("Sector rotation, stock rotation inside sectors, and semi-ready candidate discovery for the Indian market.")

    with st.sidebar:
        st.header("Controls")
        period = st.selectbox("History period", options=["6mo", "1y", "2y"], index=1)
        tail_periods = st.slider("Tail length", min_value=5, max_value=20, value=DEFAULT_CONFIG.tail_periods)
        roc_period = st.slider("RS momentum period", min_value=5, max_value=30, value=DEFAULT_CONFIG.roc_period)
        zscore_window = st.slider("Z-score window", min_value=10, max_value=60, value=DEFAULT_CONFIG.zscore_window)
        breakout_window = st.slider("Breakout lookback", min_value=20, max_value=100, value=DEFAULT_CONFIG.breakout_window)
        max_stocks = st.slider("Top stocks to show", min_value=3, max_value=10, value=5)

        st.divider()
        st.subheader("Kite Connect")
        api_key_input = st.text_input("Kite API key", value="", placeholder="Optional if already set in env")
        access_token_input = st.text_input("Kite access token", value="", type="password", placeholder="Optional if already set in env")

    config = replace(
        DEFAULT_CONFIG,
        tail_periods=tail_periods,
        roc_period=roc_period,
        zscore_window=zscore_window,
        breakout_window=breakout_window,
    )

    gateway = KiteGateway.from_credentials(api_key=api_key_input, access_token=access_token_input)
    if gateway.mode == "mock":
        env_gateway = KiteGateway.from_environment()
        if env_gateway.mode == "live":
            gateway = env_gateway

    with st.sidebar:
        if st.button("Import Zerodha holdings", use_container_width=True):
            holdings_frame = gateway.fetch_holdings()
            st.session_state["rrg_holdings"] = holdings_frame
            if holdings_frame.empty:
                st.warning("No Zerodha holdings were returned. Check Kite credentials or access token.")
            else:
                imported_symbols = unique_preserve_order(holdings_frame["yfinance_symbol"].tolist())
                st.session_state["rrg_watchlist_symbols"] = unique_preserve_order(
                    st.session_state["rrg_watchlist_symbols"] + imported_symbols
                )
                st.success(f"Imported {len(holdings_frame)} holdings from Zerodha.")

    holdings_frame = st.session_state["rrg_holdings"]
    imported_holding_symbols = unique_preserve_order(holdings_frame.get("yfinance_symbol", pd.Series(dtype=str)).tolist()) if not holdings_frame.empty else []

    benchmark = config.benchmark_symbol
    sector_symbols = list(SECTOR_INDEX_UNIVERSE.values())
    sector_labels = {value: key for key, value in SECTOR_INDEX_UNIVERSE.items()}
    tracked_stock_symbols = unique_preserve_order(
        [symbol for sector_symbols_list in SECTOR_STOCK_UNIVERSE.values() for symbol in sector_symbols_list]
    )
    stock_search_options = unique_preserve_order(NIFTY_STOCK_SEARCH_UNIVERSE + tracked_stock_symbols + imported_holding_symbols)
    sector_prices = load_prices([benchmark, *sector_symbols], period=period)
    sector_snapshot = build_rrg_snapshot(
        price_frame=sector_prices,
        benchmark_symbol=benchmark,
        tail_periods=config.tail_periods,
        roc_period=config.roc_period,
        zscore_window=config.zscore_window,
        labels=sector_labels,
    )

    if sector_snapshot.empty:
        st.error("No sector data could be loaded. Check network access or data provider response.")
        return

    leading_sector_rows = sector_snapshot.loc[sector_snapshot["quadrant"] == "Leading"].copy()
    sector_comparison_selection = st.multiselect(
        "Sector rotation comparison set",
        options=sector_symbols,
        default=sector_symbols,
        format_func=lambda symbol: sector_labels.get(symbol, symbol),
        help="Choose which sectors to include in the sector rotation graph.",
    )
    sector_rotation_mode = st.radio(
        "Sector rotation benchmark",
        options=["NIFTY 50", "Equal-weight sector basket"],
        horizontal=True,
        help="Compare selected sectors against NIFTY 50 or against their own equal-weight basket.",
    )
    if not sector_comparison_selection:
        sector_comparison_selection = sector_symbols

    selected_sector_prices = sector_prices[[benchmark, *sector_comparison_selection]].copy()
    if sector_rotation_mode == "Equal-weight sector basket" and len(sector_comparison_selection) >= 2:
        sector_rotation_prices = build_equal_weight_basket(selected_sector_prices, sector_comparison_selection)
        sector_rotation_snapshot = build_rrg_snapshot(
            price_frame=sector_rotation_prices,
            benchmark_symbol="__SECTOR_BASKET__",
            tail_periods=config.tail_periods,
            roc_period=config.roc_period,
            zscore_window=config.zscore_window,
            labels=sector_labels,
        )
        sector_rotation_title = "Sector Relative Rotation vs equal-weight sector basket"
    else:
        sector_rotation_snapshot = build_rrg_snapshot(
            price_frame=selected_sector_prices,
            benchmark_symbol=benchmark,
            tail_periods=config.tail_periods,
            roc_period=config.roc_period,
            zscore_window=config.zscore_window,
            labels=sector_labels,
        )
        sector_rotation_title = "Sector Relative Rotation vs NIFTY 50"

    selected_sector_symbol = st.selectbox(
        "Sector for stock-level RRG",
        options=sector_symbols,
        index=0,
        format_func=lambda symbol: sector_labels.get(symbol, symbol),
    )
    selected_sector_name = sector_labels.get(selected_sector_symbol, selected_sector_symbol)
    selected_sector_stocks = SECTOR_STOCK_UNIVERSE.get(selected_sector_symbol, [])
    stock_prices = load_prices([selected_sector_symbol, *selected_sector_stocks], period=period)
    stock_snapshot = build_sector_stock_snapshot(
        sector_symbol=selected_sector_symbol,
        sector_prices=stock_prices,
        config=config,
    )
    stock_search_symbol = st.selectbox(
        "NIFTY stock search in RRG",
        options=stock_search_options,
        index=stock_search_options.index("INFY.NS") if "INFY.NS" in stock_search_options else 0,
        format_func=display_symbol,
        help="Track an individual stock against NIFTY 50, even if it is outside the currently selected sector pane.",
    )
    stock_search_prices = load_prices([benchmark, stock_search_symbol], period=period)
    stock_search_snapshot = build_rrg_snapshot(
        price_frame=stock_search_prices,
        benchmark_symbol=benchmark,
        tail_periods=config.tail_periods,
        roc_period=config.roc_period,
        zscore_window=config.zscore_window,
        labels={stock_search_symbol: display_symbol(stock_search_symbol)},
    )
    searched_stock_sector = STOCK_TO_SECTOR.get(stock_search_symbol)
    searched_stock_sector_name = sector_labels.get(searched_stock_sector, "Broader NIFTY search universe")
    stock_search_frame = stock_search_prices.drop(columns=[benchmark], errors="ignore")
    search_above_200dma = False
    search_breakout = False
    if not stock_search_frame.empty:
        search_above_200dma = bool(compute_ma_filter(stock_search_frame, window=config.ma_window).get(stock_search_symbol, False))
        search_breakout = bool(compute_breakout_flags(stock_search_frame, window=config.breakout_window).get(stock_search_symbol, False))

    top_candidates = rank_top_stock_candidates(
        sector_snapshot=sector_snapshot,
        sector_price_fetcher=lambda symbol: load_prices([symbol, *SECTOR_STOCK_UNIVERSE.get(symbol, [])], period=period),
        stock_universe=SECTOR_STOCK_UNIVERSE,
        config=config,
        limit=max_stocks,
    )
    kite_context = gateway.describe()
    candidate_symbols = unique_preserve_order(top_candidates.get("symbol", pd.Series(dtype=str)).tolist()) if not top_candidates.empty else []
    watchlist_options = unique_preserve_order(imported_holding_symbols + candidate_symbols)

    current_watchlist = st.session_state["rrg_watchlist_symbols"]
    st.session_state["rrg_watchlist_symbols"] = st.multiselect(
        "Active watchlist",
        options=watchlist_options,
        default=[symbol for symbol in current_watchlist if symbol in watchlist_options],
        help="Seeded from imported Zerodha holdings and current top candidates.",
    )
    active_watchlist_symbols = st.session_state["rrg_watchlist_symbols"]

    watchlist_snapshots: list[pd.DataFrame] = []
    for sector_symbol, sector_stock_symbols in SECTOR_STOCK_UNIVERSE.items():
        sector_watchlist = [symbol for symbol in active_watchlist_symbols if symbol in sector_stock_symbols]
        if not sector_watchlist:
            continue
        prices = load_prices([sector_symbol, *sector_watchlist], period=period)
        sector_watchlist_snapshot = build_sector_stock_snapshot(sector_symbol=sector_symbol, sector_prices=prices, config=config)
        if not sector_watchlist_snapshot.empty:
            sector_watchlist_snapshot["sector_name"] = sector_labels.get(sector_symbol, sector_symbol)
            watchlist_snapshots.append(filter_snapshot_for_watchlist(sector_watchlist_snapshot, sector_watchlist))

    watchlist_snapshot = pd.concat(watchlist_snapshots, ignore_index=True) if watchlist_snapshots else pd.DataFrame()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_status_card("Benchmark", benchmark, "Primary market reference")
    with col2:
        render_status_card("Leading sectors", str(len(leading_sector_rows)), "Current sectors in the leading quadrant")
    with col3:
        render_status_card("Stock universe", str(sum(len(items) for items in SECTOR_STOCK_UNIVERSE.values())), "Tracked stocks across configured sectors")
    with col4:
        render_status_card("Kite mode", kite_context["mode"], kite_context["note"])

    if not holdings_frame.empty:
        with st.expander("Imported Zerodha portfolio", expanded=False):
            st.dataframe(holdings_frame, use_container_width=True, hide_index=True)

    if st.session_state["rrg_export_messages"]:
        for message in st.session_state["rrg_export_messages"]:
            st.success(message)
        st.session_state["rrg_export_messages"] = []

    sector_chart_col, sector_table_col = st.columns([1.4, 1.0], gap="large")
    with sector_chart_col:
        st.subheader("Sector rotation")
        sector_fig = build_rrg_figure(
            snapshot=sector_rotation_snapshot,
            title=sector_rotation_title,
            tail_periods=config.tail_periods,
        )
        st.pyplot(sector_fig, use_container_width=True)
        if st.button("Save sector chart PNG"):
            output = save_chart(sector_fig, "sector_rrg.png")
            st.success(f"Saved to {output}")

    with sector_table_col:
        st.subheader("Sector quadrant status")
        sector_table = sector_rotation_snapshot[
            ["label", "quadrant", "rs_ratio", "rs_momentum", "score"]
        ].rename(
            columns={
                "label": "Sector",
                "quadrant": "Quadrant",
                "rs_ratio": "RS Ratio",
                "rs_momentum": "RS Momentum",
                "score": "Score",
            }
        )
        st.dataframe(sector_table, use_container_width=True, hide_index=True)

    stock_col, search_col, ideas_col = st.columns([1.2, 1.0, 1.0], gap="large")
    with stock_col:
        st.subheader(f"Stock RRG inside {selected_sector_name}")
        if stock_snapshot.empty:
            st.info("No stock snapshot available for this sector yet.")
        else:
            stock_fig = build_rrg_figure(
                snapshot=stock_snapshot,
                title=f"Stock rotation inside {selected_sector_name}",
                tail_periods=config.tail_periods,
            )
            st.pyplot(stock_fig, use_container_width=True)
            if st.button("Save stock chart PNG"):
                output = save_chart(stock_fig, f"{selected_sector_symbol.replace('^', '')}_stock_rrg.png")
                st.success(f"Saved to {output}")

    with search_col:
        st.subheader(f"NIFTY stock search: {display_symbol(stock_search_symbol)}")
        if stock_search_snapshot.empty:
            st.info("This stock does not have enough clean history yet to build an RRG trail.")
        else:
            search_fig = build_rrg_figure(
                snapshot=stock_search_snapshot,
                title=f"{display_symbol(stock_search_symbol)} vs NIFTY 50",
                tail_periods=config.tail_periods,
            )
            st.pyplot(search_fig, use_container_width=True)
            latest_row = stock_search_snapshot.iloc[0]
            st.caption(f"Mapped sector context: {searched_stock_sector_name}")
            search_metric_col1, search_metric_col2 = st.columns(2)
            with search_metric_col1:
                st.metric("Quadrant", latest_row["quadrant"])
                st.metric("Above 200 DMA", "Yes" if search_above_200dma else "No")
            with search_metric_col2:
                st.metric("RS Score", f'{latest_row["score"]:.2f}')
                st.metric("Breakout", "Yes" if search_breakout else "No")

    with ideas_col:
        st.subheader("Top stocks to buy")
        if top_candidates.empty:
            st.info("No current candidates passed the sector and stock filters.")
        else:
            display = top_candidates[
                ["sector_name", "symbol", "quadrant", "close", "above_200dma", "breakout", "score"]
            ].rename(
                columns={
                    "sector_name": "Sector",
                    "symbol": "Stock",
                    "quadrant": "Quadrant",
                    "close": "Close",
                    "above_200dma": "Above 200 DMA",
                    "breakout": "Breakout",
                    "score": "Score",
                }
            )
            st.dataframe(display, use_container_width=True, hide_index=True)

            export_col1, export_col2 = st.columns(2)
            with export_col1:
                if st.button("Export buy list PNG", use_container_width=True):
                    path = save_dataframe_as_png(display, "Top Stocks To Buy", EXPORTS_DIR / "top_stocks_to_buy.png")
                    st.session_state["rrg_export_messages"] = [f"PNG export saved to {path}"]
                    st.rerun()
            with export_col2:
                if st.button("Export buy list PDF", use_container_width=True):
                    path = save_dataframe_as_pdf(display, "Top Stocks To Buy", EXPORTS_DIR / "top_stocks_to_buy.pdf")
                    st.session_state["rrg_export_messages"] = [f"PDF export saved to {path}"]
                    st.rerun()

    st.subheader("Current watchlist quadrant status")
    if watchlist_snapshot.empty:
        st.info("No watchlist symbols are active yet. Import Zerodha holdings or select symbols from the watchlist selector.")
    else:
        watchlist_display = watchlist_snapshot[
            ["sector_name", "symbol", "quadrant", "rs_ratio", "rs_momentum", "above_200dma", "breakout", "score"]
        ].rename(
            columns={
                "sector_name": "Sector",
                "symbol": "Stock",
                "quadrant": "Quadrant",
                "rs_ratio": "RS Ratio",
                "rs_momentum": "RS Momentum",
                "above_200dma": "Above 200 DMA",
                "breakout": "Breakout",
                "score": "Score",
            }
        )
        st.dataframe(watchlist_display, use_container_width=True, hide_index=True)

    with st.expander("Kite Connect context", expanded=False):
        st.json(kite_context)

    with st.expander("Terminal README", expanded=False):
        st.markdown(
            """
            ### How to read this dashboard
            - **Leading**: strong relative strength and improving momentum
            - **Weakening**: strong relative strength but momentum fading
            - **Lagging**: weak strength and weak momentum
            - **Improving**: weak strength but momentum is recovering

            ### Candidate logic
            1. Sector must be leading
            2. Stock should be in Leading or Improving
            3. Stock should be above 200 DMA
            4. Breakouts receive a ranking boost
            5. RRG score combines RS ratio and momentum

            ### Notes
            - Sector RRG uses `^NSEI` as the benchmark
            - Sector comparison can also rotate selected sectors against an equal-weight sector basket
            - Stock RRG inside a sector uses the sector index as the baseline
            - NIFTY stock search plots an individual stock directly against NIFTY 50
            - Zerodha holdings import seeds the dashboard portfolio and watchlist
            - Buy-list exports are saved as both PNG and PDF
            - Zerodha adapter is included for live workflow extension and currently supports mock fallback
            """
        )


if __name__ == "__main__":
    main()
