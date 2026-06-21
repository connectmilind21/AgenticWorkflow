from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List

from html_generator import render_html_report
from new_extractor import find_top_three_candidates
from news_extractor import fetch_market_news, fetch_stock_news, now_local_string
from stock_extractor import PREFERRED_TOP_SYMBOLS, StockSnapshot, fetch_stock_snapshot, read_symbols
from tradingview_extractor import TradingViewTechnicals, fetch_tradingview_for_symbols


def _fmt_optional(value, decimals: int = 2) -> str:
    if value is None:
        return "N/A"
    try:
        return f"{float(value):.{decimals}f}"
    except Exception:
        return str(value)


def _format_text_report(
    generated_at: str,
    symbols: List[str],
    snapshots: List[StockSnapshot],
    top_picks: List[StockSnapshot],
    market_news,
    executive_summary: List[str],
    tradingview_data: Dict[str, TradingViewTechnicals],
) -> str:
    lines = []
    lines.append("Stock Track Agent Report")
    lines.append(f"Generated: {generated_at}")
    lines.append(f"Tracked symbols ({len(symbols)}): {', '.join(symbols)}")
    lines.append("")

    lines.append("Executive Summary")
    lines.append("=" * 80)
    for item in executive_summary:
        lines.append(f"- {item}")

    lines.append("")
    lines.append("Top 3 Picks")
    lines.append("=" * 80)
    if top_picks:
        for s in top_picks:
            lines.append(
                f"- {s.symbol}: 4-week change {s.four_week_change_percent:.2f}%, sector {s.sector}, market cap bucket {s.market_cap_bucket}, "
                f"consensus target {_fmt_optional(s.consensus_price_target)} ({_fmt_optional(s.consensus_upside_percent)}% upside), AI score {_fmt_optional(s.ai_score)}"
            )
    else:
        lines.append("- No stocks met all filter criteria in this run.")

    lines.append("")
    lines.append("Analyst Price Targets")
    lines.append("=" * 80)
    for s in snapshots:
        addition = (s.consensus_price_target - s.price) if s.consensus_price_target is not None else None
        lines.append(
            f"- {s.symbol}: current {_fmt_optional(s.price)}, consensus {s.consensus_rating}, "
            f"target {_fmt_optional(s.consensus_price_target)}, addition {_fmt_optional(addition)}, upside {_fmt_optional(s.consensus_upside_percent)}%"
        )
        for row in s.analyst_targets[:5]:
            target_text = f"${row['price_target']:.2f}" if row.get('price_target') is not None else "N/A"
            add_text = _fmt_optional(row.get("target_addition"))
            lines.append(
                f"  - {row.get('brokerage', 'N/A')}: {row.get('rating', 'N/A')} | {row.get('action', 'N/A')} | "
                f"target {target_text} | addition {add_text} | {row.get('upside_downside', 'N/A')}"
            )

    lines.append("")
    lines.append("Overview")
    lines.append("=" * 80)
    for s in snapshots:
        lines.append(
            f"- {s.symbol} | Sector {s.sector} | Price {s.price:.2f} | 52W H/L {s.fifty_two_week_high} / {s.fifty_two_week_low} | "
            f"MarketCap {s.market_cap:.0f} | PE {s.pe} | EPS {s.eps} | RVOL {s.technicals.get('relative_volume')} | RSI {s.rsi} | AI {_fmt_optional(s.ai_score)}"
        )

    lines.append("")
    lines.append("TradingView Technicals (1W / 1M)")
    lines.append("=" * 80)
    for s in snapshots:
        tv = tradingview_data.get(s.symbol)
        if not tv:
            lines.append(f"- {s.symbol}: No TradingView technical data available")
            continue
        lines.append(
            f"- {s.symbol}: Summary 1W {tv.summary_1w}, 1M {tv.summary_1m} | "
            f"Oscillator 1W {tv.oscillator_1w}, 1M {tv.oscillator_1m} | "
            f"MA 1W {tv.moving_average_1w}, 1M {tv.moving_average_1m}"
        )
        if tv.link:
            lines.append(f"  {tv.link}")

    lines.append("")
    lines.append("Macro News")
    lines.append("=" * 80)
    for key in [
        "overall_stock_market",
        "finance",
        "technology_ai",
        "interest_rate_housing",
        "cpi_labor_ppi",
        "global_war",
        "india_top_5",
        "world_top_5",
    ]:
        lines.append(f"{key}:")
        for item in market_news.get(key, []):
            lines.append(f"- {item.title} ({item.source})")
            if item.link:
                lines.append(f"  {item.link}")

    return "\n".join(lines)


