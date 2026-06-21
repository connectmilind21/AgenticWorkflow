from __future__ import annotations

from html import escape
from typing import Dict, List

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from news_extractor import NewsItem
from stock_extractor import StockSnapshot
from tradingview_extractor import TradingViewTechnicals


def _fmt_num(value) -> str:
    if value is None:
        return "N/A"
    try:
        return f"{float(value):,.2f}"
    except Exception:
        return str(value)


def _fmt_pct(value) -> str:
    if value is None:
        return "N/A"
    try:
        return f"{float(value):,.2f}%"
    except Exception:
        return str(value)


def _fmt_large(value) -> str:
    if value is None:
        return "N/A"
    try:
        n = float(value)
    except Exception:
        return str(value)
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    return f"{n:,.0f}"


def _timeframe_chart(snapshot: StockSnapshot, days: int, title: str) -> str:
    df = snapshot.history_1y.tail(days).copy()
    if df.empty:
        return ""

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.62, 0.18, 0.20])
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Price",
            increasing_line_color="#16a34a",
            decreasing_line_color="#dc2626",
            showlegend=False,
        ),
        row=1,
        col=1,
    )
    fig.add_trace(go.Scatter(x=df.index, y=df["BB_UPPER"], mode="lines", line=dict(color="#0ea5e9", width=1), showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["BB_MID"], mode="lines", line=dict(color="#64748b", width=1), showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["BB_LOWER"], mode="lines", line=dict(color="#0ea5e9", width=1), showlegend=False), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], mode="lines", line=dict(color="#f97316", width=1.6), showlegend=False), row=2, col=1)
    fig.add_hline(y=70, row=2, col=1, line=dict(color="#ef4444", dash="dash", width=1))
    fig.add_hline(y=30, row=2, col=1, line=dict(color="#22c55e", dash="dash", width=1))

    fig.add_trace(go.Bar(x=df.index, y=df["MACD_HIST"], marker_color="#a78bfa", showlegend=False), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], mode="lines", line=dict(color="#2563eb", width=1.4), showlegend=False), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD_SIGNAL"], mode="lines", line=dict(color="#f43f5e", width=1.4), showlegend=False), row=3, col=1)

    fig.update_layout(
        title=title,
        height=360,
        margin=dict(l=8, r=8, t=30, b=8),
        template="plotly_white",
        paper_bgcolor="#f8fafc",
        plot_bgcolor="#f8fafc",
    )

    return fig.to_html(full_html=False, include_plotlyjs="cdn", config={"responsive": True, "displayModeBar": True})


def _render_news_list(items: List[NewsItem]) -> str:
    if not items:
        return "<li>No data available.</li>"
    return "".join(
        f"<li><strong>{escape(item.title)}</strong><br><span>{escape(item.source)}</span><br><a href='{escape(item.link, quote=True)}'>{escape(item.link)}</a></li>"
        for item in items
    )


def _format_target_rows(snapshot: StockSnapshot) -> str:
    if not snapshot.analyst_targets:
        return "<li>No reliable firm target found.</li>"

    rows = []
    for row in snapshot.analyst_targets:
        brokerage = escape(str(row.get("brokerage") or "N/A"))
        rating = escape(str(row.get("rating") or "N/A"))
        action = escape(str(row.get("action") or "N/A"))
        target = _fmt_num(row.get("price_target"))
        addition = _fmt_num(row.get("target_addition"))
        rows.append(
            f"<li><strong>{brokerage}</strong><br>"
            f"Rating: {rating} | Action: {action}<br>"
            f"Target: {target} | Addition to current: {addition}</li>"
        )
    return "".join(rows)


