from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import streamlit as st

from rrg_dashboard.charts import build_rrg_figure
from rrg_dashboard.config import DEFAULT_CONFIG, OUTPUTS_DIR, SECTOR_INDEX_UNIVERSE
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


def bootstrap_state() -> None:
    default_watchlist = ["^NSEPHARMA", "^NSEFMCG", "^NSEBANK", "^NSEIT"]
    st.session_state.setdefault("rrg_watchlist", default_watchlist)
    st.session_state.setdefault("rrg_mode", "Index")


def benchmark_key(label: str) -> str:
    return BENCHMARK_OPTIONS.get(label, "^NSEI")


def format_symbol(symbol: str) -> str:
    return next((label for label, value in SECTOR_INDEX_UNIVERSE.items() if value == symbol), symbol.replace("^", ""))


def render_watchlist_card(available_symbols: list[str]) -> None:
    asset_mode = st.radio("Asset mode", ["Index", "Stock", "ETF"], horizontal=True, label_visibility="collapsed")
    st.session_state["rrg_mode"] = asset_mode

    st.markdown("### Quickly add from your watchlists")
    if asset_mode != "Index":
        st.info("This refreshed layout is focused on sector/index RRG first. Stock and ETF watchlists can be layered back in next.")
        return

    search_text = st.text_input("Search and add indices", value="", placeholder="Search and add indices")
    watchlist = st.session_state["rrg_watchlist"]

    filtered_options = [
        symbol
        for symbol in available_symbols
        if symbol not in watchlist and search_text.lower() in format_symbol(symbol).lower()
    ]

    if filtered_options:
        add_symbol = st.selectbox(
            "Matching indices",
            options=filtered_options,
            format_func=format_symbol,
            label_visibility="collapsed",
        )
        if st.button("Add to watchlist", use_container_width=True):
            st.session_state["rrg_watchlist"] = watchlist + [add_symbol]
            st.rerun()

    if not watchlist:
        st.caption("You have not created any index watchlist yet.")
    else:
        for idx, symbol in enumerate(watchlist):
            label = format_symbol(symbol)
            row_color = WATCHLIST_ROW_COLORS[idx % len(WATCHLIST_ROW_COLORS)]
            cols = st.columns([0.16, 0.84])
            with cols[0]:
                if st.button("×", key=f"remove_{symbol}", help=f"Remove {label}"):
                    st.session_state["rrg_watchlist"] = [item for item in watchlist if item != symbol]
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
          <strong>Note:</strong> RRG charts show you the relative strength and momentum for a group of stocks. Stocks with strong
          relative strength and momentum appear in the green Leading quadrant. As relative momentum fades, they typically move into
          the yellow Weakening quadrant. If relative strength then fades, they move into the red Lagging quadrant. Finally, when
          momentum starts to pick up again, they shift into the blue Improving quadrant.
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
        .rrg-info-link {
            color:#2563eb;
            text-decoration:none;
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

    sector_symbols = list(SECTOR_INDEX_UNIVERSE.values())

    with left_col:
        st.markdown('<div class="rrg-card">', unsafe_allow_html=True)
        st.markdown('<div class="rrg-card-title">Relative Rotation Graph ⓘ</div>', unsafe_allow_html=True)

        control_col1, control_col2, control_col3 = st.columns([1.2, 1.2, 1.25], gap="large")
        with control_col1:
            benchmark_label = st.selectbox("Benchmark", list(BENCHMARK_OPTIONS.keys()), index=0)
        with control_col2:
            tail_length = st.slider("Tail length", min_value=4, max_value=12, value=6, format="%dweeks")
        with control_col3:
            timeframe = st.selectbox("Candle timeframe", ["Weekly candle", "Daily candle"], index=0)
            include_partial = st.toggle("Include partial candles", value=False)

        interval = "1wk" if timeframe == "Weekly candle" else "1d"
        period = "2y" if timeframe == "Weekly candle" else "1y"
        benchmark_symbol = benchmark_key(benchmark_label)
        watchlist_symbols = st.session_state["rrg_watchlist"] or ["^NSEPHARMA", "^NSEFMCG", "^NSEBANK", "^NSEIT"]
        price_frame = load_prices([benchmark_symbol, *watchlist_symbols], period=period, interval=interval)

        if not include_partial and not price_frame.empty and len(price_frame.index) > tail_length:
            price_frame = price_frame.iloc[:-1]

        snapshot = build_rrg_snapshot(
            price_frame=price_frame,
            benchmark_symbol=benchmark_symbol,
            tail_periods=tail_length,
            roc_period=14,
            zscore_window=20,
            labels={symbol: format_symbol(symbol) for symbol in watchlist_symbols},
        )

        latest_date = latest_available_date(price_frame)
        latest_date_text = latest_date.strftime("%d %b %Y") if latest_date else "latest close"
        st.caption(f"Showing data for {tail_length + 1} weeks ending {latest_date_text}")

        progress_left, progress_right = st.columns([5.2, 2.1], gap="small")
        with progress_left:
            st.progress(min((tail_length + 1) / 12, 1.0))
        with progress_right:
            button_cols = st.columns([1.3, 0.7, 0.8])
            with button_cols[0]:
                animate = st.button("Animate ✨", use_container_width=True)
            with button_cols[1]:
                download = st.button("⇩", use_container_width=True)
            with button_cols[2]:
                show_zone = st.toggle("Zone", value=True)

        st.markdown('<div class="rrg-note">Note: Drag window to see historic data</div>', unsafe_allow_html=True)

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
                output = save_chart(fig, f"rrg_{benchmark_label.lower().replace(' ', '_')}.png")
                st.success(f"Saved chart to {output}")
            if animate:
                st.info("Animation is not in this first rebuild yet. I kept the control in place so we can add tail playback next.")

        st.markdown("</div>", unsafe_allow_html=True)

    with right_col:
        st.markdown('<div class="rrg-watch-card">', unsafe_allow_html=True)
        render_watchlist_card(sector_symbols)
        st.markdown("</div>", unsafe_allow_html=True)
        st.write("")
        render_info_panel()

    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
