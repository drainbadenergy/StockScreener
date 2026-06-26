#!/usr/bin/env python3
"""
CLI entry point — run the EOD breakout screener and optionally push Telegram alerts.

Usage:
    python run_screener.py
    python run_screener.py --no-telegram
    python run_screener.py --symbols path/to/custom_symbols.txt
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from stock_screener.alerts.telegram import send_breakout_alert
from stock_screener.config import DEFAULT_SYMBOLS_FILE
from stock_screener.data.pipeline import fetch_historical_data
from stock_screener.engine.screener import BreakoutScreener
from stock_screener.utils.symbols import load_symbols


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EOD NSE Breakout Screener")
    parser.add_argument(
        "--symbols",
        type=Path,
        default=DEFAULT_SYMBOLS_FILE,
        help=f"Path to symbol list (default: {DEFAULT_SYMBOLS_FILE})",
    )
    parser.add_argument(
        "--no-telegram",
        action="store_true",
        help="Skip Telegram alert even if credentials are configured.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging.")
    args = parser.parse_args(argv)

    _configure_logging(args.verbose)
    logger = logging.getLogger(__name__)

    symbols = load_symbols(args.symbols)
    if not symbols:
        logger.error("No symbols to screen. Check %s", args.symbols)
        return 1

    logger.info("Fetching data for %d symbols …", len(symbols))
    stock_data, benchmark_data = fetch_historical_data(symbols)

    if not stock_data:
        logger.error("No stock data retrieved.")
        return 1
    if benchmark_data.empty:
        logger.error("Benchmark data unavailable.")
        return 1

    screener = BreakoutScreener(stock_data, benchmark_data)
    breakouts = screener.screen()

    if breakouts.empty:
        logger.info("No breakouts today.")
        print("\n=== NO BREAKOUTS ===\n")
    else:
        logger.info("%d breakout(s) found.", len(breakouts))
        print("\n=== BREAKOUTS ===\n")
        print(breakouts.to_string(index=False))
        print()

    if not args.no_telegram:
        sent = send_breakout_alert(breakouts)
        if sent:
            logger.info("Telegram alert sent.")
        else:
            logger.warning("Telegram alert not sent (check .env credentials).")

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
CLI entry point — run the EOD breakout screener and optionally push Telegram alerts.

Usage:
    python run_screener.py
    python run_screener.py --no-telegram
    python run_screener.py --symbols path/to/custom_symbols.txt
"""

import argparse
import logging
import sys
from pathlib import Path

from stock_screener.alerts.telegram import send_breakout_alert
from stock_screener.config import DEFAULT_SYMBOLS_FILE
from stock_screener.data.pipeline import fetch_historical_data
from stock_screener.engine.screener import BreakoutScreener
from stock_screener.utils.symbols import load_symbols


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EOD NSE Breakout Screener")
    parser.add_argument(
        "--symbols",
        type=Path,
        default=DEFAULT_SYMBOLS_FILE,
        help=f"Path to symbol list (default: {DEFAULT_SYMBOLS_FILE})",
    )
    parser.add_argument(
        "--no-telegram",
        action="store_true",
        help="Skip Telegram alert even if credentials are configured.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging.")
    args = parser.parse_args(argv)

    _configure_logging(args.verbose)
    logger = logging.getLogger(__name__)

    symbols = load_symbols(args.symbols)
    if not symbols:
        logger.error("No symbols to screen. Check %s", args.symbols)
        return 1

    logger.info("Fetching data for %d symbols …", len(symbols))
    stock_data, benchmark_data = fetch_historical_data(symbols)

    if not stock_data:
        logger.error("No stock data retrieved.")
        return 1
    if benchmark_data.empty:
        logger.error("Benchmark data unavailable.")
        return 1

    screener = BreakoutScreener(stock_data, benchmark_data)
    breakouts = screener.screen()

    if breakouts.empty:
        logger.info("No breakouts today.")
        print("\n=== NO BREAKOUTS ===\n")
    else:
        logger.info("%d breakout(s) found.", len(breakouts))
        print("\n=== BREAKOUTS ===\n")
        print(breakouts.to_string(index=False))
        print()

    if not args.no_telegram:
        sent = send_breakout_alert(breakouts)
        if sent:
            logger.info("Telegram alert sent.")
        else:
            logger.warning("Telegram alert not sent (check .env credentials).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
