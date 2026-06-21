from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
import re
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import yfinance as yf

PREFERRED_TOP_SYMBOLS = ["NAIL", "INTC", "BTC-USD", "ETH-USD"]
NO_FUNDAMENTALS_SYMBOLS = {
    "NAIL",
    "BTC-USD",
    "ETH-USD",
    "SOL-USD",
    "SPY",
    "QQQ",
    "FAS",
    "DPST",
    "RETL",
    "TQQQ",
    "SQQQ",
    "TECL",
    "SOXL",
    "SPXL",
    "LABU",
    "WEBL",
}

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

RELIABLE_BROKER_KEYWORDS = [
    "bank of america",
    "bofa",
    "morgan stanley",
    "goldman",
    "jpmorgan",
    "jp morgan",
    "ubs",
    "barclays",
    "citigroup",
    "citi",
    "wells fargo",
    "deutsche bank",
    "jefferies",
    "rbc",
    "royal bank",
]

SYMBOL_ALIASES = {
    "NVDIA": "NVDA",
    "FACEBOOK": "META",
    "GOOGLE": "GOOGL",
    "SPCX": "^GSPC",
    "SPX": "^GSPC",
    "TESLA": "TSLA",
    "AMAZON": "AMZN",
    "NETFLIX": "NFLX",
    "INTEL": "INTC",
    "BITCOIN": "BTC-USD",
    "ETHERM": "ETH-USD",
    "SOL": "SOL-USD",
    "MARVELL": "MRVL",
    "WDCC": "WDC",
}


@dataclass
class StockSnapshot:
    symbol: str
    sector: str
    price: float
    change_percent: float
    four_week_change_percent: float
    volume: float
    market_cap: float
    market_cap_bucket: str
    pe: Optional[float]
    eps: Optional[float]
    fifty_two_week_high: Optional[float]
    fifty_two_week_low: Optional[float]
    rsi: Optional[float]
    macd: Optional[float]
    macd_signal: Optional[float]
    ma_150: Optional[float]
    ma_50: Optional[float]
    ema_21: Optional[float]
    analyst_sources: Dict[str, str]
    analyst_targets: List[Dict[str, Any]]
    consensus_price_target: Optional[float]
    consensus_upside_percent: Optional[float]
    consensus_rating: str
    technicals: Dict[str, Any]
    fundamentals: Dict[str, Any]
    catalysts: Dict[str, Any]
    risk_flags: Dict[str, Any]
    ai_components: Dict[str, float]
    ai_score: Optional[float]
    history_1y: pd.DataFrame


def normalize_symbol(symbol: str) -> str:
    cleaned = symbol.strip().upper().replace(" ", "")
    return SYMBOL_ALIASES.get(cleaned, cleaned)


