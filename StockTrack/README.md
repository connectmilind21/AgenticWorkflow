# StockTrack

This project provides a modular agentic workflow named `stock-track-agent`.

## What it does
- Reads the editable symbol list from [stocks.txt](stocks.txt)
- Normalizes aliases (for example `NVDIA -> NVDA`, `FACEBOOK -> META`, `WDCC -> WDC`)
- Pulls market data, indicators, analyst metadata, and news
- Screens and appends up to 3 momentum candidates using relaxed price, cap, RSI, RVOL, trend, and growth rules
- Falls back to up to 2 CNN market movers when the relaxed screen returns no names
- Rewrites [stocks.txt](stocks.txt) by preserving file order, keeping pinned symbols at top only if present, and appending screened picks at the bottom
- Generates timestamped HTML and plain-text reports in [output](output)
- Includes analyst target addition versus current price and TradingView technicals for 1W/1M Summary, Oscillator, and Moving Average
- Includes interactive 1Y/4W/1W chart panels with RSI, MACD, and Bollinger bands

## Run
1. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```
2. Execute:
   ```bash
   python stock-track-agent.py
   ```

## Report sections
- Executive Summary
- Top Picks
- Overview Table
- Analyst Price Targets (Reliable Firms)
- TradingView Technicals (1W / 1M)
- Interactive Charts
- Top News By Stock
- Macro News

## Notes
- Signal Dashboard was removed from the report.
- Email sending is optional and skipped by default unless a sender module is added.

## Structure
- [stock-track-agent.py](stock-track-agent.py): entrypoint
- [stock-track-agent.txt](stock-track-agent.txt): run instructions
- [stock-track-agent/skills/SKILL.md](stock-track-agent/skills/SKILL.md)
- [stock-track-agent/skills/stock_extractor.py](stock-track-agent/skills/stock_extractor.py)
- [stock-track-agent/skills/new_extractor.py](stock-track-agent/skills/new_extractor.py)
- [stock-track-agent/skills/news_extractor.py](stock-track-agent/skills/news_extractor.py)
- [stock-track-agent/skills/html_generator.py](stock-track-agent/skills/html_generator.py)
- [stock-track-agent/skills/new_stock_tracker.py](stock-track-agent/skills/new_stock_tracker.py)
