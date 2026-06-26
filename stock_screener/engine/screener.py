"""
Vectorized EOD breakout screener engine.

All indicator calculations use pandas / pandas_ta rolling operations applied to the
full time series at once — no Python loops over daily rows.

The six gates (ALL must pass on the latest bar):
  1. Trend:        Close > SMA_200  AND  SMA_50 > SMA_200
  2. VCP:          ATR_10 < ATR_50
  3. Rel Strength: Stock 50d return > Benchmark 50d return
  4. Volume:       Volume > 2.5 × 20-day Volume SMA
  5. Breakout:     Close > 50-day resistance (max High of prior 50 sessions)
  6. Anti-chase:   Close <= Resistance × 1.05
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import pandas_ta as ta

from stock_screener.config import (
    ANTI_CHASE_BUFFER,
    RESISTANCE_WINDOW,
    RETURN_LOOKBACK,
    VOLUME_SMA_WINDOW,
    VOLUME_SPIKE_MULTIPLIER,
)

logger = logging.getLogger(__name__)

# Output column order for the results table.
RESULT_COLUMNS: list[str] = [
    "Symbol",
    "Close",
    "Volume",
    "Volume_Spike_Pct",
    "Distance_From_Resistance_Pct",
    "ATR_Ratio",
    "Relative_Strength",
    "Resistance_50",
    "SMA_50",
    "SMA_200",
    "Return_50d",
    "Benchmark_Return_50d",
    "Date",
]


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Attach all screener indicators to *df* using fully vectorized operations.

    Parameters
    ----------
    df:
        OHLCV DataFrame indexed by datetime with columns Open, High, Low, Close, Volume.

    Returns
    -------
    pd.DataFrame
        Input frame with indicator columns appended.
    """
    if df.empty:
        return df

    out = df.copy()

    # --- Trend ---
    out["SMA_50"] = out["Close"].rolling(window=50, min_periods=50).mean()
    out["SMA_200"] = out["Close"].rolling(window=200, min_periods=200).mean()

    # --- Volatility contraction (VCP) via ATR ---
    # Shifted by 1 so the screener checks for compression the day BEFORE the breakout
    out["ATR_10"] = ta.atr(out["High"], out["Low"], out["Close"], length=10).shift(1)
    out["ATR_50"] = ta.atr(out["High"], out["Low"], out["Close"], length=50).shift(1)

    # --- Institutional volume baseline ---
    out["Vol_SMA_20"] = out["Volume"].rolling(
        window=VOLUME_SMA_WINDOW, min_periods=VOLUME_SMA_WINDOW
    ).mean()

    # --- 50-day resistance: highest High of the *previous* 50 sessions (excludes today) ---
    out["Resistance_50"] = (
        out["High"].shift(1).rolling(window=RESISTANCE_WINDOW, min_periods=RESISTANCE_WINDOW).max()
    )

    # --- 50-day percentage return (Close / Close_50d_ago - 1) × 100 ---
    out["Return_50d"] = out["Close"].pct_change(periods=RETURN_LOOKBACK) * 100.0

    return out


def _latest_row_passes_gates(
    latest: pd.Series,
    benchmark_return_50d: float,
) -> bool:
    """Evaluate all six gates on the most recent bar."""
    required = [
        "Close",
        "SMA_50",
        "SMA_200",
        "ATR_10",
        "ATR_50",
        "Volume",
        "Vol_SMA_20",
        "Resistance_50",
        "Return_50d",
    ]
    if latest[required].isna().any() or pd.isna(benchmark_return_50d):
        return False

    resistance = float(latest["Resistance_50"])
    if resistance <= 0:
        return False

    trend_ok = (latest["Close"] > latest["SMA_200"]) and (
        latest["SMA_50"] > latest["SMA_200"]
    )
    # In compute_indicators():
    out["VCP_Streak"] = (out["ATR_10"] < out["ATR_50"]).astype(int).rolling(5).sum()
    # In screener:
    vcp_ok = latest["VCP_Streak"] >= 3
    rs_ok = latest["Return_50d"] > benchmark_return_50d

    MIN_VOLUME_ABSOLUTE = 1_000_000  # 1 million shares
    volume_ok = (latest["Volume"] > MIN_VOLUME_ABSOLUTE) and (latest["Volume"] > (VOLUME_SPIKE_MULTIPLIER * latest["Vol_SMA_20"]))

    breakout_ok = latest["Close"] > resistance
    anti_chase_ok = latest["Close"] <= (resistance * ANTI_CHASE_BUFFER)

    return bool(trend_ok and vcp_ok and rs_ok and volume_ok and breakout_ok and anti_chase_ok)


