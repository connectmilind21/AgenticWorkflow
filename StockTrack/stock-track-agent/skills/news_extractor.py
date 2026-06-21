from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List

import feedparser
import requests

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

LOW_NOISE_NEWS_SYMBOLS = {"NAIL", "DPST", "SPY", "QQQ", "INTC", "BTC-USD", "ETH-USD"}


@dataclass
class NewsItem:
    title: str
    link: str
    source: str
    published: str


def fetch_google_news(query: str, limit: int) -> List[NewsItem]:
    url = "https://news.google.com/rss/search?q=" + requests.utils.quote(query)
    try:
        response = requests.get(url, timeout=20, headers=REQUEST_HEADERS)
        response.raise_for_status()
    except Exception:
        return []

    parsed = feedparser.parse(response.content)
    out: List[NewsItem] = []
    for entry in parsed.entries[:limit]:
        source = "Google News"
        if isinstance(entry.get("source"), dict):
            source = entry.get("source", {}).get("title") or source
        published = entry.get("published") or entry.get("updated") or ""
        if published:
            published = published.strip()
        out.append(
            NewsItem(
                title=(entry.get("title") or "").strip(),
                link=entry.get("link") or "",
                source=source,
                published=published,
            )
        )
    return [n for n in out if n.title]


def fetch_stock_news(symbol: str, limit: int = 2) -> List[NewsItem]:
    normalized = symbol.strip().upper().replace(" ", "")
    adjusted_limit = 1 if normalized in LOW_NOISE_NEWS_SYMBOLS else limit
    return fetch_google_news(f"{symbol} stock news", limit=adjusted_limit)


def fetch_market_news() -> Dict[str, List[NewsItem]]:
    return {
        "overall_stock_market": fetch_google_news("US stock market outlook", 2),
        "finance": fetch_google_news("finance market update", 2),
        "technology_ai": fetch_google_news("technology AI market news", 2),
        "interest_rate_housing": fetch_google_news("interest rates housing market Federal Reserve", 2),
        "cpi_labor_ppi": fetch_google_news("CPI labor market PPI report", 2),
        "global_war": fetch_google_news("global war geopolitical risk markets", 2),
        "india_top_5": fetch_google_news("India markets economy technology news", 5),
        "world_top_5": fetch_google_news("world economy global markets top news", 5),
    }


def now_local_string() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