def read_symbols(path) -> List[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [normalize_symbol(line) for line in lines if line.strip() and not line.strip().startswith("#")]


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        result = float(value)
        if pd.isna(result):
            return None
        return result
    except Exception:
        return None


def _safe_percent(value: Any) -> Optional[float]:
    result = _safe_float(value)
    if result is None:
        return None
    if abs(result) <= 1.5:
        return result * 100
    return result


def _safe_date(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, (list, tuple)) and value:
        value = value[0]
    try:
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            return "N/A"
        return parsed.to_pydatetime().strftime("%Y-%m-%d")
    except Exception:
        return "N/A"


def _market_cap_bucket(market_cap: Optional[float]) -> str:
    if not market_cap:
        return "Unknown"
    if market_cap < 2_000_000_000:
        return "Small Cap"
    if market_cap < 10_000_000_000:
        return "Mid Cap"
    if market_cap < 200_000_000_000:
        return "Large Cap"
    return "Mega Cap"


def _recommendation_label_from_mean(mean_value: Optional[float]) -> str:
    if mean_value is None:
        return "N/A"
    if mean_value <= 1.5:
        return f"Strong Buy ({mean_value:.2f})"
    if mean_value <= 2.5:
        return f"Buy ({mean_value:.2f})"
    if mean_value <= 3.5:
        return f"Hold ({mean_value:.2f})"
    if mean_value <= 4.5:
        return f"Sell ({mean_value:.2f})"
    return f"Strong Sell ({mean_value:.2f})"


def _first_non_empty(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text and text.lower() not in {"nan", "none", "n/a", "na"}:
            return text
    return "N/A"


def _format_recommendation_frame(frame: Any) -> str:
    if frame is None:
        return "N/A"
    try:
        if isinstance(frame, pd.DataFrame) and not frame.empty:
            latest = frame.tail(1).iloc[0]
            parts = []
            for key in latest.index:
                value = latest.get(key)
                if pd.notna(value):
                    parts.append(f"{key}: {value}")
            return "; ".join(parts) if parts else "N/A"
    except Exception:
        pass
    return "N/A"


def _marketbeat_exchange_slug(info: Dict[str, Any], symbol: str) -> Optional[str]:
    normalized = normalize_symbol(symbol)
    if normalized.startswith("^") or normalized.endswith("-USD"):
        return None

    exchange = _first_non_empty(info.get("exchange"), info.get("fullExchangeName"), "").upper()
    candidates = []
    if "NASDAQ" in exchange or "NMS" in exchange:
        candidates.append("NASDAQ")
    if "NYSE" in exchange or "NYQ" in exchange:
        candidates.append("NYSE")
    if "AMEX" in exchange or "ARCA" in exchange:
        candidates.append("AMEX")

    if normalized in {"SPY", "QQQ", "DPST", "FAS", "RETL", "TQQQ", "SQQQ", "TECL", "SOXL", "SPXL", "LABU", "WEBL"}:
        candidates.extend(["NYSEARCA", "NYSE"])

    candidates.extend(["NASDAQ", "NYSE", "NYSEARCA", "AMEX"])
    for candidate in candidates:
        if candidate:
            return candidate
    return None


def _extract_price_target_number(text: Any) -> Optional[float]:
    cleaned = str(text or "")
    matches = re.findall(r"\$([0-9]+(?:\.[0-9]+)?)", cleaned)
    if matches:
        return _safe_float(matches[-1])
    matches = re.findall(r"([0-9]+(?:\.[0-9]+)?)", cleaned)
    return _safe_float(matches[-1]) if matches else None


def _is_reliable_brokerage(name: str) -> bool:
    lowered = name.lower()
    return any(keyword in lowered for keyword in RELIABLE_BROKER_KEYWORDS)


def _parse_marketbeat_price_targets(symbol: str, info: Dict[str, Any], current_price: Optional[float]) -> List[Dict[str, Any]]:
    slug = _marketbeat_exchange_slug(info, symbol)
    if not slug:
        return []

    url = f"https://www.marketbeat.com/stocks/{slug}/{symbol}/forecast/"
    try:
        response = requests.get(url, timeout=20, headers=REQUEST_HEADERS)
        response.raise_for_status()
    except Exception:
        return []

    try:
        tables = pd.read_html(response.text)
    except Exception:
        return []

    rows: List[Dict[str, Any]] = []
    for table in tables:
        column_map = {str(column).strip().lower(): column for column in table.columns}
        if "brokerage" not in column_map or "price target" not in column_map:
            continue

        for _, row in table.iterrows():
            brokerage = _first_non_empty(row.get(column_map.get("brokerage")), row.get("brokerage"))
            if not brokerage or "subscribe" in brokerage.lower():
                continue

            analyst = _first_non_empty(row.get(column_map.get("analyst")), row.get("analyst"))
            action = _first_non_empty(row.get(column_map.get("action")), row.get("action"))
            rating = _first_non_empty(row.get(column_map.get("rating")), row.get("rating"))
            price_target_text = row.get(column_map.get("price target"))
            target_price = _extract_price_target_number(price_target_text)
            if target_price is None or target_price <= 0:
                continue
            upside_text = _first_non_empty(
                row.get(column_map.get("report date upside/downside")),
                row.get(column_map.get("upside/downside")),
            )
            target_addition = (target_price - current_price) if current_price not in (None, 0) else None

            rows.append(
                {
                    "brokerage": brokerage,
                    "analyst": analyst,
                    "action": action,
                    "rating": rating,
                    "price_target": target_price,
                    "target_addition": target_addition,
                    "upside_downside": upside_text,
                }
            )

        if rows:
            break

    unique_rows: List[Dict[str, Any]] = []
    seen = set()
    for row in rows:
        key = row["brokerage"].lower()
        if key in seen:
            continue
        seen.add(key)
        unique_rows.append(row)

    reliable_rows = [row for row in unique_rows if _is_reliable_brokerage(row["brokerage"])]
    if reliable_rows:
        return reliable_rows[:5]
    return unique_rows[:5]


def build_analyst_sources(ticker: yf.Ticker, info: Dict[str, Any]) -> Dict[str, str]:
    mean = _safe_float(info.get("recommendationMean"))
    target_mean = _safe_float(info.get("targetMeanPrice"))
    current_price = _safe_float(info.get("currentPrice")) or _safe_float(info.get("regularMarketPrice"))
    consensus_upside = None
    if target_mean is not None and current_price not in (None, 0):
        consensus_upside = ((target_mean - current_price) / current_price) * 100

    rating_count = _first_non_empty(info.get("numberOfAnalystOpinions"), info.get("recommendationMean"))
    morningstar = _first_non_empty(
        info.get("morningStarRecommendation"),
        info.get("morningStarOverallRating"),
        info.get("morningStarRiskRating"),
    )
    upgrades = _format_recommendation_frame(getattr(ticker, "upgrades_downgrades", None))
    trend = _format_recommendation_frame(getattr(ticker, "recommendation_trend", None))

    return {
        "marketbeat": f"Consensus target {target_mean:,.2f} ({consensus_upside:.2f}% upside)" if consensus_upside is not None and target_mean is not None else "N/A",
        "tipranks": _recommendation_label_from_mean(mean),
        "morningstar": morningstar,
        "marketedge": upgrades if upgrades != "N/A" else trend,
        "argus": f"Analyst opinions: {rating_count}",
        "seekingalpha": _first_non_empty(info.get("recommendationKey"), trend),
    }


def compute_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def compute_macd(close: pd.Series) -> pd.DataFrame:
    ema_fast = close.ewm(span=12, adjust=False).mean()
    ema_slow = close.ewm(span=26, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    return pd.DataFrame({"MACD": macd, "Signal": signal, "Histogram": hist})


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["MA_20"] = out["Close"].rolling(window=20).mean()
    out["RSI"] = compute_rsi(out["Close"])
    macd_df = compute_macd(out["Close"])
    out["MACD"] = macd_df["MACD"]
    out["MACD_SIGNAL"] = macd_df["Signal"]
    out["MACD_HIST"] = macd_df["Histogram"]
    out["BB_MID"] = out["Close"].rolling(window=20).mean()
    std = out["Close"].rolling(window=20).std()
    out["BB_UPPER"] = out["BB_MID"] + 2 * std
    out["BB_LOWER"] = out["BB_MID"] - 2 * std
    out["MA_150"] = out["Close"].rolling(window=150).mean()
    out["MA_50"] = out["Close"].rolling(window=50).mean()
    out["MA_200"] = out["Close"].rolling(window=200).mean()
    out["EMA_21"] = out["Close"].ewm(span=21, adjust=False).mean()

    true_range = pd.concat(
        [
            out["High"] - out["Low"],
            (out["High"] - out["Close"].shift(1)).abs(),
            (out["Low"] - out["Close"].shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    out["ATR_14"] = true_range.rolling(window=14).mean()

    direction = out["Close"].diff().fillna(0)
    signed_volume = out["Volume"].fillna(0).where(direction >= 0, -out["Volume"].fillna(0))
    out["OBV"] = signed_volume.cumsum()

    spread = (out["High"] - out["Low"]).replace(0, pd.NA)
    mfm = (((out["Close"] - out["Low"]) - (out["High"] - out["Close"])) / spread).fillna(0)
    out["AD_LINE"] = (mfm * out["Volume"].fillna(0)).cumsum()
    return out


@lru_cache(maxsize=1)
def _benchmark_history() -> pd.DataFrame:
    try:
        history = yf.Ticker("^GSPC").history(period="1y", interval="1d", auto_adjust=False)
    except Exception:
        return pd.DataFrame()
    return add_indicators(history) if not history.empty else pd.DataFrame()


def _compute_relative_strength_rating(history: pd.DataFrame) -> Optional[float]:
    benchmark = _benchmark_history()
    if history.empty or benchmark.empty:
        return None

    stock_close = history["Close"].dropna()
    benchmark_close = benchmark["Close"].dropna()
    if len(stock_close) < 20 or len(benchmark_close) < 20:
        return None

    stock_return = (stock_close.iloc[-1] / stock_close.iloc[0] - 1) * 100
    benchmark_return = (benchmark_close.iloc[-1] / benchmark_close.iloc[0] - 1) * 100
    spread = stock_return - benchmark_return
    return max(1.0, min(99.0, 50.0 + spread * 2.0))


def _compute_ai_components(technicals: Dict[str, Any], fundamentals: Dict[str, Any], analyst_sources: Dict[str, str]) -> Dict[str, float]:
    trend = 40.0
    if technicals.get("above_50dma"):
        trend += 20
    if technicals.get("above_200dma"):
        trend += 20
    if technicals.get("golden_cross"):
        trend += 10
    if technicals.get("rsi") is not None and 50 <= float(technicals["rsi"]) <= 75:
        trend += 10

    fundamentals_score = 40.0
    if fundamentals.get("revenue_growth") is not None and fundamentals["revenue_growth"] > 10:
        fundamentals_score += 20
    if fundamentals.get("eps_growth") is not None and fundamentals["eps_growth"] > 10:
        fundamentals_score += 20
    if fundamentals.get("gross_margin") is not None and fundamentals["gross_margin"] > 30:
        fundamentals_score += 10
    if fundamentals.get("roe") is not None and fundamentals["roe"] > 10:
        fundamentals_score += 10
    if fundamentals.get("debt_to_equity") is not None and fundamentals["debt_to_equity"] < 200:
        fundamentals_score += 10

    volume_score = 40.0
    if technicals.get("relative_volume") is not None:
        volume_score += min(25.0, max(0.0, (float(technicals["relative_volume"]) - 1.0) * 15.0))
    if technicals.get("obv") is not None:
        volume_score += 10
    if technicals.get("accumulation_distribution") is not None:
        volume_score += 10

    analyst_score = 40.0
    if analyst_sources.get("tipranks", "").startswith("Strong Buy"):
        analyst_score += 25
    elif analyst_sources.get("tipranks", "").startswith("Buy"):
        analyst_score += 15
    if analyst_sources.get("marketbeat", "").startswith("Consensus target"):
        analyst_score += 10

    news_score = 50.0

    return {
        "trend": max(0.0, min(100.0, trend)),
        "fundamentals": max(0.0, min(100.0, fundamentals_score)),
        "volume_money_flow": max(0.0, min(100.0, volume_score)),
        "analyst_sentiment": max(0.0, min(100.0, analyst_score)),
        "news_sentiment": max(0.0, min(100.0, news_score)),
    }


def fetch_stock_snapshot(symbol: str) -> StockSnapshot:
    normalized = normalize_symbol(symbol)
    ticker = yf.Ticker(normalized)
    info = {} if normalized.startswith("^") or normalized.endswith("-USD") or normalized in NO_FUNDAMENTALS_SYMBOLS else (ticker.info or {})

    history = ticker.history(period="1y", interval="1d", auto_adjust=False)
    if history.empty:
        raise RuntimeError(f"No price history for {normalized}")

    history = add_indicators(history)
    close = history["Close"].dropna()
    if close.empty:
        raise RuntimeError(f"No close prices for {normalized}")

    price = float(close.iloc[-1])
    previous = float(close.iloc[-2]) if len(close) > 1 else price
    close_4w = float(close.iloc[-21]) if len(close) >= 21 else float(close.iloc[0])

    daily_change = ((price - previous) / previous * 100) if previous else 0.0
    four_week_change = ((price - close_4w) / close_4w * 100) if close_4w else 0.0

    rsi = _safe_float(history["RSI"].dropna().iloc[-1]) if not history["RSI"].dropna().empty else None
    macd = _safe_float(history["MACD"].dropna().iloc[-1]) if not history["MACD"].dropna().empty else None
    macd_signal = _safe_float(history["MACD_SIGNAL"].dropna().iloc[-1]) if not history["MACD_SIGNAL"].dropna().empty else None

    ma_20 = _safe_float(history["MA_20"].dropna().iloc[-1]) if not history["MA_20"].dropna().empty else None
    ma_50 = _safe_float(history["MA_50"].dropna().iloc[-1]) if not history["MA_50"].dropna().empty else None
    ma_150 = _safe_float(history["MA_150"].dropna().iloc[-1]) if not history["MA_150"].dropna().empty else None
    ma_200 = _safe_float(history["MA_200"].dropna().iloc[-1]) if not history["MA_200"].dropna().empty else None
    ema_21 = _safe_float(history["EMA_21"].dropna().iloc[-1]) if not history["EMA_21"].dropna().empty else None
    atr = _safe_float(history["ATR_14"].dropna().iloc[-1]) if not history["ATR_14"].dropna().empty else None
    obv = _safe_float(history["OBV"].dropna().iloc[-1]) if not history["OBV"].dropna().empty else None
    ad_line = _safe_float(history["AD_LINE"].dropna().iloc[-1]) if not history["AD_LINE"].dropna().empty else None

    bollinger_upper = _safe_float(history["BB_UPPER"].dropna().iloc[-1]) if not history["BB_UPPER"].dropna().empty else None
    bollinger_lower = _safe_float(history["BB_LOWER"].dropna().iloc[-1]) if not history["BB_LOWER"].dropna().empty else None
    bollinger_mid = _safe_float(history["BB_MID"].dropna().iloc[-1]) if not history["BB_MID"].dropna().empty else None
    bollinger_position = None
    if bollinger_upper is not None and bollinger_lower is not None and bollinger_upper != bollinger_lower:
        bollinger_position = max(0.0, min(100.0, ((price - bollinger_lower) / (bollinger_upper - bollinger_lower)) * 100))

    volume = _safe_float(history["Volume"].dropna().iloc[-1]) or 0.0
    avg_volume_20 = _safe_float(history["Volume"].tail(20).mean())
    relative_volume = (volume / avg_volume_20) if avg_volume_20 else None
    volume_spike_percent = ((relative_volume - 1) * 100) if relative_volume is not None else None

    support_level = _safe_float(history["Low"].tail(20).min()) if not history["Low"].tail(20).empty else None
    resistance_level = _safe_float(history["High"].tail(20).max()) if not history["High"].tail(20).empty else None
    gap_percent = None
    try:
        latest_open = _safe_float(history["Open"].iloc[-1])
        if latest_open is not None and previous:
            gap_percent = ((latest_open - previous) / previous) * 100
    except Exception:
        gap_percent = None

    above_50dma = ma_50 is not None and price > ma_50
    above_200dma = ma_200 is not None and price > ma_200
    golden_cross = ma_50 is not None and ma_200 is not None and ma_50 > ma_200
    death_cross = ma_50 is not None and ma_200 is not None and ma_50 < ma_200
    relative_strength_rating = _compute_relative_strength_rating(history)

    sector = str(info.get("sector") or "N/A")
    if normalized.endswith("-USD"):
        sector = "Crypto"
    if normalized.startswith("^"):
        sector = "Index"

    analyst_sources = build_analyst_sources(ticker, info)
    analyst_targets = _parse_marketbeat_price_targets(normalized, info, price)

    consensus_price_target = _safe_float(info.get("targetMeanPrice"))
    if consensus_price_target is None and analyst_targets:
        consensus_price_target = sum(row["price_target"] for row in analyst_targets if row.get("price_target") is not None) / len(analyst_targets)
    consensus_rating = _recommendation_label_from_mean(_safe_float(info.get("recommendationMean")))
    consensus_upside_percent = ((consensus_price_target - price) / price * 100) if consensus_price_target is not None else None

    technicals = {
        "ma_20": ma_20,
        "ma_50": ma_50,
        "ma_150": ma_150,
        "ma_200": ma_200,
        "ema_21": ema_21,
        "atr": atr,
        "bollinger_mid": bollinger_mid,
        "bollinger_upper": bollinger_upper,
        "bollinger_lower": bollinger_lower,
        "bollinger_position": bollinger_position,
        "support_level": support_level,
        "resistance_level": resistance_level,
        "relative_volume": relative_volume,
        "volume_spike_percent": volume_spike_percent,
        "obv": obv,
        "accumulation_distribution": ad_line,
        "gap_percent": gap_percent,
        "relative_strength_rating": relative_strength_rating,
        "above_50dma": above_50dma,
        "above_200dma": above_200dma,
        "golden_cross": golden_cross,
        "death_cross": death_cross,
    }

    fundamentals = {
        "forward_pe": _safe_float(info.get("forwardPE")),
        "peg_ratio": _safe_float(info.get("pegRatio")),
        "revenue_growth": _safe_percent(info.get("revenueGrowth")),
        "eps_growth": _safe_percent(info.get("earningsGrowth")),
        "gross_margin": _safe_percent(info.get("grossMargins")),
        "debt_to_equity": _safe_float(info.get("debtToEquity")),
        "free_cash_flow": _safe_float(info.get("freeCashflow")),
        "roe": _safe_percent(info.get("returnOnEquity")),
        "market_cap": _safe_float(info.get("marketCap")) or 0.0,
        "pe": _safe_float(info.get("trailingPE")),
        "eps": _safe_float(info.get("trailingEps")),
        "industry": _first_non_empty(info.get("industry")),
        "website": _first_non_empty(info.get("website")),
        "insider_ownership_pct": _safe_percent(info.get("heldPercentInsiders")),
        "institutional_ownership_pct": _safe_percent(info.get("heldPercentInstitutions")),
        "short_interest_pct": _safe_percent(info.get("shortPercentOfFloat")),
        "days_to_cover": _safe_float(info.get("shortRatio")),
    }

    catalysts = {
        "earnings_date": _safe_date(info.get("earningsDate") or info.get("earningsTimestamp")),
        "days_until_earnings": "N/A",
        "dividend_date": _safe_date(info.get("dividendDate")),
        "ex_dividend_date": _safe_date(info.get("exDividendDate")),
    }
    try:
        earnings_date = pd.to_datetime(info.get("earningsDate"), errors="coerce")
        if not pd.isna(earnings_date):
            catalysts["days_until_earnings"] = int((earnings_date.normalize() - pd.Timestamp.now().normalize()).days)
    except Exception:
        pass

    risk_flags = {
        "short_interest_pct": fundamentals["short_interest_pct"],
        "days_to_cover": fundamentals["days_to_cover"],
        "recent_secondary_offering": "N/A",
        "debt_maturity": "N/A",
        "sec_investigations": "N/A",
    }

    ai_components = _compute_ai_components(technicals, fundamentals, analyst_sources)
    ai_score = round(
        ai_components["trend"] * 0.25
        + ai_components["fundamentals"] * 0.25
        + ai_components["volume_money_flow"] * 0.20
        + ai_components["analyst_sentiment"] * 0.15
        + ai_components["news_sentiment"] * 0.15,
        2,
    )

    return StockSnapshot(
        symbol=normalized,
        sector=sector,
        price=price,
        change_percent=daily_change,
        four_week_change_percent=four_week_change,
        volume=volume,
        market_cap=fundamentals["market_cap"],
        market_cap_bucket=_market_cap_bucket(fundamentals["market_cap"]),
        pe=fundamentals["pe"],
        eps=fundamentals["eps"],
        fifty_two_week_high=_safe_float(info.get("fiftyTwoWeekHigh")),
        fifty_two_week_low=_safe_float(info.get("fiftyTwoWeekLow")),
        rsi=rsi,
        macd=macd,
        macd_signal=macd_signal,
        ma_150=ma_150,
        ma_50=ma_50,
        ema_21=ema_21,
        analyst_sources=analyst_sources,
        analyst_targets=analyst_targets,
        consensus_price_target=consensus_price_target,
        consensus_upside_percent=consensus_upside_percent,
        consensus_rating=consensus_rating,
        technicals=technicals,
        fundamentals=fundamentals,
        catalysts=catalysts,
        risk_flags=risk_flags,
        ai_components=ai_components,
        ai_score=ai_score,
        history_1y=history,
    )


def format_symbols_by_sector(snapshots: List[StockSnapshot]) -> List[str]:
    grouped: Dict[str, List[str]] = {}
    for snapshot in snapshots:
        grouped.setdefault(snapshot.sector, []).append(snapshot.symbol)

    ordered: List[str] = []
    for sector in sorted(grouped.keys()):
        for symbol in sorted(set(grouped[sector])):
            ordered.append(symbol)
    return ordered
