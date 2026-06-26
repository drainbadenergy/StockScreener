"""
Central configuration for the EOD Breakout Screener.

Loads environment variables and defines quantitative thresholds used by the engine.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root is one level above this package directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load .env from project root (does not override existing OS env vars).
load_dotenv(PROJECT_ROOT / ".env")

# --- Market data ---
BENCHMARK_SYMBOL: str = "^NSEI"
YFINANCE_SUFFIX: str = ".NS"
DEFAULT_SYMBOLS_FILE: Path = PROJECT_ROOT / "data" / "nifty500.txt"
DATA_PERIOD: str = "2y"  # Enough history for SMA-200 + buffer
MIN_TRADING_DAYS: int = 210  # Minimum rows required before screening a symbol

# --- Screener thresholds (the 6 gates) ---
VOLUME_SPIKE_MULTIPLIER: float = 1.5
VOLUME_SMA_WINDOW: int = 20
RESISTANCE_WINDOW: int = 50
RETURN_LOOKBACK: int = 50
ANTI_CHASE_BUFFER: float = 1.08  # Close must be <= Resistance * 1.05

# --- Telegram (loaded from environment — never hardcode secrets) ---
TELEGRAM_BOT_TOKEN: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID: str | None = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API_BASE: str = "https://api.telegram.org/bot{token}/sendMessage"

# --- UI ---
CHART_LOOKBACK_DAYS: int = 90
