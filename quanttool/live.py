from __future__ import annotations

import json
import math
import os
import statistics
import time
import xml.etree.ElementTree as ET
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


DEFAULT_WATCHLIST = [
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "META",
    "GOOGL",
    "GOOG",
    "TSLA",
    "AVGO",
    "AMD",
    "NFLX",
    "COST",
    "CRM",
    "ADBE",
    "ORCL",
    "INTC",
    "QCOM",
    "TXN",
    "MU",
    "PANW",
    "CRWD",
    "PLTR",
    "SHOP",
    "UBER",
    "COIN",
    "MSTR",
    "SMCI",
    "ARM",
    "NOW",
    "SNOW",
    "JPM",
    "BAC",
    "GS",
    "MS",
    "V",
    "MA",
    "AXP",
    "LLY",
    "UNH",
    "JNJ",
    "MRK",
    "ABBV",
    "PFE",
    "XOM",
    "CVX",
    "COP",
    "GE",
    "CAT",
    "BA",
    "LMT",
    "WMT",
    "HD",
    "LOW",
    "NKE",
    "DIS",
    "CMCSA",
    "T",
    "VZ",
    "SPY",
    "QQQ",
]


@dataclass
class Quote:
    symbol: str
    provider: str
    price: float | None = None
    change_pct: float | None = None
    change: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    previous_close: float | None = None
    volume: float | None = None
    timestamp: float = field(default_factory=time.time)
    intraday_closes: list[float] = field(default_factory=list)
    intraday_volumes: list[float] = field(default_factory=list)


@dataclass
class ProviderStatus:
    provider: str
    enabled: bool
    ok: bool
    message: str
    latency_ms: int | None = None


@dataclass
class RankedSymbol:
    rank: int
    symbol: str
    price: float | None
    change_pct: float
    score: float
    continuation_probability: float
    signal: str
    volume: float | None
    providers: list[str]
    reasons: list[str]
    sparkline: list[float]
    entry_window: dict[str, Any]
    news: dict[str, Any] | None = None
    news_items: list[dict[str, Any]] = field(default_factory=list)
    macro_reason: str = "No clear macro theme"


class TTLCache:
    def __init__(self) -> None:
        self._values: dict[str, tuple[float, Any]] = {}

    def get(self, key: str, ttl_seconds: float) -> Any | None:
        item = self._values.get(key)
        if item is None:
            return None
        created_at, value = item
        if time.time() - created_at > ttl_seconds:
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._values[key] = (time.time(), value)