def _build_result_row(
    symbol: str,
    latest: pd.Series,
    benchmark_return_50d: float,
) -> dict[str, Any]:
    """Derive display metrics from the latest indicator row."""
    resistance = float(latest["Resistance_50"])
    vol_sma = float(latest["Vol_SMA_20"])
    atr_50 = float(latest["ATR_50"])

    volume_spike_pct = ((float(latest["Volume"]) / vol_sma) - 1.0) * 100.0 if vol_sma > 0 else float("nan")
    distance_pct = ((float(latest["Close"]) / resistance) - 1.0) * 100.0 if resistance > 0 else float("nan")
    atr_ratio = float(latest["ATR_10"]) / atr_50 if atr_50 > 0 else float("nan")
    relative_strength = float(latest["Return_50d"]) - benchmark_return_50d

    return {
        "Symbol": symbol,
        "Close": round(float(latest["Close"]), 2),
        "Volume": int(latest["Volume"]),
        "Volume_Spike_Pct": round(volume_spike_pct, 2),
        "Distance_From_Resistance_Pct": round(distance_pct, 2),
        "ATR_Ratio": round(atr_ratio, 4),
        "Relative_Strength": round(relative_strength, 2),
        "Resistance_50": round(resistance, 2),
        "SMA_50": round(float(latest["SMA_50"]), 2),
        "SMA_200": round(float(latest["SMA_200"]), 2),
        "Return_50d": round(float(latest["Return_50d"]), 2),
        "Benchmark_Return_50d": round(benchmark_return_50d, 2),
        "Date": latest.name.strftime("%Y-%m-%d") if hasattr(latest.name, "strftime") else str(latest.name),
    }


class BreakoutScreener:
    """
    Orchestrates vectorized indicator computation and gate evaluation across a universe.
    """

    def __init__(self, stock_data: dict[str, pd.DataFrame], benchmark_data: pd.DataFrame) -> None:
        self.stock_data = stock_data
        self.benchmark_data = benchmark_data
        self._benchmark_return_50d: float | None = None

    @property
    def benchmark_return_50d(self) -> float:
        """50-day benchmark return from the latest available session."""
        if self._benchmark_return_50d is not None:
            return self._benchmark_return_50d

        bench = compute_indicators(self.benchmark_data)
        if bench.empty:
            self._benchmark_return_50d = float("nan")
            return self._benchmark_return_50d

        value = bench["Return_50d"].iloc[-1]
        self._benchmark_return_50d = float(value) if pd.notna(value) else float("nan")
        return self._benchmark_return_50d

    def screen(self) -> pd.DataFrame:
        """
        Run all six gates on every symbol and return a DataFrame of breakouts.

        Iteration is over *symbols* only; per-symbol indicator math is vectorized.
        """
        bench_ret = self.benchmark_return_50d
        if pd.isna(bench_ret):
            logger.error("Benchmark 50-day return unavailable — cannot screen.")
            return pd.DataFrame(columns=RESULT_COLUMNS)

        winners: list[dict[str, Any]] = []

        for symbol, ohlcv in self.stock_data.items():
            try:
                enriched = compute_indicators(ohlcv)
                if enriched.empty:
                    continue
                latest = enriched.iloc[-1]
                if _latest_row_passes_gates(latest, bench_ret):
                    winners.append(_build_result_row(symbol, latest, bench_ret))
            except Exception as exc:
                logger.warning("Failed to screen %s: %s", symbol, exc)

        if not winners:
            return pd.DataFrame(columns=RESULT_COLUMNS)

        results = pd.DataFrame(winners)[RESULT_COLUMNS]
        return results.sort_values("Relative_Strength", ascending=False).reset_index(drop=True)

    def get_price_history(self, symbol: str, lookback_days: int = 90) -> pd.DataFrame:
        """Return the last *lookback_days* of Close prices for charting."""
        frame = self.stock_data.get(symbol)
        if frame is None or frame.empty:
            return pd.DataFrame(columns=["Close"])
        tail = frame[["Close"]].tail(lookback_days).copy()
        tail.index = pd.to_datetime(tail.index)
        return tail
