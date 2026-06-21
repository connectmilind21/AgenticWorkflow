---
name: stock-track-agent
description: Modular workflow to run stock-track-agent, update stocks.txt, screen momentum picks, and generate executive HTML/text reports with analyst and TradingView technical sections.
---

# Stock Track Agent Skill

Use this skill when the user asks to run stock-track-agent, generate a stock report, or maintain the stock workflow structure.

## Copilot Instructions
- Treat [stocks.txt](../../stocks.txt) as the user-controlled list of tracked symbols.
- If the user says "run stock-track-agent" or asks for a stock report, run [stock-track-agent.py](../../stock-track-agent.py) and generate report files in the output folder.
- Prefer [stock-track-agent/skills/SKILL.md](SKILL.md) as the canonical skill definition for the stock report workflow.
- When asked to produce a finance report, use the workflow in [stock-track-agent.py](../../stock-track-agent.py).
- Prefer clear, structured outputs that can be saved as HTML or plain text.
- If the user asks for market/news updates, include both stock-specific and broad market topics.
- Always include a clear executive summary at the top of the report covering U.S. market, India, world, crypto, finance, interest rates, housing, CPI, and job-market themes.
- If email settings are missing, explain that email is optional and skip sending.
- Never request, store, print, or transmit passwords, tokens, API keys, or other confidential information.
- Do not send confidential laptop data to external services or the internet.
- If a secret appears, redact it immediately and do not include it in reports or logs.
- Only use public market/news data for the report.

## Workflow
1. Read symbols from stocks.txt.
2. Normalize aliases and fetch market data for each symbol.
3. Run relaxed screener rules to find top 3 additional stocks.
4. If no screened names qualify, fall back to up to 2 CNN market movers.
5. Rewrite tracked symbols by preserving file order, keeping pinned symbols at top only if present, and appending top picks.
6. Fetch stock-specific and macro news.
7. Fetch TradingView technical recommendations (1W/1M).
8. Generate HTML and plain-text reports in output/.

## Input
- stocks.txt is the editable source of tracked symbols.
- Users can add, remove, or reorder symbols manually.

## Data Processing
- Find up to 3 additional stocks that satisfy relaxed market-cap, sector, price, RSI, RVOL, growth, and momentum rules.
- Keep pinned symbols at top only when they already exist in the tracked list.
- Include stock-specific news and broad macro news.

## Output
- Write HTML and text reports to output/.
- Include executive summary, top picks, overview tables, analyst price target table with target addition, TradingView technicals (summary/oscillator/MA for 1W and 1M), interactive charts, and macro news.
- Do not include Signal Dashboard (removed).

## Safety
- Use only public market/news sources.
- Never request or print credentials.
- If external providers fail, continue with available data and clearly mark unavailable fields.