class LiveMarketScanner:
    def __init__(self) -> None:
        self.cache = TTLCache()
        self.alpha_key = os.getenv("ALPHA_VANTAGE_API_KEY", "")
        self.polygon_key = os.getenv("POLYGON_API_KEY", "")
        self.finnhub_key = os.getenv("FINNHUB_API_KEY", "")

    def scan(self, symbols: list[str], limit: int = 30) -> dict[str, Any]:
        cleaned = clean_symbols(symbols) or DEFAULT_WATCHLIST
        limit = max(1, min(limit, 100))
        statuses: list[ProviderStatus] = []
        quotes: list[Quote] = []

        jobs = [
            ("yahoo", lambda: self.fetch_yahoo(cleaned)),
        ]

        with ThreadPoolExecutor(max_workers=len(jobs)) as executor:
            futures = {executor.submit(run_provider, job): name for name, job in jobs}
            for future in as_completed(futures):
                provider = futures[future]
                try:
                    provider_quotes, status, latency_ms = future.result()
                    status.latency_ms = latency_ms
                    quotes.extend(provider_quotes)
                    statuses.append(status)
                except Exception as exc:
                    statuses.append(ProviderStatus(provider, True, False, str(exc)))

        market_context = self.fetch_market_context()
        ranked = rank_quotes(cleaned, quotes)[:limit]
        attach_news(ranked, self.fetch_news_for_symbols([item.symbol for item in ranked[:limit]]))
        attach_macro_reasons(ranked, market_context)
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "universe_size": len(cleaned),
            "ranked": [asdict(item) for item in ranked],
            "market_context": market_context,
            "providers": [asdict(status) for status in statuses],
            "notes": [
                "排名是模型评分，不是收益承诺。",
                "页面可以每秒刷新；实际行情新鲜度取决于 Yahoo Finance、交易时段和限流。",
            ],
        }

    def fetch_yahoo(self, symbols: list[str]) -> tuple[list[Quote], ProviderStatus]:
        cache_key = "yahoo:" + ",".join(symbols)
        cached = self.cache.get(cache_key, 2)
        if cached is not None:
            return cached

        try:
            url = "https://query1.finance.yahoo.com/v7/finance/quote?" + urllib.parse.urlencode(
                {"symbols": ",".join(symbols)}
            )
            payload = request_json(url)
            results = payload.get("quoteResponse", {}).get("result", [])
        except RuntimeError:
            return self.fetch_yahoo_chart(symbols)

        quotes = []
        for row in results:
            symbol = row.get("symbol")
            if not symbol:
                continue
            quotes.append(
                Quote(
                    symbol=symbol,
                    provider="Yahoo",
                    price=num(row.get("regularMarketPrice")),
                    change_pct=num(row.get("regularMarketChangePercent")),
                    change=num(row.get("regularMarketChange")),
                    open=num(row.get("regularMarketOpen")),
                    high=num(row.get("regularMarketDayHigh")),
                    low=num(row.get("regularMarketDayLow")),
                    previous_close=num(row.get("regularMarketPreviousClose")),
                    volume=num(row.get("regularMarketVolume")),
                    timestamp=num(row.get("regularMarketTime")) or time.time(),
                )
            )
        status = ProviderStatus("Yahoo Finance", True, bool(quotes), f"{len(quotes)} quotes")
        value = (quotes, status)
        self.cache.set(cache_key, value)
        return value

    def fetch_news_for_symbols(self, symbols: list[str]) -> dict[str, list[dict[str, Any]]]:
        if not symbols:
            return {}

        cache_key = "news:" + ",".join(symbols)
        cached = self.cache.get(cache_key, 300)
        if cached is not None:
            return cached

        news: dict[str, list[dict[str, Any]]] = {}
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(self.fetch_symbol_news, symbol): symbol for symbol in symbols[:30]}
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    items = future.result()
                    if items:
                        news[symbol] = items
                except RuntimeError:
                    continue

        self.cache.set(cache_key, news)
        return news

    def fetch_symbol_news(self, symbol: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        if self.finnhub_key:
            items.extend(self.fetch_finnhub_news(symbol))
        try:
            items.extend(fetch_yahoo_rss_news_items(symbol, limit=5))
        except RuntimeError:
            if not items:
                raise
        return dedupe_news_items(items)[:6]

    def fetch_finnhub_news(self, symbol: str) -> list[dict[str, Any]]:
        today = datetime.now(timezone.utc).date()
        start = today - timedelta(days=7)
        url = "https://finnhub.io/api/v1/company-news?" + urllib.parse.urlencode(
            {"symbol": symbol, "from": start.isoformat(), "to": today.isoformat(), "token": self.finnhub_key}
        )
        rows = request_json(url, timeout=4)
        if not isinstance(rows, list) or not rows:
            return []
        items = []
        for row in rows[:5]:
            items.append(
                {
                    "title": str(row.get("headline") or "Latest news"),
                    "source": str(row.get("source") or "Finnhub"),
                    "url": str(row.get("url") or ""),
                    "published_at": row.get("datetime"),
                }
            )
        return items

    def fetch_market_context(self) -> list[dict[str, Any]]:
        cached = self.cache.get("market_context", 300)
        if cached is not None:
            return cached

        symbols = ["SPY", "QQQ", "DIA", "USO", "GLD", "TLT", "UUP"]
        headlines: list[dict[str, Any]] = []
        for symbol in symbols:
            try:
                item = fetch_yahoo_rss_news(symbol)
            except RuntimeError:
                continue
            if item and item.get("title") not in {headline.get("title") for headline in headlines}:
                item["theme"] = classify_theme(str(item.get("title", "")))
                item["symbol"] = symbol
                headlines.append(item)
            if len(headlines) >= 6:
                break

        self.cache.set("market_context", headlines)
        return headlines

    def fetch_yahoo_chart(self, symbols: list[str]) -> tuple[list[Quote], ProviderStatus]:
        cache_key = "yahoo_chart:" + ",".join(symbols)
        cached = self.cache.get(cache_key, 15)
        if cached is not None:
            return cached

        quotes: list[Quote] = []
        errors: list[str] = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(fetch_yahoo_chart_symbol, symbol): symbol for symbol in symbols[:60]}
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    quote = future.result()
                    if quote is not None:
                        quotes.append(quote)
                except RuntimeError as exc:
                    errors.append(str(exc))
                    if "Too Many Requests" in str(exc) or "HTTP 429" in str(exc):
                        break

        message = f"{len(quotes)} quotes via chart fallback"
        if not quotes and errors:
            message = errors[-1]
        status = ProviderStatus("Yahoo Finance", True, bool(quotes), message)
        value = (quotes, status)
        self.cache.set(cache_key, value)
        return value

    def fetch_alpha_vantage(self, symbols: list[str]) -> tuple[list[Quote], ProviderStatus]:
        if not self.alpha_key:
            return [], ProviderStatus("Alpha Vantage", False, False, "Set ALPHA_VANTAGE_API_KEY")
        cache_key = "alpha:" + ",".join(symbols)
        cached = self.cache.get(cache_key, 60)
        if cached is not None:
            return cached

        quotes: list[Quote] = []
        for symbol in symbols:
            url = "https://www.alphavantage.co/query?" + urllib.parse.urlencode(
                {"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": self.alpha_key}
            )
            payload = request_json(url)
            row = payload.get("Global Quote", {})
            if not row:
                continue
            quotes.append(
                Quote(
                    symbol=symbol,
                    provider="Alpha Vantage",
                    price=num(row.get("05. price")),
                    change_pct=parse_percent(row.get("10. change percent")),
                    change=num(row.get("09. change")),
                    open=num(row.get("02. open")),
                    high=num(row.get("03. high")),
                    low=num(row.get("04. low")),
                    previous_close=num(row.get("08. previous close")),
                    volume=num(row.get("06. volume")),
                )
            )
        status = ProviderStatus("Alpha Vantage", True, bool(quotes), f"{len(quotes)} quotes")
        value = (quotes, status)
        self.cache.set(cache_key, value)
        return value

    def fetch_polygon(self, symbols: list[str]) -> tuple[list[Quote], ProviderStatus]:
        if not self.polygon_key:
            return [], ProviderStatus("Polygon", False, False, "Set POLYGON_API_KEY")
        cache_key = "polygon:" + ",".join(symbols)
        cached = self.cache.get(cache_key, 5)
        if cached is not None:
            return cached

        url = "https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers?" + urllib.parse.urlencode(
            {"tickers": ",".join(symbols), "apiKey": self.polygon_key}
        )
        payload = request_json(url)
        quotes = []
        for row in payload.get("tickers", []):
            symbol = row.get("ticker")
            day = row.get("day", {}) or {}
            prev = row.get("prevDay", {}) or {}
            last = row.get("lastTrade", {}) or {}
            price = num(last.get("p")) or num(day.get("c"))
            previous_close = num(prev.get("c"))
            change_pct = None
            if price and previous_close:
                change_pct = (price / previous_close - 1) * 100
            quotes.append(
                Quote(
                    symbol=symbol,
                    provider="Polygon",
                    price=price,
                    change_pct=change_pct,
                    open=num(day.get("o")),
                    high=num(day.get("h")),
                    low=num(day.get("l")),
                    previous_close=previous_close,
                    volume=num(day.get("v")),
                    timestamp=(num(last.get("t")) or time.time() * 1000) / 1000,
                )
            )
        status = ProviderStatus("Polygon", True, bool(quotes), f"{len(quotes)} quotes")
        value = (quotes, status)
        self.cache.set(cache_key, value)
        return value

    def fetch_finnhub(self, symbols: list[str]) -> tuple[list[Quote], ProviderStatus]:
        if not self.finnhub_key:
            return [], ProviderStatus("Finnhub", False, False, "Set FINNHUB_API_KEY")
        cache_key = "finnhub:" + ",".join(symbols)
        cached = self.cache.get(cache_key, 5)
        if cached is not None:
            return cached

        quotes: list[Quote] = []
        for symbol in symbols:
            url = "https://finnhub.io/api/v1/quote?" + urllib.parse.urlencode(
                {"symbol": symbol, "token": self.finnhub_key}
            )
            row = request_json(url)
            price = num(row.get("c"))
            if price is None:
                continue
            quotes.append(
                Quote(
                    symbol=symbol,
                    provider="Finnhub",
                    price=price,
                    change_pct=num(row.get("dp")),
                    change=num(row.get("d")),
                    open=num(row.get("o")),
                    high=num(row.get("h")),
                    low=num(row.get("l")),
                    previous_close=num(row.get("pc")),
                    timestamp=num(row.get("t")) or time.time(),
                )
            )
        status = ProviderStatus("Finnhub", True, bool(quotes), f"{len(quotes)} quotes")
        value = (quotes, status)
        self.cache.set(cache_key, value)
        return value


