import logging

from sqlalchemy.orm import Session

from app.models import (
    HistoricalPrice, NewsArticle, Quote, ScrapeLog, ScrapeStatus, Ticker, utcnow,
)
from app.scraper.yahoo import InvalidTickerError, fetch_ticker_data

log = logging.getLogger(__name__)

INVALID_PREFIX = "Invalid ticker"


def _write_log(db: Session, ticker_id, status, started, records, message):
    entry = ScrapeLog(
        ticker_id=ticker_id,
        status=status,
        started_at=started,
        finished_at=utcnow(),
        records_affected=records,
        error_message=message,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def scrape_ticker(db: Session, symbol: str) -> ScrapeLog:
    """Scrape one symbol and save it. Never raises: always returns a ScrapeLog row."""
    symbol = symbol.strip().upper()
    started = utcnow()
    ticker = db.query(Ticker).filter(Ticker.symbol == symbol).first()
    existing_id = ticker.id if ticker else None

    try:
        data = fetch_ticker_data(symbol)
    except InvalidTickerError as exc:
        return _write_log(db, existing_id, ScrapeStatus.FAILED, started, 0,
                          f"{INVALID_PREFIX}: {exc}")
    except Exception as exc:  # noqa: BLE001
        log.exception("Scrape failed for %s", symbol)
        return _write_log(db, existing_id, ScrapeStatus.FAILED, started, 0,
                          f"Scrape failed: {exc}")

    try:
        records = 0

        if ticker is None:
            ticker = Ticker(symbol=symbol)
            db.add(ticker)
        for key, value in data["company"].items():
            if value is not None:
                setattr(ticker, key, value)
        ticker.last_scraped_at = utcnow()
        db.flush()  # gives a new ticker its id
        records += 1

        quote = db.query(Quote).filter(Quote.ticker_id == ticker.id).first()
        if quote is None:
            quote = Quote(ticker_id=ticker.id)
            db.add(quote)
        for key, value in data["quote"].items():
            if value is not None:
                setattr(quote, key, value)
        quote.scraped_at = utcnow()
        records += 1

        existing_prices = {
            p.date: p
            for p in db.query(HistoricalPrice).filter(HistoricalPrice.ticker_id == ticker.id)
        }
        for row in data["history"]:
            price = existing_prices.get(row["date"])
            if price is None:
                price = HistoricalPrice(ticker_id=ticker.id, date=row["date"])
                db.add(price)
            price.open_price = row["open_price"]
            price.high_price = row["high_price"]
            price.low_price = row["low_price"]
            price.close_price = row["close_price"]
            price.volume = row["volume"]
            records += 1

        urls = [a["url"] for a in data["news"]]
        known_urls = set()
        if urls:
            known_urls = {
                u for (u,) in db.query(NewsArticle.url).filter(NewsArticle.url.in_(urls))
            }
        for article in data["news"]:
            if article["url"] in known_urls:
                continue
            db.add(NewsArticle(ticker_id=ticker.id, **article))
            records += 1

        db.commit()

        if data["missing"]:
            return _write_log(db, ticker.id, ScrapeStatus.PARTIAL, started, records,
                              "Missing fields: " + ", ".join(data["missing"]))
        return _write_log(db, ticker.id, ScrapeStatus.SUCCESS, started, records, None)

    except Exception as exc:  # noqa: BLE001
        db.rollback()
        log.exception("Saving data failed for %s", symbol)
        return _write_log(db, existing_id, ScrapeStatus.FAILED, started, 0,
                          f"Could not save data: {exc}")