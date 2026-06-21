from __future__ import annotations

import re
from typing import Dict, List

import pandas as pd
import requests

from typing import Dict, List

from stock_extractor import StockSnapshot, fetch_stock_snapshot

# Curated, non-pharma leaning universe for scanning low-price momentum names.
SCREEN_UNIVERSE = [
    "PLUG", "SOFI", "RUN", "CLSK", "JOBY", "DNA", "RKLB", "OPEN", "QS", "BE",
    "ACHR", "WULF", "RIOT", "MARA", "ASTS", "RGTI", "QBTS", "IONQ", "U", "SOUN",
    "KULR", "MVIS", "LCID", "NIO", "FUBO", "CHPT", "LUNR", "BBAI", "GRAB", "HIMS",
    "JMIA", "AI", "PINS", "AFRM", "SNAP", "HOOD", "CRSR", "XPEV", "CCL", "RCL",
]


def _is_pharma(sector: str) -> bool:
    lowered = sector.lower()
    return "pharma" in lowered or "biotech" in lowered or "drug" in lowered


def _score_snapshot(snapshot: StockSnapshot) -> float:
    score = 0.0

    if snapshot.price >= 2 and snapshot.price <= 50:
        score += 15
    if snapshot.four_week_change_percent > 25:
        score += 20
    if snapshot.rsi is not None and 50 <= snapshot.rsi <= 75:
        score += 10
    if snapshot.technicals.get("relative_volume") is not None and snapshot.technicals["relative_volume"] > 1.2:
        score += 12
    if snapshot.fundamentals.get("revenue_growth") is not None and snapshot.fundamentals["revenue_growth"] > 10:
        score += 15
    if snapshot.technicals.get("above_50dma"):
        score += 8
    if snapshot.technicals.get("above_200dma"):
        score += 8
    if snapshot.consensus_upside_percent is not None and snapshot.consensus_upside_percent > 10:
        score += 6
    if snapshot.ai_score is not None:
        score += snapshot.ai_score * 0.15

    return score


def _fetch_cnn_premarket_picks(existing_symbols: List[str]) -> List[StockSnapshot]:
    url = "https://www.cnn.com/markets"
    try:
        response = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
    except Exception:
        return []

    try:
        tables = pd.read_html(response.text)
    except Exception:
        tables = []

    candidates: List[str] = []
    for table in tables:
        if table.empty:
            continue
        for value in table.astype(str).head(10).stack().tolist():
            token = str(value).strip().split()[0] if str(value).strip() else ""
            if re.fullmatch(r"[A-Z0-9][A-Z0-9\-\.]{1,9}", token) and token not in candidates:
                candidates.append(token)
            if len(candidates) >= 2:
                break
        if len(candidates) >= 2:
            break

    picks: List[StockSnapshot] = []
    for symbol in candidates:
        if symbol in existing_symbols:
            continue
        try:
            picks.append(fetch_stock_snapshot(symbol))
        except Exception:
            continue
        if len(picks) >= 2:
            break
    return picks[:2]


def find_top_three_candidates(existing_symbols: List[str]) -> List[StockSnapshot]:
    picks: List[StockSnapshot] = []
    existing = set(existing_symbols)

    for symbol in SCREEN_UNIVERSE:
        if symbol in existing:
            continue
        try:
            snap = fetch_stock_snapshot(symbol)
        except Exception:
            continue

        if snap.market_cap < 300_000_000 or snap.market_cap > 50_000_000_000:
            continue
        if _is_pharma(snap.sector):
            continue
        if snap.price < 2 or snap.price > 50:
            continue
        if snap.four_week_change_percent <= 25:
            continue
        if snap.rsi is not None and not (50 <= snap.rsi <= 75):
            continue
        if snap.technicals.get("relative_volume") is not None and snap.technicals["relative_volume"] <= 1.2:
            continue
        if snap.fundamentals.get("revenue_growth") is not None and snap.fundamentals["revenue_growth"] <= 10:
            continue

        picks.append(snap)

    picks.sort(key=_score_snapshot, reverse=True)

    # Keep category diversity when possible.
    selected: List[StockSnapshot] = []
    used_caps: Dict[str, int] = {}
    for snap in picks:
        if len(selected) >= 3:
            break
        cap = snap.market_cap_bucket
        if used_caps.get(cap, 0) >= 1:
            continue
        selected.append(snap)
        used_caps[cap] = used_caps.get(cap, 0) + 1

    if len(selected) < 3:
        for snap in picks:
            if len(selected) >= 3:
                break
            if snap.symbol in {s.symbol for s in selected}:
                continue
            selected.append(snap)

    if selected:
        return selected[:3]

    return _fetch_cnn_premarket_picks(existing_symbols)
