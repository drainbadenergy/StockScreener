"""Write data/nifty500.txt from the bundled Nifty 500 symbol universe."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from stock_screener.data.symbol_map import normalize_universe
from stock_screener.data.universe import NIFTY500_SYMBOLS

OUTPUT = Path(__file__).resolve().parent.parent / "data" / "nifty500.txt"


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    normalized, _ = normalize_universe(list(NIFTY500_SYMBOLS))
    header = (
        "# Nifty 500 universe — one NSE symbol per line (without .NS suffix)\n"
        "# Yahoo-ready symbols after merge/rename corrections\n"
        "# Refresh: python scripts/update_symbols.py\n\n"
    )
    OUTPUT.write_text(header + "\n".join(normalized) + "\n", encoding="utf-8")
    print(f"Wrote {len(normalized)} symbols -> {OUTPUT}")


if __name__ == "__main__":
    main()
