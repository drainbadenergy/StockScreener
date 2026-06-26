"""Symbol universe loading utilities."""

from __future__ import annotations

import logging
from pathlib import Path

from stock_screener.config import DEFAULT_SYMBOLS_FILE
from stock_screener.data.symbol_map import normalize_universe
from stock_screener.data.universe import NIFTY500_SYMBOLS

logger = logging.getLogger(__name__)


def load_symbols(path: Path | None = None) -> list[str]:
    """
    Load NSE symbols from a newline-delimited text file.

    Lines starting with '#' are treated as comments. Blank lines are ignored.
    Symbols may include or omit the .NS suffix.

    Falls back to the bundled Nifty 500 universe when the file is missing.
    """
    file_path = path or DEFAULT_SYMBOLS_FILE

    if not file_path.exists():
        logger.warning(
            "Symbol file not found (%s) — using bundled Nifty 500 universe (%d symbols).",
            file_path,
            len(NIFTY500_SYMBOLS),
        )
        normalized, _ = normalize_universe(list(NIFTY500_SYMBOLS))
        logger.info(
            "After symbol corrections: %d tradable tickers (%d legacy names removed/mapped).",
            len(normalized),
            len(NIFTY500_SYMBOLS) - len(normalized),
        )
        return normalized

    symbols: list[str] = []
    with file_path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            for token in stripped.replace(",", " ").split():
                clean = token.strip().upper()
                if clean:
                    symbols.append(clean)

    seen: set[str] = set()
    unique: list[str] = []
    for symbol in symbols:
        if symbol not in seen:
            seen.add(symbol)
            unique.append(symbol)

    if not unique:
        logger.warning("Symbol file empty — using bundled universe.")
        normalized, _ = normalize_universe(list(NIFTY500_SYMBOLS))
        return normalized

    normalized, _ = normalize_universe(unique)
    logger.info(
        "Loaded %d symbols from %s (%d after NSE/Yahoo corrections).",
        len(unique),
        file_path,
        len(normalized),
    )
    return normalized