def run_provider(job: Any) -> tuple[list[Quote], ProviderStatus, int]:
    started = time.time()
    quotes, status = job()
    return quotes, status, int((time.time() - started) * 1000)


def attach_news(ranked: list[RankedSymbol], news: dict[str, list[dict[str, Any]]]) -> None:
    for item in ranked:
        item.news_items = news.get(item.symbol, [])
        item.news = item.news_items[0] if item.news_items else None


def attach_macro_reasons(ranked: list[RankedSymbol], market_context: list[dict[str, Any]]) -> None:
    themes = [str(item.get("theme", "")) for item in market_context]
    headlines = [str(item.get("title", "")) for item in market_context]
    for item in ranked:
        own_news = [str(news.get("title", "")) for news in item.news_items[:3]]
        item.macro_reason = build_macro_reason(item.symbol, themes, headlines + own_news)


def build_macro_reason(symbol: str, themes: list[str], headlines: list[str]) -> str:
    sector = sector_for_symbol(symbol)
    theme_text = " ".join(themes).lower()
    headline_text = " ".join(headlines).lower()

    if sector == "semiconductors" and any(word in theme_text + headline_text for word in ["ai", "chip", "semiconductor", "memory"]):
        return "AI/chip headline tailwind; watch for sector-wide rotation."
    if sector == "crypto" and any(word in theme_text + headline_text for word in ["crypto", "bitcoin", "digital asset"]):
        return "Crypto policy/Bitcoin headlines may amplify moves."
    if sector == "energy" and any(word in theme_text + headline_text for word in ["oil", "energy", "hormuz", "iran", "opec"]):
        return "Oil/geopolitical headline sensitivity."
    if sector == "defense" and any(word in theme_text + headline_text for word in ["war", "defense", "iran", "geopolitical"]):
        return "Geopolitical risk can support defense flows."
    if sector == "banks" and any(word in theme_text + headline_text for word in ["rate", "yield", "fed", "treasury", "bank"]):
        return "Rates/yields headline sensitivity."
    if sector == "consumer" and any(word in theme_text + headline_text for word in ["consumer", "retail", "tariff", "inflation"]):
        return "Consumer/inflation headlines may affect demand sentiment."
    if symbol in {"SPY", "QQQ"}:
        return "Broad market proxy; macro headlines directly matter."
    if themes:
        return f"Macro backdrop: {themes[0]}."
    return "No strong macro headline match."


