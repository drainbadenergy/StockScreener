"""
Telegram alerting for EOD breakout results.

Credentials are read exclusively from environment variables:
  - TELEGRAM_BOT_TOKEN
  - TELEGRAM_CHAT_ID

Never hardcode API keys in source code.
"""

from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd
import requests

from stock_screener.config import TELEGRAM_API_BASE, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)


def _credentials_configured() -> bool:
    token = (TELEGRAM_BOT_TOKEN or "").strip()
    chat_id = (TELEGRAM_CHAT_ID or "").strip()
    return bool(token and chat_id and "your_" not in token.lower())


def format_breakout_message(breakouts: pd.DataFrame, *, as_of: datetime | None = None) -> str:
    """
    Build a Markdown-formatted Telegram message with emoji hierarchy.

    Parameters
    ----------
    breakouts:
        Screener output DataFrame (may be empty).
    as_of:
        Report timestamp (defaults to now).
    """
    stamp = (as_of or datetime.now()).strftime("%d %b %Y, %H:%M IST")
    lines: list[str] = [
        "📊 *EOD Breakout Screener*",
        f"🗓 _As of {stamp}_",
        "",
    ]

    if breakouts is None or breakouts.empty:
        lines.extend(
            [
                "⚪ *No breakouts today*",
                "",
                "No NSE symbols passed all 6 quantitative gates on the latest session.",
            ]
        )
        return "\n".join(lines)

    lines.append(f"🟢 *{len(breakouts)} Breakout(s) Found*")
    lines.append("")

    for _, row in breakouts.iterrows():
        symbol = row.get("Symbol", "N/A")
        close = row.get("Close", "—")
        vol_spike = row.get("Volume_Spike_Pct", "—")
        dist = row.get("Distance_From_Resistance_Pct", "—")
        atr_ratio = row.get("ATR_Ratio", "—")
        rel_str = row.get("Relative_Strength", "—")
        resistance = row.get("Resistance_50", "—")

        lines.extend(
            [
                f"━━━━━━━━━━━━━━━━",
                f"🚀 *{symbol}*  |  Close ₹{close}",
                f"📈 Vol Spike: *+{vol_spike}%* vs 20d avg",
                f"🎯 Above Resistance: *+{dist}%*  (R50 ₹{resistance})",
                f"📉 ATR Ratio (10/50): *{atr_ratio}*",
                f"💪 Rel Strength vs Nifty: *+{rel_str}%*",
                "",
            ]
        )

    lines.append("_All 6 gates passed: Trend · VCP · RS · Volume · Breakout · Anti-chase_")
    return "\n".join(lines)


def send_telegram_message(text: str, *, parse_mode: str = "Markdown") -> bool:
    """
    POST *text* to all configured Telegram chats.
    Returns True if at least one message was sent successfully.
    """
    if not _credentials_configured():
        logger.warning("Telegram credentials missing — alert skipped.")
        return False

    url = TELEGRAM_API_BASE.format(token=TELEGRAM_BOT_TOKEN)
    
    # Split the comma-separated IDs into a list
    chat_ids = [cid.strip() for cid in TELEGRAM_CHAT_ID.split(",") if cid.strip()]
    
    success = False
    for chat_id in chat_ids:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            logger.info("Telegram alert delivered to %s.", chat_id)
            success = True
        except requests.RequestException as exc:
            logger.error("Telegram API error for %s: %s", chat_id, exc)

    return success

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        logger.info("Telegram alert delivered successfully.")
        return True
    except requests.RequestException as exc:
        logger.error("Telegram API error: %s", exc)
        return False


def send_breakout_alert(breakouts: pd.DataFrame) -> bool:
    """Format and send the daily breakout report (including empty-day status)."""
    message = format_breakout_message(breakouts)
    return send_telegram_message(message)
