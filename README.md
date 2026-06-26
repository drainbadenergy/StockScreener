# StockScreener

# 🚀 NSE Breakout Screener & Telegram Bot

An automated Python-based stock screener that filters the Nifty 500 universe for high-probability, institutional-grade breakout setups and delivers real-time alerts directly to a Telegram group.


<img width="846" height="367" alt="image" src="https://github.com/user-attachments/assets/e5a53308-b7a4-4805-8831-eed15d1d949e" />


## 📖 Overview
This script is designed to run automatically at market close. It downloads 2 years of historical daily OHLCV data for 467 tradable NSE equities via Yahoo Finance (`yfinance`). It then pushes every stock through a strict **6-Gate Technical Filter** based on Trend, Volatility Contraction (VCP), and Relative Strength. 

Stocks that survive all 6 gates are formatted into a clean report and fired off to a designated Telegram chat via a custom bot.

## ✨ Features
* **Stateless Execution:** Pulls fresh data on every run to prevent corrupted local cache issues.
* **Vectorized Math:** Uses `pandas` and `pandas-ta` to calculate technical indicators for 467 stocks in seconds.
* **Anti-Bot Proxy Avoidance:** Designed to run locally (avoiding cloud firewall IP bans from Yahoo Finance).
* **Automated Delivery:** Integrates directly with the Telegram Bot API for instant push notifications.

---

## 🧠 The 6-Gate Strategy
For a stock to trigger an alert, it must pass **all six** of these conditions simultaneously on the daily timeframe:

1. **The Macro Trend:** Current Close > 200 SMA **AND** 50 SMA > 200 SMA. (Ensures we only buy in confirmed macro uptrends).
2. **Volatility Contraction (VCP):** Yesterday's 10-day ATR < Yesterday's 50-day ATR. (Ensures the stock was tightly coiled and building energy before today's move).
3. **Relative Strength:** 50-day return > Nifty 50 benchmark (`^NSEI`) 50-day return. (Filters out market laggards).
4. **Institutional Volume:** Today's Volume > 1.8x the 20-day Average Volume. (Proves heavy institutional money is driving the move).
5. **The Breakout:** Today's Close > Highest High of the last 50 trading sessions. (The actual trigger clearing medium-term resistance).
6. **Anti-Chase Buffer:** Today's Close is <= 8% above the 50-day resistance line. (Prevents buying into overextended, runaway gaps).

---

## ⚙️ Installation & Setup

### 1. Prerequisites
* Python 3.9+ installed on your machine.
* A Telegram Bot Token (Create one via [@BotFather](https://t.me/botfather) on Telegram).
* A Telegram Chat ID (The ID of the group or user receiving the alerts).

### 2. Clone the Repository
```bash
git clone [https://github.com/YourUsername/Stock-Screener.git](https://github.com/YourUsername/Stock-Screener.git)
cd Stock-Screener