def sector_for_symbol(symbol: str) -> str:
    groups = {
        "semiconductors": {"NVDA", "AMD", "AVGO", "INTC", "QCOM", "TXN", "MU", "ARM", "SMCI"},
        "crypto": {"COIN", "MSTR"},
        "energy": {"XOM", "CVX", "COP", "USO"},
        "defense": {"LMT", "BA"},
        "banks": {"JPM", "BAC", "GS", "MS", "AXP", "V", "MA"},
        "consumer": {"WMT", "HD", "LOW", "NKE", "COST", "DIS", "AMZN"},
        "software": {"MSFT", "CRM", "ADBE", "ORCL", "NOW", "SNOW", "PANW", "CRWD", "PLTR"},
        "healthcare": {"LLY", "UNH", "JNJ", "MRK", "ABBV", "PFE"},
    }
    for sector, symbols in groups.items():
        if symbol in symbols:
            return sector
    return "general"


def classify_theme(title: str) -> str:
    text = title.lower()
    checks = [
        ("AI/chips", ["ai", "chip", "semiconductor", "memory", "nvidia", "micron"]),
        ("Oil/geopolitics", ["oil", "hormuz", "iran", "opec", "geopolitical"]),
        ("Rates/Fed", ["fed", "rate", "yield", "treasury", "inflation"]),
        ("Crypto policy", ["crypto", "bitcoin", "digital asset"]),
        ("Consumer/inflation", ["consumer", "retail", "tariff", "inflation"]),
        ("Market risk", ["futures", "dow", "nasdaq", "s&p", "market"]),
    ]
    padded = f" {text} "
    for theme, keywords in checks:
        if any(keyword in padded for keyword in keywords):
            return theme
    return "General market"


