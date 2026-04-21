from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from rrg_dashboard.charts import build_rrg_figure
from rrg_dashboard.config import DEFAULT_CONFIG, ETF_UNIVERSE, NIFTY_STOCK_SEARCH_UNIVERSE, OUTPUTS_DIR, SECTOR_INDEX_UNIVERSE
from rrg_dashboard.data_sources import fetch_price_history, latest_available_date
from rrg_dashboard.rrg import build_rrg_snapshot


st.set_page_config(page_title="Relative Rotation Graph", layout="wide")


BENCHMARK_OPTIONS = {
    "Nifty 50": "^NSEI",
    "Nifty 500": "^CRSLDX",
}

WATCHLIST_ROW_COLORS = ["#e8f5e9", "#fff8db", "#efe8ff", "#fdecec", "#e8f0ff", "#eaf7f7"]


@st.cache_data(show_spinner=False, ttl=60 * 30)
def load_prices(symbols: list[str], period: str, interval: str):
    return fetch_price_history(symbols, period=period, interval=interval)


def save_chart(fig, filename: str) -> Path:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUTS_DIR / filename
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    return output_path


def build_demo_snapshot(symbols: list[str]) -> pd.DataFrame:
    if not symbols:
        return pd.DataFrame()

    demo_points = [
        ("Improving", 96.0, 101.0, [94.8, 95.2, 95.6, 96.0], [99.0, 99.7, 100.3, 101.0]),
        ("Leading", 102.0, 101.5, [100.8, 101.1, 101.5, 102.0], [99.6, 100.0, 100.7, 101.5]),
        ("Lagging", 92.4, 94.9, [93.2, 92.6, 92.5, 92.4], [96.0, 95.0, 94.9, 94.9]),
        ("Leading", 97.2, 101.2, [95.2, 95.6, 96.3, 97.2], [99.4, 100.1, 100.7, 101.2]),
        ("Weakening", 101.6, 99.6, [102.2, 102.1, 101.9, 101.6], [101.2, 100.7, 100.2, 99.6]),
        ("Improving", 98.3, 100.5, [97.0, 97.4, 97.9, 98.3], [99.1, 99.6, 100.0, 100.5]),
    ]

    rows = []
    for idx, symbol in enumerate(symbols):
        quadrant, rs_ratio, rs_momentum, tail_x, tail_y = demo_points[idx % len(demo_points)]
        rows.append(
            {
                "symbol": symbol,
                "label": format_symbol(symbol),
                "rs_ratio": (rs_ratio - 100) / 4.0,
                "rs_momentum": (rs_momentum - 100) / 4.0,
                "quadrant": quadrant,
                "score": ((rs_ratio - 100) / 4.0) + ((rs_momentum - 100) / 4.0),
                "tail_x": [(value - 100) / 4.0 for value in tail_x],
                "tail_y": [(value - 100) / 4.0 for value in tail_y],
                "tail_dates": [f"T-{offset}" for offset in range(len(tail_x), 0, -1)],
                "close": 0.0,
            }
        )

    return pd.DataFrame(rows)


def bootstrap_state() -> None:
    st.session_state.setdefault("rrg_index_watchlist", list(SECTOR_INDEX_UNIVERSE.values()))
    st.session_state.setdefault("rrg_stock_watchlist", ["HDFCBANK.NS", "ICICIBANK.NS", "RELIANCE.NS", "INFY.NS"])
    st.session_state.setdefault("rrg_etf_watchlist", ["NIFTYBEES.NS", "BANKBEES.NS", "ITBEES.NS", "GOLDBEES.NS"])
    st.session_state.setdefault("rrg_mode", "Index")


def benchmark_key(label: str) -> str:
    return BENCHMARK_OPTIONS.get(label, "^NSEI")


def format_symbol(symbol: str) -> str:
    sector_label = next((label for label, value in SECTOR_INDEX_UNIVERSE.items() if value == symbol), None)
    if sector_label:
        return sector_label
    etf_label = next((label for label, value in ETF_UNIVERSE.items() if value == symbol), None)
    if etf_label:
        return etf_label
    return symbol.replace("^", "").replace(".NS", "").replace(".BO", "")


def active_watchlist_key(mode: str) -> str:
    return {
        "Index": "rrg_index_watchlist",
        "Stock": "rrg_stock_watchlist",
        "ETF": "rrg_etf_watchlist",
    }[mode]


