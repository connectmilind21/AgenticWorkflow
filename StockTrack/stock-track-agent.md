# stock-track-agent

## Trigger
- User asks to run stock-track-agent or generate a stock report.

## Command
```bash
python stock-track-agent.py
```

## Current behavior
1. Reads tracked symbols from stocks.txt.
2. Normalizes aliases (for example: NVDIA -> NVDA, FACEBOOK -> META, WDCC -> WDC).
3. Fetches snapshots with price, indicators, fundamentals, analyst metadata, and history.
4. Screens up to 3 momentum candidates using relaxed constraints.
5. If the screen returns none, falls back to up to 2 CNN market movers.
6. Rewrites stocks.txt by preserving file order, keeping pinned symbols at top only when present, and appending picks at the bottom.
7. Fetches stock news, macro news, and TradingView technical recommendations.
8. Generates timestamped HTML and TXT reports in output/.

## Report sections
- Executive Summary
- Top Picks
- Overview Table
- Analyst Price Targets (Reliable Firms)
- TradingView Technicals (1W / 1M)
- Interactive Charts (1Y / 4W / 1W with RSI, MACD, Bollinger)
- Top News By Stock
- Macro News

## Important updates reflected
- Signal Dashboard removed.
- Analyst section includes target addition versus current price.
- TradingView section includes Summary, Oscillator, and Moving Average for 1W and 1M.
- Email sending is optional and skipped by default unless a sender module is added.
