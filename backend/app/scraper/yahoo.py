import datetime as dt
import logging
import time

import yfinance as yf

from app import config

log = logging.getLogger(__name__)


class InvalidTickerError(Exception):
    """Yahoo Finance has no data for this symbol."""


def _retry(func, *args, **kwargs):
    """Call func, retrying on errors up to MAX_RETRIES times with a growing delay."""
    last_error = None
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            log.warning("Attempt %s/%s failed: %s", attempt, config.MAX_RETRIES, exc)
            if attempt < config.MAX_RETRIES:
                time.sleep(config.REQUEST_DELAY_SECONDS * attempt)
    raise last_error


def _num(value):
    try:
        if value is None:
            return None
        number = float(value)
        return None if number != number else number  # NaN -> None
    except (TypeError, ValueError):
        return None


def _int(value):
    number = _num(value)
    return int(number) if number is not None else None


def _pick(data, *keys):
    for key in keys:
        value = data.get(key)
        if value is not None:
            return value
    return None


def _to_naive_utc(value):
    try:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return dt.datetime.fromtimestamp(value, tz=dt.timezone.utc).replace(tzinfo=None)
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(dt.timezone.utc).replace(tzinfo=None)
        return parsed
    except (ValueError, OSError, OverflowError):
        return None


def _parse_news(raw_items):
    articles, seen = [], set()
    for item in raw_items or []:
        if not isinstance(item, dict):
            continue
        content = item.get("content") if isinstance(item.get("content"), dict) else item
        title = content.get("title")
        url = None
        for key in ("canonicalUrl", "clickThroughUrl"):
            link = content.get(key)
            if isinstance(link, dict) and link.get("url"):
                url = link["url"]
                break
        url = url or content.get("link") or content.get("url")
        provider = content.get("provider")
        source = (
            provider.get("displayName")
            if isinstance(provider, dict)
            else content.get("publisher")
        )
        published = _to_naive_utc(
            content.get("pubDate")
            or content.get("displayTime")
            or content.get("providerPublishTime")
        )
        if title and url and url not in seen:
            seen.add(url)
            articles.append(
                {"title": title, "url": url, "source": source, "published_at": published}
            )
    return articles[:20]


QUOTE_REQUIRED = [
    "current_price", "change", "change_percent", "previous_close", "open_price",
    "days_low", "days_high", "week52_low", "week52_high", "volume", "market_cap",
]
COMPANY_FIELDS = [
    "company_name", "exchange", "currency", "sector", "industry",
    "website", "business_summary", "full_time_employees",
]


def fetch_ticker_data(symbol: str) -> dict:
    """Fetch prices, company info and news for one symbol. Raises InvalidTickerError
    if Yahoo has nothing for it. Missing fields become None and are listed in 'missing'."""
    ticker = yf.Ticker(symbol)
    missing: list[str] = []

    # 1) Historical data (3 months of daily prices)
    history_df = _retry(
        ticker.history, period="3mo", interval="1d", timeout=config.REQUEST_TIMEOUT
    )
    time.sleep(config.REQUEST_DELAY_SECONDS)

    # 2) Summary data (quote table + company overview)
    try:
        info = _retry(lambda: ticker.info) or {}
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not fetch summary info for %s: %s", symbol, exc)
        info = {}
        missing.append("summary info")
    time.sleep(config.REQUEST_DELAY_SECONDS)

    # 3) News
    try:
        news_raw = _retry(lambda: ticker.news) or []
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not fetch news for %s: %s", symbol, exc)
        news_raw = []
        missing.append("news")

    has_history = history_df is not None and not history_df.empty
    if not has_history and _pick(info, "currentPrice", "regularMarketPrice") is None:
        raise InvalidTickerError(
            f"No data found for '{symbol}'. The symbol may be invalid or delisted."
        )

    history_rows = []
    if has_history:
        for index, row in history_df.iterrows():
            day = index.date() if hasattr(index, "date") else index
            history_rows.append(
                {
                    "date": day,
                    "open_price": _num(row.get("Open")),
                    "high_price": _num(row.get("High")),
                    "low_price": _num(row.get("Low")),
                    "close_price": _num(row.get("Close")),
                    "volume": _int(row.get("Volume")),
                }
            )
    else:
        missing.append("historical prices")

    last = history_rows[-1] if history_rows else {}
    prev_day_close = history_rows[-2]["close_price"] if len(history_rows) > 1 else None

    current = _num(_pick(info, "currentPrice", "regularMarketPrice")) or last.get("close_price")
    previous = (
        _num(_pick(info, "regularMarketPreviousClose", "previousClose")) or prev_day_close
    )
    if current is not None and previous:
        change = round(current - previous, 4)
        change_pct = round(change / previous * 100, 4)
    else:
        change = _num(info.get("regularMarketChange"))
        change_pct = _num(info.get("regularMarketChangePercent"))

    quote = {
        "current_price": current,
        "change": change,
        "change_percent": change_pct,
        "previous_close": previous,
        "open_price": _num(_pick(info, "regularMarketOpen", "open")) or last.get("open_price"),
        "days_low": _num(_pick(info, "regularMarketDayLow", "dayLow")) or last.get("low_price"),
        "days_high": _num(_pick(info, "regularMarketDayHigh", "dayHigh")) or last.get("high_price"),
        "week52_low": _num(info.get("fiftyTwoWeekLow")),
        "week52_high": _num(info.get("fiftyTwoWeekHigh")),
        "volume": _int(_pick(info, "regularMarketVolume", "volume")) or last.get("volume"),
        "market_cap": _int(info.get("marketCap")),
        "pe_ratio": _num(info.get("trailingPE")),
        "eps": _num(info.get("trailingEps")),
    }

    company = {
        "company_name": _pick(info, "longName", "shortName"),
        "exchange": _pick(info, "fullExchangeName", "exchange"),
        "currency": info.get("currency"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "website": info.get("website"),
        "business_summary": info.get("longBusinessSummary"),
        "full_time_employees": _int(info.get("fullTimeEmployees")),
    }

    for key in QUOTE_REQUIRED:
        if quote[key] is None:
            missing.append(key)
    for key in COMPANY_FIELDS:
        if company[key] is None:
            missing.append(key)

    return {
        "company": company,
        "quote": quote,
        "history": history_rows,
        "news": _parse_news(news_raw),
        "missing": sorted(set(missing)),
    }