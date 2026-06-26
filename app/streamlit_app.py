<<<<<<< HEAD
"""
Streamlit dashboard for the EOD Indian Breakout Screener.

Launch:
    streamlit run app/streamlit_app.py
"""
=======
>>>>>>> dcc7302aa2d9528f517b8a4b707d98d90954037a

from __future__ import annotations

import logging
import sys
from pathlib import Path

import streamlit as st

<<<<<<< HEAD
# Ensure project root is on sys.path when launched via `streamlit run`.
=======
>>>>>>> dcc7302aa2d9528f517b8a4b707d98d90954037a
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from stock_screener.alerts.telegram import send_breakout_alert
from stock_screener.config import CHART_LOOKBACK_DAYS, DEFAULT_SYMBOLS_FILE
from stock_screener.data.pipeline import fetch_historical_data
from stock_screener.engine.screener import BreakoutScreener
from stock_screener.utils.symbols import load_symbols

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="EOD Breakout Screener | NSE",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom styling for a cleaner dashboard ---
st.markdown(
    """
    <style>
    div[data-testid="stMetricValue"] { font-size: 1.35rem; }
    .block-container { padding-top: 1.5rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _init_session_state() -> None:
    defaults = {
        "breakouts": None,
        "screener": None,
        "symbols_screened": 0,
        "last_run_ok": False,
        "telegram_sent": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _run_pipeline(*, send_telegram: bool) -> None:
    """Fetch data, screen, optionally alert — updates session state."""
    symbols = load_symbols()
    if not symbols:
        st.error(f"No symbols found. Add tickers to `{DEFAULT_SYMBOLS_FILE}`.")
        return

    with st.spinner(f"Downloading & screening {len(symbols)} NSE symbols …"):
        stock_data, benchmark_data = fetch_historical_data(symbols)

        if not stock_data:
            st.warning("No usable price data returned. Check symbols or try again later.")
            st.session_state.last_run_ok = False
            return

        if benchmark_data.empty:
            st.error("Benchmark (^NSEI) data unavailable — screener cannot run.")
            st.session_state.last_run_ok = False
            return

        screener = BreakoutScreener(stock_data, benchmark_data)
        breakouts = screener.screen()

        st.session_state.screener = screener
        st.session_state.breakouts = breakouts
        st.session_state.symbols_screened = len(stock_data)
        st.session_state.last_run_ok = True
        st.session_state.telegram_sent = False

        if send_telegram:
            st.session_state.telegram_sent = send_breakout_alert(breakouts)


def main() -> None:
    _init_session_state()

    # --- Sidebar controls ---
    with st.sidebar:
        st.title("⚙️ Controls")
        st.caption("Six-gate EOD breakout system for NSE equities vs ^NSEI.")

        symbol_count = len(load_symbols())
        st.metric("Universe Size", f"{symbol_count} symbols")

        send_telegram = st.toggle("Send Telegram alert", value=False)

        if st.button("▶ Run Screener", type="primary", use_container_width=True):
            _run_pipeline(send_telegram=send_telegram)

        st.divider()
        st.markdown("**The 6 Gates**")
        st.markdown(
            """
            1. **Trend** — Close > SMA200, SMA50 > SMA200  
            2. **VCP** — ATR10 < ATR50  
            3. **Rel Strength** — 50d return > Nifty  
            4. **Volume** — Vol > 2.5× 20d avg  
            5. **Breakout** — Close > 50d resistance  
            6. **Anti-chase** — Close ≤ R50 × 1.05
            """
        )

    # --- Header ---
    st.title("📈 EOD Breakout Screener")
    st.markdown(
        "Identify **institutional-grade breakouts** across your NSE universe "
        "using six quantitative filters applied to the latest session."
    )

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Symbols Screened", st.session_state.symbols_screened or "—")
    with col_b:
        count = len(st.session_state.breakouts) if st.session_state.breakouts is not None else "—"
        st.metric("Breakouts Found", count)
    with col_c:
        if st.session_state.telegram_sent:
            st.metric("Telegram", "Sent ✓")
        else:
            st.metric("Telegram", "—")

    # --- Auto-load on first visit ---
    if st.session_state.breakouts is None:
        st.info("Click **Run Screener** in the sidebar to load today's results.")
        if st.button("Load Screener Now", type="secondary"):
            _run_pipeline(send_telegram=False)
        return

    breakouts = st.session_state.breakouts
    screener: BreakoutScreener | None = st.session_state.screener

    st.subheader("Breakout Candidates")
    if breakouts.empty:
        st.success("No breakouts today — no symbols passed all six gates.")
    else:
        st.dataframe(
            breakouts,
            use_container_width=True,
            hide_index=True,
        )

    # --- Per-stock detail expanders ---
    if screener is not None and breakouts is not None and not breakouts.empty:
        st.subheader("Stock Detail")
        for _, row in breakouts.iterrows():
            symbol = row["Symbol"]
            with st.expander(f"🔍 {symbol} — Close ₹{row['Close']}  ({row['Date']})", expanded=False):
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Volume Spike %", f"+{row['Volume_Spike_Pct']}%")
                m2.metric("Distance from Resistance", f"+{row['Distance_From_Resistance_Pct']}%")
                m3.metric("ATR Ratio (10/50)", f"{row['ATR_Ratio']}")
                m4.metric("Relative Strength", f"+{row['Relative_Strength']}%")

                history = screener.get_price_history(symbol, lookback_days=CHART_LOOKBACK_DAYS)
                if not history.empty:
                    st.caption(f"{CHART_LOOKBACK_DAYS}-day closing price")
                    st.line_chart(history, use_container_width=True)
                else:
                    st.warning("Price history unavailable for chart.")


if __name__ == "__main__":
    main()