def render_html_report(
    generated_at: str,
    symbols: List[str],
    snapshots: List[StockSnapshot],
    top_picks: List[StockSnapshot],
    stock_news: Dict[str, List[NewsItem]],
    market_news: Dict[str, List[NewsItem]],
    executive_summary: List[str],
    tradingview_data: Dict[str, TradingViewTechnicals],
) -> str:
    summary_html = "".join(f"<li>{escape(line)}</li>" for line in executive_summary)

    picks_html = "".join(
        f"<div class='pick-card'><h3>{escape(p.symbol)} ({escape(p.market_cap_bucket)})</h3>"
        f"<p>4-week move: <strong>{_fmt_pct(p.four_week_change_percent)}</strong></p>"
        f"<p>Sector: {escape(p.sector)} | Price: {_fmt_num(p.price)} | Market Cap: {_fmt_large(p.market_cap)}</p>"
        f"<p>Consensus target: <strong>{_fmt_num(p.consensus_price_target)}</strong> | Addition: {_fmt_num((p.consensus_price_target - p.price) if p.consensus_price_target is not None else None)}</p>"
        f"</div>"
        for p in top_picks
    ) or "<p>No stocks met all screening criteria in this run.</p>"

    overview_rows = "".join(
        "<tr>"
        f"<td>{escape(s.symbol)}</td>"
        f"<td>{escape(s.sector)}</td>"
        f"<td>{_fmt_num(s.price)}</td>"
        f"<td>{_fmt_num(s.fifty_two_week_high)}</td>"
        f"<td>{_fmt_num(s.fifty_two_week_low)}</td>"
        f"<td>{_fmt_large(s.market_cap)}</td>"
        f"<td>{_fmt_num(s.pe)}</td>"
        f"<td>{_fmt_num(s.eps)}</td>"
        f"<td>{_fmt_num(s.consensus_price_target)}</td>"
        f"<td>{_fmt_num((s.consensus_price_target - s.price) if s.consensus_price_target is not None else None)}</td>"
        f"<td>{_fmt_pct(s.consensus_upside_percent)}</td>"
        "</tr>"
        for s in snapshots
    )

    recommendations_rows = "".join(
        "<tr>"
        f"<td>{escape(s.symbol)}</td>"
        f"<td>{_fmt_num(s.price)}</td>"
        f"<td>{_fmt_num(s.consensus_price_target)}</td>"
        f"<td>{_fmt_num((s.consensus_price_target - s.price) if s.consensus_price_target is not None else None)}</td>"
        f"<td>{_fmt_pct(s.consensus_upside_percent)}</td>"
        f"<td>{escape(s.consensus_rating)}</td>"
        f"<td><ul class='inline-list'>{_format_target_rows(s)}</ul></td>"
        "</tr>"
        for s in snapshots
    )

    tv_rows = ""
    for s in snapshots:
        tv = tradingview_data.get(s.symbol)
        if tv is None:
            tv_rows += (
                "<tr>"
                f"<td>{escape(s.symbol)}</td><td>N/A</td><td>N/A</td><td>N/A</td><td>N/A</td><td>N/A</td><td>N/A</td><td>N/A</td>"
                "</tr>"
            )
            continue

        link_html = f"<a href='{escape(tv.link, quote=True)}'>TradingView</a>" if tv.link else "N/A"
        tv_rows += (
            "<tr>"
            f"<td>{escape(tv.symbol)}</td>"
            f"<td>{escape(tv.tradingview_ticker)}</td>"
            f"<td>{escape(tv.summary_1w)}</td>"
            f"<td>{escape(tv.summary_1m)}</td>"
            f"<td>{escape(tv.oscillator_1w)}</td>"
            f"<td>{escape(tv.oscillator_1m)}</td>"
            f"<td>{escape(tv.moving_average_1w)}</td>"
            f"<td>{escape(tv.moving_average_1m)}</td>"
            f"<td>{link_html}</td>"
            "</tr>"
        )

    charts_html = []
    for s in snapshots:
        c1 = _timeframe_chart(s, 252, f"{s.symbol} - 1Y")
        c2 = _timeframe_chart(s, 20, f"{s.symbol} - 4W")
        c3 = _timeframe_chart(s, 5, f"{s.symbol} - 1W")
        legend = (
            f"<div class='legend'><h4>{escape(s.symbol)} Details</h4>"
            f"<p>Sector: {escape(s.sector)}</p>"
            f"<p>Price: {_fmt_num(s.price)} | Change: {_fmt_pct(s.change_percent)} | Volume: {_fmt_large(s.volume)}</p>"
            f"<p>Market Cap: {_fmt_large(s.market_cap)} | 52W: {_fmt_num(s.fifty_two_week_low)} - {_fmt_num(s.fifty_two_week_high)}</p>"
            f"<p>RSI: {_fmt_num(s.rsi)} | MACD: {_fmt_num(s.macd)} / {_fmt_num(s.macd_signal)}</p>"
            f"<p>150d MA: {_fmt_num(s.ma_150)} | 50d MA: {_fmt_num(s.ma_50)} | 21 EMA: {_fmt_num(s.ema_21)}</p>"
            "</div>"
        )
        charts_html.append(
            "<section class='stock-chart-block'>"
            f"<h3>{escape(s.symbol)} Interactive Panels</h3>"
            "<div class='chart-row'>"
            f"<div class='chart'>{c1}</div><div class='chart'>{c2}</div><div class='chart'>{c3}</div>{legend}"
            "</div>"
            "</section>"
        )

    stock_news_html = "".join(
        f"<h4>{escape(symbol)}</h4><ul>{_render_news_list(items)}</ul>" for symbol, items in stock_news.items()
    )

    market_blocks = []
    for key, title in [
        ("overall_stock_market", "Top 2 Overall Stock Market News"),
        ("finance", "Top 2 Finance News"),
        ("technology_ai", "Top 2 Technology/AI News"),
        ("interest_rate_housing", "Top 2 Interest Rate/Housing News"),
        ("cpi_labor_ppi", "Top 2 CPI/Labor/PPI News"),
        ("global_war", "Top 2 Global War News"),
        ("india_top_5", "Top 5 India News"),
        ("world_top_5", "Top 5 World News"),
    ]:
        market_blocks.append(f"<h4>{title}</h4><ul>{_render_news_list(market_news.get(key, []))}</ul>")

    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset='utf-8'>
  <title>Stock Track Agent Report</title>
  <style>
    :root {{
      --bg-1: #f9fafb;
      --bg-2: #e2e8f0;
      --accent-1: #0ea5e9;
      --ink: #0f172a;
      --card: #ffffff;
      --line: #cbd5e1;
    }}
    body {{ margin: 0; font-family: "Segoe UI", Tahoma, sans-serif; color: var(--ink); background: radial-gradient(circle at 20% 0%, #e0f2fe 0%, var(--bg-1) 45%, var(--bg-2) 100%); }}
    .container {{ max-width: 1500px; margin: 0 auto; padding: 20px; }}
    .panel {{ background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 18px; margin-bottom: 18px; box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08); }}
    h1 {{ margin-top: 0; font-size: 32px; }}
    h2 {{ border-left: 6px solid var(--accent-1); padding-left: 10px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border: 1px solid var(--line); padding: 8px; font-size: 12px; vertical-align: top; }}
    th {{ background: #dbeafe; }}
    .pick-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }}
    .pick-card {{ border: 1px solid var(--line); border-radius: 10px; padding: 12px; background: linear-gradient(140deg, #ffffff, #f8fafc); }}
    .stock-chart-block {{ border-top: 2px solid #dbeafe; padding-top: 12px; margin-top: 12px; }}
    .chart-row {{ display: grid; grid-template-columns: 1fr 1fr 1fr 300px; gap: 8px; align-items: start; }}
    .chart {{ border: 1px solid var(--line); border-radius: 10px; overflow: hidden; background: #f8fafc; }}
    .legend {{ border: 1px solid var(--line); border-radius: 10px; padding: 10px; background: #f8fafc; font-size: 12px; }}
    .inline-list {{ margin: 0; padding-left: 18px; }}
    @media (max-width: 1280px) {{
      .chart-row {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class='container'>
    <div class='panel'>
      <h1>Stock Track Agent Executive Report</h1>
      <p>Generated: {escape(generated_at)}</p>
      <p>Tracked symbols ({len(symbols)}): {escape(', '.join(symbols))}</p>
      <h2>Executive Summary</h2>
      <ul>{summary_html}</ul>
    </div>

    <div class='panel'>
      <h2>Top Picks</h2>
      <div class='pick-grid'>{picks_html}</div>
    </div>

    <div class='panel'>
      <h2>Overview Table</h2>
      <table>
        <thead><tr><th>Symbol</th><th>Sector</th><th>Current Price</th><th>52W High</th><th>52W Low</th><th>Market Cap</th><th>P/E</th><th>EPS</th><th>Consensus Target</th><th>Target Addition</th><th>Upside</th></tr></thead>
        <tbody>{overview_rows}</tbody>
      </table>
    </div>

    <div class='panel'>
      <h2>Analyst Price Targets (Reliable Firms)</h2>
      <table>
        <thead><tr><th>Symbol</th><th>Current Price</th><th>Consensus Target</th><th>Target Addition</th><th>Upside</th><th>Consensus Rating</th><th>Reliable Firm Targets</th></tr></thead>
        <tbody>{recommendations_rows}</tbody>
      </table>
    </div>

    <div class='panel'>
      <h2>TradingView Technicals (1W / 1M)</h2>
      <table>
        <thead><tr><th>Symbol</th><th>TradingView Ticker</th><th>Summary 1W</th><th>Summary 1M</th><th>Oscillator 1W</th><th>Oscillator 1M</th><th>Moving Average 1W</th><th>Moving Average 1M</th><th>Link</th></tr></thead>
        <tbody>{tv_rows}</tbody>
      </table>
    </div>

    <div class='panel'>
      <h2>Interactive Charts (1Y, 4W, 1W + RSI + MACD + Bollinger)</h2>
      {''.join(charts_html)}
    </div>

    <div class='panel'>
      <h2>Top News By Stock</h2>
      {stock_news_html}
    </div>

    <div class='panel'>
      <h2>Macro News</h2>
      {''.join(market_blocks)}
    </div>
  </div>
</body>
</html>
"""
