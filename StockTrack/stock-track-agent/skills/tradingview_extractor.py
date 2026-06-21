from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import requests

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

SCAN_URLS = [
    "https://scanner.tradingview.com/america/scan",
    "https://scanner.tradingview.com/crypto/scan",
]


@dataclass
class TradingViewTechnicals:
    symbol: str
    tradingview_ticker: str
    summary_1w: str
    summary_1m: str
    oscillator_1w: str
    oscillator_1m: str
    moving_average_1w: str
    moving_average_1m: str
    link: str


def _rating_label(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    if value <= -0.5:
        return "Strong Sell"
    if value < -0.1:
        return "Sell"
    if value < 0.1:
        return "Neutral"
    if value < 0.5:
        return "Buy"
    return "Strong Buy"


def _to_tradingview_candidates(symbol: str) -> List[str]:
    normalized = symbol.strip().upper()
    if normalized.endswith("-USD"):
        return [f"CRYPTO:{normalized.replace('-USD', 'USD')}"]
    if normalized.startswith("^"):
        return []

    return [
        f"NASDAQ:{normalized}",
        f"NYSE:{normalized}",
        f"AMEX:{normalized}",
        f"NYSEARCA:{normalized}",
    ]


def _build_link(tv_ticker: str) -> str:
    if ":" not in tv_ticker:
        return ""
    exchange, raw_symbol = tv_ticker.split(":", 1)
    return f"https://www.tradingview.com/symbols/{exchange}-{raw_symbol}/technicals/"


def fetch_tradingview_technicals(symbol: str) -> TradingViewTechnicals:
    candidates = _to_tradingview_candidates(symbol)
    if not candidates:
        return TradingViewTechnicals(
            symbol=symbol,
            tradingview_ticker="N/A",
            summary_1w="N/A",
            summary_1m="N/A",
            oscillator_1w="N/A",
            oscillator_1m="N/A",
            moving_average_1w="N/A",
            moving_average_1m="N/A",
            link="",
        )

    payload = {
        "symbols": {"tickers": candidates, "query": {"types": []}},
        "columns": [
            "Recommend.All|1W",
            "Recommend.All|1M",
            "Recommend.Other|1W",
            "Recommend.Other|1M",
            "Recommend.MA|1W",
            "Recommend.MA|1M",
        ],
    }

    for url in SCAN_URLS:
        try:
            response = requests.post(url, json=payload, timeout=20, headers=REQUEST_HEADERS)
            response.raise_for_status()
            body = response.json()
        except Exception:
            continue

        data = body.get("data") or []
        if not data:
            continue

        row = data[0]
        ticker = str(row.get("s") or candidates[0])
        values = row.get("d") or []

        def _v(idx: int) -> Optional[float]:
            if idx >= len(values):
                return None
            try:
                return float(values[idx])
            except Exception:
                return None

        return TradingViewTechnicals(
            symbol=symbol,
            tradingview_ticker=ticker,
            summary_1w=_rating_label(_v(0)),
            summary_1m=_rating_label(_v(1)),
            oscillator_1w=_rating_label(_v(2)),
            oscillator_1m=_rating_label(_v(3)),
            moving_average_1w=_rating_label(_v(4)),
            moving_average_1m=_rating_label(_v(5)),
            link=_build_link(ticker),
        )

    return TradingViewTechnicals(
        symbol=symbol,
        tradingview_ticker="N/A",
        summary_1w="N/A",
        summary_1m="N/A",
        oscillator_1w="N/A",
        oscillator_1m="N/A",
        moving_average_1w="N/A",
        moving_average_1m="N/A",
        link="",
    )


def fetch_tradingview_for_symbols(symbols: List[str]) -> Dict[str, TradingViewTechnicals]:
    results: Dict[str, TradingViewTechnicals] = {}
    for symbol in symbols:
        results[symbol] = fetch_tradingview_technicals(symbol)
    return results
