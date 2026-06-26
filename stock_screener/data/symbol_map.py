"""
NSE symbol corrections for yfinance.

The bundled Nifty 500 list includes legacy tickers from mergers, renames, and
delistings. This module maps old symbols to current Yahoo/NSE tickers and
drops symbols with no reliable data source.
"""

from __future__ import annotations

# Old NSE symbol -> current symbol accepted by yfinance (without .NS suffix).
SYMBOL_ALIASES: dict[str, str] = {
    "ADANITRANS": "ADANIENSOL",
    "AEGISCHEM": "AEGISLOG",
    "AMARAJABAT": "ARE&M",
    "CENTURYTEX": "ABREL",
    "WELSPUNIND": "WELSPUNLIV",
    "MINDAIND": "UNOMINDA",
    "L&TFH": "LTF",
    "IBULHSGFIN": "SAMMAANCAP",
    "SHRIRAMCIT": "SHRIRAMFIN",
    "SRTRANSFIN": "SHRIRAMFIN",
    "IIFLWAM": "360ONE",
    "PVR": "PVRINOX",
    "ZOMATO": "ETERNAL",
    "MCDOWELL-N": "UNITDSPR",
    "HDFC": "HDFCBANK",
    "IDFC": "IDFCFIRSTB",
    "TATACOFFEE": "TATACONSUM",
    "TATAMOTORS": "TMPV",
    "TATASTLLP": "TATASTEEL",
}

# Symbols with no usable Yahoo history — skip silently (merged, suspended, or delisted).
SYMBOLS_EXCLUDED: frozenset[str] = frozenset(
    {
        "DHANI",
        "SPICEJET",
        "MAHINDCIE",
        "EQUITAS",
        "GMRINFRA",
        "GLS",
        "TV18BRDCST",
        "TATAMTRDVR",
        "IBREALEST",
        "LAXMIMACH",
        "HEMIPROP",
        "TCNSBRANDS",
        "INOXLEISUR",
        "EASEMYTRIP",
        "GOCOLORS",
        "SUVENPHAR",
        "SOLARA",
        "JUSTDIAL",
        "VAKRANGEE",
        "RTNINDIA",
        "PEL",
        "LTIM",
        "LTI",
        "MINDTREE",
        "INFIBEAM",
        "KALPATPOWR",
        "ISEC",
        "SEQUENT",
        "GSPL",
    }
)


def resolve_symbol(symbol: str) -> str | None:
    """
    Return the yfinance-ready NSE symbol, or None if the symbol should be skipped.
    """
    clean = symbol.strip().upper()
    if not clean or clean.startswith("^"):
        return clean or None
    if clean.endswith(".NS"):
        clean = clean[: -len(".NS")]
    if clean in SYMBOLS_EXCLUDED:
        return None
    mapped = SYMBOL_ALIASES.get(clean, clean)
    if mapped in SYMBOLS_EXCLUDED:
        return None
    return mapped


def normalize_universe(symbols: list[str]) -> tuple[list[str], dict[str, str]]:
    """
    Resolve aliases, drop excluded tickers, and deduplicate.

    Returns
    -------
    tuple[list[str], dict[str, str]]
        Unique resolved symbols for download, and mapping resolved -> original
        (when an alias was applied, original is the first seen legacy name).
    """
    resolved: list[str] = []
    seen: set[str] = set()
    provenance: dict[str, str] = {}

    for raw in symbols:
        canonical = resolve_symbol(raw)
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        resolved.append(canonical)
        if canonical != raw.strip().upper().replace(".NS", ""):
            provenance[canonical] = raw.strip().upper()
        else:
            provenance[canonical] = canonical

    return resolved, provenance