def current_available_symbols(mode: str, index_symbols: list[str]) -> list[str]:
    if mode == "Index":
        return index_symbols
    if mode == "Stock":
        return NIFTY_STOCK_SEARCH_UNIVERSE
    return list(ETF_UNIVERSE.values())


def render_watchlist_card(index_symbols: list[str]) -> None:
    asset_mode = st.radio("Asset mode", ["Index", "Stock", "ETF"], horizontal=True, label_visibility="collapsed")
    st.session_state["rrg_mode"] = asset_mode

    st.markdown("### Quickly add from your watchlists")

    watchlist_key = active_watchlist_key(asset_mode)
    watchlist = st.session_state[watchlist_key]
    available_symbols = current_available_symbols(asset_mode, index_symbols)
    search_placeholder = {
        "Index": "Search and add indices",
        "Stock": "Search and add stocks",
        "ETF": "Search and add ETFs",
    }[asset_mode]

    search_text = st.text_input("Search and add", value="", placeholder=search_placeholder, label_visibility="collapsed")
    filtered_options = [
        symbol
        for symbol in available_symbols
        if symbol not in watchlist and search_text.lower() in format_symbol(symbol).lower()
    ]

    if filtered_options:
        add_symbol = st.selectbox(
            "Matching items",
            options=filtered_options,
            format_func=format_symbol,
            label_visibility="collapsed",
        )
        if st.button("Add to watchlist", use_container_width=True):
            st.session_state[watchlist_key] = watchlist + [add_symbol]
            st.rerun()

    if not watchlist:
        st.caption(f"You have not created any {asset_mode.lower()} watchlist yet.")
    else:
        for idx, symbol in enumerate(watchlist):
            label = format_symbol(symbol)
            row_color = WATCHLIST_ROW_COLORS[idx % len(WATCHLIST_ROW_COLORS)]
            cols = st.columns([0.16, 0.84])
            with cols[0]:
                if st.button("×", key=f"remove_{asset_mode}_{symbol}", help=f"Remove {label}"):
                    st.session_state[watchlist_key] = [item for item in watchlist if item != symbol]
                    st.rerun()
            with cols[1]:
                st.markdown(
                    f"""
                    <div style="background:{row_color};border-radius:10px;padding:0.62rem 0.8rem;font-size:0.94rem;
                    color:#1f2937;border:1px solid rgba(15,23,42,0.06);margin-bottom:0.35rem;">
                      {label}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def render_info_panel() -> None:
    st.markdown(
        """
        <div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:14px;padding:1rem 1rem 0.9rem 1rem;
        color:#334155;font-size:0.86rem;line-height:1.55;">
          <strong>Tip:</strong> Click and drag an area of the chart to zoom.<br/>
          <strong>Note:</strong> RRG charts show you the relative strength and momentum for a group of securities. Strong members
          appear in the green Leading quadrant. As relative momentum fades, they move into the yellow Weakening quadrant. If relative
          strength then fades, they move into the red Lagging quadrant. Finally, when momentum starts to pick up again, they shift
          into the blue Improving quadrant.
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    bootstrap_state()

    st.markdown(
        """
        <style>
        .stApp {
            background: #f5f7fb;
        }
        div[data-testid="stSidebar"] {
            display: none;
        }
        .rrg-shell {
            padding-top: 0.2rem;
        }
        .rrg-topline {
            display:flex;
            justify-content:space-between;
            align-items:center;
            font-size:0.82rem;
            color:#3b82f6;
            margin-bottom:0.6rem;
        }
        .rrg-card {
            background:#ffffff;
            border:1px solid #e5e7eb;
            border-radius:16px;
            padding:1rem 1rem 0.7rem 1rem;
            box-shadow:0 1px 2px rgba(15,23,42,0.04);
        }
        .rrg-card-title {
            font-size:1.18rem;
            font-weight:700;
            color:#111827;
            margin-bottom:0.9rem;
        }
        .rrg-note {
            color:#6b7280;
            font-size:0.8rem;
        }
        .rrg-watch-card {
            background:#ffffff;
            border:1px solid #e5e7eb;
            border-radius:16px;
            padding:1rem;
            box-shadow:0 1px 2px rgba(15,23,42,0.04);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="rrg-shell">', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="rrg-topline">
          <div>Relative Rotation Graph</div>
          <div>◎ Watch Demo</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left_col, right_col = st.columns([4.2, 1.3], gap="large")
    index_symbols = list(SECTOR_INDEX_UNIVERSE.values())

    with left_col:
        st.markdown('<div class="rrg-card">', unsafe_allow_html=True)
        st.markdown('<div class="rrg-card-title">Relative Rotation Graph ⓘ</div>', unsafe_allow_html=True)

        control_col1, control_col2, control_col3 = st.columns([1.2, 1.2, 1.25], gap="large")
        with control_col1:
            benchmark_label = st.selectbox("Benchmark", list(BENCHMARK_OPTIONS.keys()), index=0)
        with control_col2:
            tail_length = st.slider("Tail length", min_value=4, max_value=52, value=6, format="%dweeks")
        with control_col3:
            timeframe = st.selectbox("Candle timeframe", ["Weekly candle", "Daily candle"], index=0)
            include_partial = st.toggle("Include partial candles", value=False)

        asset_mode = st.session_state["rrg_mode"]
        interval = "1wk" if timeframe == "Weekly candle" else "1d"
        period = "5y" if timeframe == "Weekly candle" else "2y"
        benchmark_symbol = benchmark_key(benchmark_label)
        watchlist_symbols = st.session_state[active_watchlist_key(asset_mode)] or current_available_symbols(asset_mode, index_symbols)[:4]
        price_frame = load_prices([benchmark_symbol, *watchlist_symbols], period=period, interval=interval)

        if not include_partial and not price_frame.empty and len(price_frame.index) > tail_length:
            price_frame = price_frame.iloc[:-1]

        snapshot = build_rrg_snapshot(
            price_frame=price_frame,
            benchmark_symbol=benchmark_symbol,
            tail_periods=tail_length,
            roc_period=DEFAULT_CONFIG.roc_period,
            zscore_window=DEFAULT_CONFIG.zscore_window,
            labels={symbol: format_symbol(symbol) for symbol in watchlist_symbols},
        )
        live_symbol_count = len(snapshot.index) if not snapshot.empty else 0
        using_demo_snapshot = live_symbol_count < max(2, min(len(watchlist_symbols), 2))
        if using_demo_snapshot:
            snapshot = build_demo_snapshot(watchlist_symbols)

        latest_date = latest_available_date(price_frame)
        latest_date_text = latest_date.strftime("%d %b %Y") if latest_date else "latest close"
        period_label = "weeks" if timeframe == "Weekly candle" else "sessions"
        st.caption(f"Showing data for {tail_length + 1} {period_label} ending {latest_date_text}")

        progress_left, progress_right = st.columns([5.2, 2.1], gap="small")
        with progress_left:
            st.progress(min((tail_length + 1) / 52, 1.0))
        with progress_right:
            button_cols = st.columns([1.3, 0.7, 0.8])
            with button_cols[0]:
                animate = st.button("Animate ✨", use_container_width=True)
            with button_cols[1]:
                download = st.button("⇩", use_container_width=True)
            with button_cols[2]:
                show_zone = st.toggle("Zone", value=True)

        st.markdown('<div class="rrg-note">Note: Drag window to see historic data</div>', unsafe_allow_html=True)
        if using_demo_snapshot:
            st.info("Live Yahoo data is unavailable or incomplete right now, so this chart is showing demo RRG trails for the selected watchlist.")

        if snapshot.empty:
            st.warning("No RRG snapshot could be created for the selected benchmark and watchlist.")
        else:
            fig = build_rrg_figure(
                snapshot=snapshot,
                title="",
                tail_periods=tail_length,
                zone_shading=show_zone,
                scale_mode="rrg100",
            )
            st.pyplot(fig, use_container_width=True)

            if download:
                filename_mode = asset_mode.lower()
                output = save_chart(fig, f"rrg_{filename_mode}_{benchmark_label.lower().replace(' ', '_')}.png")
                st.success(f"Saved chart to {output}")
            if animate:
                st.info("Animation is not implemented yet. The control is kept in place so we can add tail playback next.")

        st.markdown("</div>", unsafe_allow_html=True)

    with right_col:
        st.markdown('<div class="rrg-watch-card">', unsafe_allow_html=True)
        render_watchlist_card(index_symbols)
        st.markdown("</div>", unsafe_allow_html=True)
        st.write("")
        render_info_panel()

    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
