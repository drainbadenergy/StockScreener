"""
Batch historical data pipeline for NSE equities and the Nifty 50 benchmark.
Uses yfinance parallel downloads (threads=True) to minimize network latency.
"""

from __future__ import annotations

import logging
from typing import Iterable

import pandas as pd
import yfinance as yf

from stock_screener.config import (
    BENCHMARK_SYMBOL,
    DATA_PERIOD,
    MIN_TRADING_DAYS,
    YFINANCE_SUFFIX,
)
from stock_screener.data.symbol_map import resolve_symbol

logger = logging.getLogger(__name__)
_OHLCV_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


def to_yfinance_ticker(symbol: str) -> str:
    """Append the NSE suffix when missing (e.g. RELIANCE -> RELIANCE.NS)."""
    symbol = symbol.strip().upper()
    if not symbol:
        raise ValueError("Empty symbol string.")
    if symbol.startswith("^"):
        return symbol
    if symbol.endswith(YFINANCE_SUFFIX):
        symbol = symbol[: -len(YFINANCE_SUFFIX)]
    resolved = resolve_symbol(symbol)
    if resolved is None:
        raise ValueError(f"Symbol excluded or invalid: {symbol}")
    symbol = resolved
    return f"{symbol}{YFINANCE_SUFFIX}"


def strip_yfinance_suffix(ticker: str) -> str:
    """Display-friendly symbol without exchange suffix."""
    if ticker.endswith(YFINANCE_SUFFIX):
        return ticker[: -len(YFINANCE_SUFFIX)]
    return ticker.lstrip("^")


def _normalize_ohlcv_frame(raw: pd.DataFrame) -> pd.DataFrame:
    """Coerce a single-ticker download into a clean, sorted OHLCV DataFrame."""
    if raw is None or raw.empty:
        return pd.DataFrame(columns=_OHLCV_COLUMNS)

    frame = raw.copy()
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(-1)

    missing = [col for col in _OHLCV_COLUMNS if col not in frame.columns]
    if missing:
        logger.debug("Missing columns %s — skipping frame.", missing)
        return pd.DataFrame(columns=_OHLCV_COLUMNS)

    frame = frame[_OHLCV_COLUMNS].copy()
    frame.index = pd.to_datetime(frame.index)
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    frame = frame.dropna(subset=["Close", "Volume"], how="any")
    frame["Volume"] = frame["Volume"].clip(lower=0)
    return frame


def _extract_ticker_frame(
    downloaded: pd.DataFrame,
    ticker: str,
    *,
    single_ticker: bool,
) -> pd.DataFrame:
    """Pull one ticker's OHLCV from a (possibly multi-ticker) yfinance download."""
    if downloaded is None or downloaded.empty:
        return pd.DataFrame(columns=_OHLCV_COLUMNS)

    if single_ticker:
        return _normalize_ohlcv_frame(downloaded)

    if not isinstance(downloaded.columns, pd.MultiIndex):
        return _normalize_ohlcv_frame(downloaded)

    if ticker not in downloaded.columns.get_level_values(0):
        logger.warning("No data returned for %s.", ticker)
        return pd.DataFrame(columns=_OHLCV_COLUMNS)

    return _normalize_ohlcv_frame(downloaded[ticker])


_DOWNLOAD_CHUNK_SIZE = 80


def _download_batch(
    tickers: list[str],
    *,
    period: str,
) -> pd.DataFrame:
    """Download a batch of tickers; returns raw yfinance DataFrame."""
    if not tickers:
        return pd.DataFrame()
    try:
        # NO optional arguments that might cause trouble
        return yf.download(
            tickers=tickers,
            period=period,
            interval="1d",
            group_by="ticker",
            threads=True,
            auto_adjust=True,
            progress=False,
        )
    except Exception as e:
        logger.warning("Batch download failed for chunk %s...: %s", tickers[:3], str(e)[:50])
        return pd.DataFrame()


def _merge_downloads(parts: list[pd.DataFrame]) -> pd.DataFrame:
    """Combine chunked multi-ticker downloads on the ticker column level."""
    valid = [part for part in parts if part is not None and not part.empty]
    if not valid:
        return pd.DataFrame()
    if len(valid) == 1:
        return valid[0]
    if all(isinstance(part.columns, pd.MultiIndex) for part in valid):
        return pd.concat(valid, axis=1)
    return valid[-1]


