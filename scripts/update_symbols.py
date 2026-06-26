#!/usr/bin/env python3
"""
Download the official NSE Nifty 500 constituent list and write data/nifty500.txt.

Usage:
    python scripts/update_symbols.py

Source CSV:
    https://www.nseindia.com/content/indices/ind_nifty500list.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = PROJECT_ROOT / "data" / "nifty500.txt"
NSE_CSV_URLS = (
    "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv",
    "https://www.nseindia.com/content/indices/ind_nifty500list.csv",
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/csv,application/octet-stream,*/*",
}


def fetch_nifty500_symbols() -> list[str]:
    session = requests.Session()
    session.headers.update(HEADERS)
    # NSE often requires a session cookie from the homepage.
    session.get("https://www.nseindia.com", timeout=30)
    last_error: Exception | None = None
    response = None
    for url in NSE_CSV_URLS:
        try:
            response = session.get(url, timeout=60)
            response.raise_for_status()
            break
        except Exception as exc:
            last_error = exc
            continue
    if response is None:
        raise RuntimeError(f"All NSE CSV URLs failed: {last_error}")

    from io import StringIO

    frame = pd.read_csv(StringIO(response.text))
    symbol_col = next(
        (col for col in frame.columns if str(col).strip().lower() in {"symbol", "symbols"}),
        frame.columns[2] if len(frame.columns) > 2 else frame.columns[0],
    )
    symbols = (
        frame[symbol_col]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
        .tolist()
    )
    return [s for s in symbols if s and s != "NAN"]


def write_symbol_file(symbols: list[str]) -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# Nifty 500 universe — one NSE symbol per line (without .NS suffix)\n"
        "# Regenerate with: python scripts/update_symbols.py\n"
    )
    body = "\n".join(symbols)
    OUTPUT_FILE.write_text(f"{header}\n{body}\n", encoding="utf-8")
    print(f"Wrote {len(symbols)} symbols to {OUTPUT_FILE}")


def main() -> int:
    try:
        symbols = fetch_nifty500_symbols()
    except Exception as exc:
        print(f"Failed to download NSE list: {exc}", file=sys.stderr)
        return 1

    if len(symbols) < 400:
        print(f"Warning: only {len(symbols)} symbols parsed — verify CSV format.", file=sys.stderr)

    write_symbol_file(symbols)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