def fetch_yahoo_rss_news(symbol: str) -> dict[str, Any] | None:
    items = fetch_yahoo_rss_news_items(symbol, limit=1)
    return items[0] if items else None


def fetch_yahoo_rss_news_items(symbol: str, limit: int = 5) -> list[dict[str, Any]]:
    url = "https://feeds.finance.yahoo.com/rss/2.0/headline?" + urllib.parse.urlencode(
        {"s": symbol, "region": "US", "lang": "en-US"}
    )
    request = urllib.request.Request(url, headers={"User-Agent": "quant-stock-tool/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=4) as response:
            root = ET.fromstring(response.read())
    except (urllib.error.HTTPError, urllib.error.URLError, ET.ParseError) as exc:
        raise RuntimeError(f"Yahoo news error for {symbol}: {exc}") from exc

    channel = root.find("channel")
    if channel is None:
        return []

    items = []
    for row in channel.findall("item")[:limit]:
        title = row.findtext("title") or "Latest news"
        link = row.findtext("link") or ""
        source = row.findtext("source") or "Yahoo Finance"
        published = row.findtext("pubDate") or ""
        items.append(
            {
                "title": title,
                "source": source,
                "url": link,
                "published_at": published,
            }
        )
    return items


def dedupe_news_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        key = (title.lower(), url)
        if not title or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def fetch_yahoo_chart_symbol(symbol: str) -> Quote | None:
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(symbol) + "?" + urllib.parse.urlencode(
        {"range": "1d", "interval": "1m"}
    )
    payload = request_json(url, timeout=4)
    result = (payload.get("chart", {}).get("result") or [None])[0]
    if not result:
        return None
    meta = result.get("meta", {})
    indicators = result.get("indicators", {})
    quote_rows = indicators.get("quote") or [{}]
    quote_row = quote_rows[0]
    closes = compact_numbers(quote_row.get("close", []))
    highs = compact_numbers(quote_row.get("high", []))
    lows = compact_numbers(quote_row.get("low", []))
    opens = compact_numbers(quote_row.get("open", []))
    volumes = compact_numbers(quote_row.get("volume", []))
    price = num(meta.get("regularMarketPrice")) or (closes[-1] if closes else None)
    previous_close = num(meta.get("chartPreviousClose")) or num(meta.get("previousClose"))
    change_pct = None
    if price is not None and previous_close:
        change_pct = (price / previous_close - 1) * 100
    return Quote(
        symbol=symbol,
        provider="Yahoo Chart",
        price=price,
        change_pct=change_pct,
        open=opens[0] if opens else None,
        high=max(highs) if highs else None,
        low=min(lows) if lows else None,
        previous_close=previous_close,
        volume=sum(volumes) if volumes else None,
        timestamp=num(meta.get("regularMarketTime")) or time.time(),
        intraday_closes=closes,
        intraday_volumes=volumes,
    )


def rank_quotes(symbols: list[str], quotes: list[Quote]) -> list[RankedSymbol]:
    by_symbol: dict[str, list[Quote]] = {symbol: [] for symbol in symbols}
    for quote in quotes:
        by_symbol.setdefault(quote.symbol, []).append(quote)

    ranked: list[RankedSymbol] = []
    for symbol in symbols:
        symbol_quotes = by_symbol.get(symbol, [])
        if not symbol_quotes:
            continue

        price = median_field(symbol_quotes, "price")
        change_pct = median_field(symbol_quotes, "change_pct") or 0.0
        open_price = median_field(symbol_quotes, "open")
        high = median_field(symbol_quotes, "high")
        low = median_field(symbol_quotes, "low")
        previous_close = median_field(symbol_quotes, "previous_close")
        volume = median_field(symbol_quotes, "volume")

        range_position = 0.5
        if price is not None and high is not None and low is not None and high > low:
            range_position = clamp((price - low) / (high - low), 0, 1)

        intraday_strength = 0.0
        if price is not None and open_price:
            intraday_strength = (price / open_price - 1) * 100

        gap = 0.0
        if open_price is not None and previous_close:
            gap = (open_price / previous_close - 1) * 100

        volume_component = 0.0
        if volume:
            volume_component = min(math.log10(max(volume, 1)) / 8, 1) * 10

        score = (
            change_pct * 2.4
            + intraday_strength * 1.4
            + gap * 0.6
            + (range_position - 0.5) * 18
            + volume_component
        )
        continuation = sigmoid((score - 8) / 12)
        signal = signal_label(continuation, change_pct, range_position)
        providers = sorted({quote.provider for quote in symbol_quotes})
        reasons = build_reasons(change_pct, intraday_strength, gap, range_position, providers)
        closes = longest_series(symbol_quotes, "intraday_closes")
        volumes = longest_series(symbol_quotes, "intraday_volumes")
        sparkline = intraday_sparkline(closes, previous_close) or synthetic_sparkline(
            price, previous_close, open_price, low, high
        )
        entry_window = recommend_entry_window(
            price=price,
            previous_close=previous_close,
            open_price=open_price,
            high=high,
            low=low,
            change_pct=change_pct,
            intraday_strength=intraday_strength,
            range_position=range_position,
            closes=closes,
            volumes=volumes,
        )

        ranked.append(
            RankedSymbol(
                rank=0,
                symbol=symbol,
                price=price,
                change_pct=change_pct,
                score=score,
                continuation_probability=continuation,
                signal=signal,
                volume=volume,
                providers=providers,
                reasons=reasons,
                sparkline=sparkline,
                entry_window=entry_window,
            )
        )

    ranked.sort(key=lambda item: item.score, reverse=True)
    for index, item in enumerate(ranked, 1):
        item.rank = index
    return ranked


def build_reasons(
    change_pct: float,
    intraday_strength: float,
    gap: float,
    range_position: float,
    providers: list[str],
) -> list[str]:
    reasons = []
    if change_pct > 0:
        reasons.append(f"当日涨幅 {change_pct:.2f}%")
    if intraday_strength > 0:
        reasons.append(f"盘中强度 {intraday_strength:.2f}%")
    if gap > 0:
        reasons.append(f"开盘跳空 {gap:.2f}%")
    if range_position >= 0.7:
        reasons.append("价格靠近日内高位")
    if len(providers) > 1:
        reasons.append(f"{len(providers)} 个数据源确认")
    return reasons[:4] or ["数据完整度较高"]


def recommend_entry_window(
    price: float | None,
    previous_close: float | None,
    open_price: float | None,
    high: float | None,
    low: float | None,
    change_pct: float,
    intraday_strength: float,
    range_position: float,
    closes: list[float],
    volumes: list[float],
) -> dict[str, Any]:
    gap = 0.0
    if open_price is not None and previous_close:
        gap = (open_price / previous_close - 1) * 100

    first_slice = closes[: max(3, min(12, len(closes) // 5))]
    last_slice = closes[-max(3, min(12, len(closes) // 5)) :] if closes else []
    open_fade = False
    late_reclaim = False
    trend_slope = 0.0
    vwap_distance = None

    if closes:
        session_high = max(closes)
        first_high = max(first_slice) if first_slice else session_high
        last_price = closes[-1]
        open_fade = gap > 1.0 and first_high > 0 and last_price < first_high * 0.985
        late_reclaim = len(last_slice) > 1 and last_slice[-1] > statistics.mean(last_slice)
        if closes[0]:
            trend_slope = (closes[-1] / closes[0] - 1) * 100
        vwap = estimate_vwap(closes, volumes)
        if vwap:
            vwap_distance = (last_price / vwap - 1) * 100

    if change_pct < 0 or range_position < 0.35:
        label = "No chase"
        window = "等待重新站上 VWAP 后再评估"
        confidence = 35
        rationale = "当日走势偏弱，直接追入风险较高。"
    elif open_fade:
        label = "Wait for pullback"
        window = "美东 10:00-11:30 回踩确认"
        confidence = 62
        rationale = "高开后回落，优先等开盘情绪释放后观察是否守住 VWAP/前低。"
    elif gap > 2.0 and range_position > 0.75 and vwap_distance is not None and vwap_distance > 1.5:
        label = "VWAP pullback"
        window = "回踩 VWAP 附近，不追高点"
        confidence = 68
        rationale = "强势高开且价格偏离 VWAP，较好的位置通常来自回踩而不是尖峰追入。"
    elif trend_slope > 1.0 and range_position > 0.7 and late_reclaim:
        label = "Breakout confirm"
        window = "美东 10:15-11:00 或 14:30-15:30 确认突破"
        confidence = 72
        rationale = "盘中趋势仍在抬高，可等突破后回踩不破再观察。"
    elif intraday_strength > 0 and range_position > 0.55:
        label = "Midday base"
        window = "美东 11:00-13:30 横盘企稳"
        confidence = 58
        rationale = "走势偏强但不是极强，适合等午盘收敛后再看方向。"
    else:
        label = "Late confirm"
        window = "美东 14:30-15:45 尾盘确认"
        confidence = 50
        rationale = "信号不够清晰，等待尾盘资金方向更稳。"

    if vwap_distance is not None:
        rationale += f" 当前距估算 VWAP {vwap_distance:+.2f}%."

    buy_zone = recommend_buy_zone(
        label=label,
        price=price,
        open_price=open_price,
        high=high,
        low=low,
        closes=closes,
        volumes=volumes,
    )
    sell_zone = recommend_sell_zone(
        label=label,
        price=price,
        high=high,
        low=low,
        closes=closes,
        volumes=volumes,
        buy_zone=buy_zone,
    )

    return {
        "label": label,
        "window": window,
        "confidence": confidence,
        "rationale": rationale,
        "buy_zone": buy_zone,
        "sell_zone": sell_zone,
    }


def recommend_buy_zone(
    label: str,
    price: float | None,
    open_price: float | None,
    high: float | None,
    low: float | None,
    closes: list[float],
    volumes: list[float],
) -> dict[str, Any]:
    if price is None:
        return {
            "label": "No price",
            "range": "--",
            "trigger": "等待实时价格恢复",
        }

    vwap = estimate_vwap(closes, volumes)
    recent_support = min(closes[-20:]) if len(closes) >= 5 else low
    recent_resistance = max(closes[-20:]) if len(closes) >= 5 else high

    if label == "No chase":
        anchor = vwap or recent_resistance or price
        lower = anchor * 0.998
        upper = anchor * 1.004
        trigger = "重新站上 VWAP 且 5-15 分钟不跌回"
    elif label == "VWAP pullback":
        anchor = vwap or open_price or price
        lower = anchor * 0.992
        upper = anchor * 1.006
        trigger = "回踩区间内缩量企稳，随后放量转强"
    elif label == "Wait for pullback":
        anchor = max(value for value in [vwap, recent_support, low, price] if value is not None)
        lower = anchor * 0.995
        upper = anchor * 1.008
        trigger = "开盘回落后守住支撑，重新上穿短线均价"
    elif label == "Breakout confirm":
        anchor = recent_resistance or high or price
        lower = anchor * 0.998
        upper = anchor * 1.012
        trigger = "突破前高后回踩不破，避免直接追最高点"
    elif label == "Midday base":
        anchor = vwap or statistics.mean(closes[-20:]) if closes else price
        lower = anchor * 0.996
        upper = anchor * 1.006
        trigger = "午盘窄幅整理后向上离开区间"
    else:
        anchor = price
        lower = price * 0.995
        upper = price * 1.005
        trigger = "尾盘放量站稳当前价附近"

    return {
        "label": "24h observe zone",
        "range": f"${lower:.2f} - ${upper:.2f}",
        "trigger": trigger,
        "lower": lower,
        "upper": upper,
    }


def recommend_sell_zone(
    label: str,
    price: float | None,
    high: float | None,
    low: float | None,
    closes: list[float],
    volumes: list[float],
    buy_zone: dict[str, Any],
) -> dict[str, Any]:
    if price is None:
        return {
            "target": "--",
            "risk": "--",
            "trigger": "等待实时价格恢复",
        }

    vwap = estimate_vwap(closes, volumes)
    buy_upper = float(buy_zone.get("upper") or price)
    buy_lower = float(buy_zone.get("lower") or price)
    recent_support = min(closes[-20:]) if len(closes) >= 5 else low or price
    recent_resistance = max(closes[-20:]) if len(closes) >= 5 else high or price

    if label in {"VWAP pullback", "Breakout confirm"}:
        target_low = max(price, recent_resistance) * 1.012
        target_high = max(price, recent_resistance) * 1.035
        risk = min(buy_lower * 0.985, (vwap or buy_lower) * 0.99)
        trigger = "冲高靠近目标区可分批止盈；跌破买入区下沿/VWAP 减仓"
    elif label == "Midday base":
        target_low = buy_upper * 1.012
        target_high = buy_upper * 1.028
        risk = min(buy_lower * 0.988, recent_support * 0.992)
        trigger = "午盘突破后若量能衰减，可在目标区分批卖出"
    elif label == "Late confirm":
        target_low = price * 1.008
        target_high = price * 1.02
        risk = min(buy_lower * 0.99, (vwap or buy_lower) * 0.992)
        trigger = "尾盘确认失败或跌回 VWAP，优先退出观察"
    elif label == "No chase":
        target_low = price * 1.006
        target_high = price * 1.016
        risk = min(recent_support * 0.99, buy_lower * 0.99)
        trigger = "只适合反弹观察；不能站稳 VWAP 就不持有"
    else:
        target_low = price * 1.01
        target_high = price * 1.025
        risk = price * 0.985
        trigger = "达到目标区或跌破失效线时重新评估"

    return {
        "target": f"${target_low:.2f} - ${target_high:.2f}",
        "risk": f"失效线 ${risk:.2f}",
        "trigger": trigger,
    }


def signal_label(probability: float, change_pct: float, range_position: float) -> str:
    if probability >= 0.72 and change_pct > 0 and range_position > 0.65:
        return "Strong watch"
    if probability >= 0.58 and change_pct > 0:
        return "Watch"
    if change_pct < 0:
        return "Weak"
    return "Neutral"


def synthetic_sparkline(
    price: float | None,
    previous_close: float | None,
    open_price: float | None,
    low: float | None,
    high: float | None,
) -> list[float]:
    points = [value for value in [previous_close, open_price, low, high, price] if value is not None]
    if len(points) < 2:
        return []
    first = points[0]
    if first == 0:
        return points
    return [round((value / first - 1) * 100, 2) for value in points]


def intraday_sparkline(closes: list[float], previous_close: float | None) -> list[float]:
    if len(closes) < 2:
        return []
    step = max(1, len(closes) // 5)
    sampled = closes[::step][:5]
    if sampled[-1] != closes[-1]:
        sampled.append(closes[-1])
    base = previous_close or sampled[0]
    if not base:
        return sampled
    return [round((value / base - 1) * 100, 2) for value in sampled]


def longest_series(quotes: list[Quote], field_name: str) -> list[float]:
    series = [getattr(quote, field_name) for quote in quotes if getattr(quote, field_name)]
    if not series:
        return []
    return list(max(series, key=len))


def estimate_vwap(closes: list[float], volumes: list[float]) -> float | None:
    if not closes:
        return None
    if not volumes or len(volumes) != len(closes):
        return sum(closes) / len(closes)
    total_volume = sum(volumes)
    if total_volume <= 0:
        return sum(closes) / len(closes)
    return sum(price * volume for price, volume in zip(closes, volumes)) / total_volume


def request_json(url: str, timeout: float = 8) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "quant-stock-tool/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} from {urllib.parse.urlparse(url).netloc}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error: {exc.reason}") from exc


def clean_symbols(symbols: list[str]) -> list[str]:
    cleaned = []
    for symbol in symbols:
        value = "".join(ch for ch in symbol.upper().strip() if ch.isalnum() or ch in ".-")
        if value and value not in cleaned:
            cleaned.append(value)
    return cleaned[:250]


def median_field(quotes: list[Quote], field_name: str) -> float | None:
    values = [getattr(quote, field_name) for quote in quotes if getattr(quote, field_name) is not None]
    if not values:
        return None
    return float(statistics.median(values))


def num(value: Any) -> float | None:
    if value in (None, "", "None"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_percent(value: Any) -> float | None:
    if isinstance(value, str):
        value = value.replace("%", "")
    return num(value)


def compact_numbers(values: list[Any]) -> list[float]:
    return [number for value in values if (number := num(value)) is not None]


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def sigmoid(value: float) -> float:
    return 1 / (1 + math.exp(-value))