def _build_executive_summary(snapshots: List[StockSnapshot], top_picks: List[StockSnapshot]) -> List[str]:
    gains = sum(1 for s in snapshots if s.change_percent > 0)
    losses = len(snapshots) - gains
    top = sorted(snapshots, key=lambda s: s.change_percent, reverse=True)[:3]
    lead = ", ".join(f"{s.symbol} ({s.change_percent:.2f}%)" for s in top) if top else "N/A"

    summary = [
        f"Tracked basket is mixed with {gains} gainers and {losses} decliners.",
        f"Top daily movers: {lead}.",
        "Rates, inflation, labor data, and geopolitical headlines remain key macro drivers.",
        "Crypto trend is represented through BTC-USD, ETH-USD, and SOL-USD in the same report.",
    ]

    if top_picks:
        summary.append(f"Momentum screening found {len(top_picks)} candidate(s) using the relaxed price, cap, RSI, RVOL, and growth filters.")
    else:
        summary.append("Momentum screening found no new names satisfying all strict filters today.")

    return summary


def _rewrite_stocks_file(stocks_file: Path, ordered_symbols: List[str], top_picks: List[StockSnapshot]) -> List[str]:
    existing = []
    for s in ordered_symbols:
        if s not in existing:
            existing.append(s)

    pinned = [symbol for symbol in PREFERRED_TOP_SYMBOLS if symbol in existing]
    remaining = [symbol for symbol in existing if symbol not in pinned]

    picks = [p.symbol for p in top_picks if p.symbol not in pinned and p.symbol not in remaining]
    new_order = pinned + remaining + picks

    body = []
    body.append("# Editable symbol list for stock-track-agent")
    body.append("# You can add, remove, or reorder symbols manually.")
    body.append("# This workflow preserves the file order, keeps pinned symbols at the top, and appends screened picks at the bottom.")
    body.extend(new_order)
    stocks_file.write_text("\n".join(body) + "\n", encoding="utf-8")
    return new_order


def run_stock_track_agent(root: Path) -> None:
    output_dir = root / "output"
    stocks_file = root / "stocks.txt"
    output_dir.mkdir(exist_ok=True)

    symbols = read_symbols(stocks_file)

    snapshots: List[StockSnapshot] = []
    for symbol in symbols:
        try:
            snapshots.append(fetch_stock_snapshot(symbol))
        except Exception as exc:
            print(f"Skipping {symbol}: {exc}")

    if not snapshots:
        raise RuntimeError("No stock data available from stocks.txt")

    top_picks = find_top_three_candidates([s.symbol for s in snapshots])

    # Preserve the current stocks.txt order while still appending screened picks at the bottom.
    ordered_base = [symbol for symbol in symbols if symbol in {snapshot.symbol for snapshot in snapshots}]
    updated_symbols = _rewrite_stocks_file(stocks_file, ordered_base, top_picks)

    # Ensure snapshots include any newly added top picks.
    existing_symbols = {s.symbol for s in snapshots}
    for pick in top_picks:
        if pick.symbol not in existing_symbols:
            snapshots.append(pick)

    snapshots.sort(key=lambda x: updated_symbols.index(x.symbol) if x.symbol in updated_symbols else 9999)

    stock_news: Dict[str, list] = {}
    for s in snapshots:
        stock_news[s.symbol] = fetch_stock_news(s.symbol, limit=2)

    market_news = fetch_market_news()
    tradingview_data = fetch_tradingview_for_symbols([s.symbol for s in snapshots])
    generated_at = now_local_string()
    executive_summary = _build_executive_summary(snapshots, top_picks)

    html_report = render_html_report(
        generated_at=generated_at,
        symbols=updated_symbols,
        snapshots=snapshots,
        top_picks=top_picks,
        stock_news=stock_news,
        market_news=market_news,
        executive_summary=executive_summary,
        tradingview_data=tradingview_data,
    )

    text_report = _format_text_report(
        generated_at=generated_at,
        symbols=updated_symbols,
        snapshots=snapshots,
        top_picks=top_picks,
        market_news=market_news,
        executive_summary=executive_summary,
        tradingview_data=tradingview_data,
    )

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_path = output_dir / f"stock-track-agent_report_{stamp}.html"
    txt_path = output_dir / f"stock-track-agent_report_{stamp}.txt"

    html_path.write_text(html_report, encoding="utf-8")
    txt_path.write_text(text_report, encoding="utf-8")

    print(f"Saved HTML report: {html_path}")
    print(f"Saved text report: {txt_path}")
    print("Email is optional. SMTP sending is skipped in this modular workflow unless a sender module is added.")