def _download_all_tickers(tickers: list[str], *, period: str) -> pd.DataFrame:
    """Download tickers in chunks to avoid Yahoo/yfinance dropping symbols."""
    parts: list[pd.DataFrame] = []
    for start in range(0, len(tickers), _DOWNLOAD_CHUNK_SIZE):
        chunk = tickers[start : start + _DOWNLOAD_CHUNK_SIZE]
        parts.append(_download_batch(chunk, period=period))
    return _merge_downloads(parts)


def _retry_single_ticker(ticker: str, *, period: str) -> pd.DataFrame:
    """Fallback single-ticker download when batch response is empty."""
    try:
        return yf.download(
            tickers=ticker,
            period=period,
            interval="1d",
            auto_adjust=True,
            progress=False,
        )
    except Exception as e:
        logger.warning("Single retry failed for %s: %s", ticker, str(e)[:50])
        return pd.DataFrame()


def fetch_historical_data(
    symbols: Iterable[str],
    *,
    period: str = DATA_PERIOD,
    benchmark: str = BENCHMARK_SYMBOL,
    min_trading_days: int = MIN_TRADING_DAYS,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """Batch-download daily OHLCV for all symbols plus the benchmark index."""
    tickers = []
    for raw in symbols:
        if not str(raw).strip():
            continue
        try:
            tickers.append(to_yfinance_ticker(str(raw)))
        except ValueError:
            continue

    benchmark_ticker = to_yfinance_ticker(benchmark)

    seen: set[str] = set()
    equity_tickers: list[str] = []
    for ticker in tickers:
        if ticker == benchmark_ticker or ticker in seen:
            continue
        seen.add(ticker)
        equity_tickers.append(ticker)

    if not equity_tickers:
        logger.warning("No equity symbols supplied.")
        return {}, pd.DataFrame(columns=_OHLCV_COLUMNS)

    logger.info(
        "Downloading %d symbols + benchmark (%s) with threads=True …",
        len(equity_tickers),
        benchmark_ticker,
    )

    all_tickers = equity_tickers + [benchmark_ticker]
    single = len(all_tickers) == 1

    yfinance_logger = logging.getLogger("yfinance")
    previous_level = yfinance_logger.level
    yfinance_logger.setLevel(logging.CRITICAL)

    try:
        downloaded = _download_all_tickers(all_tickers, period=period)
    except Exception as exc:
        logger.exception("yfinance batch download failed: %s", exc)
        return {}, pd.DataFrame(columns=_OHLCV_COLUMNS)
    finally:
        yfinance_logger.setLevel(previous_level)

    stock_frames: dict[str, pd.DataFrame] = {}
    retry_queue: list[str] = []
    for ticker in equity_tickers:
        frame = _extract_ticker_frame(downloaded, ticker, single_ticker=single)
        if len(frame) < min_trading_days:
            retry_queue.append(ticker)
            continue
        stock_frames[strip_yfinance_suffix(ticker)] = frame

    for ticker in retry_queue:
        retry = _retry_single_ticker(ticker, period=period)
        frame = _normalize_ohlcv_frame(retry)
        if len(frame) >= min_trading_days:
            stock_frames[strip_yfinance_suffix(ticker)] = frame

    missing = [
        strip_yfinance_suffix(ticker)
        for ticker in equity_tickers
        if strip_yfinance_suffix(ticker) not in stock_frames
    ]

    if missing:
        preview = ", ".join(missing[:15])
        suffix = f" (+{len(missing) - 15} more)" if len(missing) > 15 else ""
        logger.warning(
            "No usable Yahoo data for %d symbols (skipped): %s%s",
            len(missing),
            preview,
            suffix,
        )

    benchmark_frame = _extract_ticker_frame(
        downloaded, benchmark_ticker, single_ticker=single
    )
    if len(benchmark_frame) < min_trading_days:
        retry = _retry_single_ticker(benchmark_ticker, period=period)
        benchmark_frame = _normalize_ohlcv_frame(retry)
    if len(benchmark_frame) < min_trading_days:
        logger.error(
            "Benchmark %s has insufficient data (%d rows).",
            benchmark_ticker,
            len(benchmark_frame),
        )
        benchmark_frame = pd.DataFrame(columns=_OHLCV_COLUMNS)

    logger.info(
        "Download complete — %d/%d symbols usable, benchmark rows=%d.",
        len(stock_frames),
        len(equity_tickers),
        len(benchmark_frame),
    )
    return stock_frames, benchmark_frame