import datetime as dt
from typing import Optional

from sqlalchemy import (
    BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

Price = Numeric(18, 4, asdecimal=False)


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


class ScrapeStatus:
    SUCCESS = "Success"
    PARTIAL = "Partial"
    FAILED = "Failed"


class Ticker(Base):
    __tablename__ = "tickers"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(255))
    exchange: Mapped[Optional[str]] = mapped_column(String(100))
    currency: Mapped[Optional[str]] = mapped_column(String(10))
    sector: Mapped[Optional[str]] = mapped_column(String(100))
    industry: Mapped[Optional[str]] = mapped_column(String(150))
    website: Mapped[Optional[str]] = mapped_column(String(500))
    business_summary: Mapped[Optional[str]] = mapped_column(Text)
    full_time_employees: Mapped[Optional[int]] = mapped_column(Integer)
    last_scraped_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime)

    quote: Mapped[Optional["Quote"]] = relationship(
        back_populates="ticker", uselist=False, cascade="all, delete-orphan"
    )
    prices: Mapped[list["HistoricalPrice"]] = relationship(
        back_populates="ticker", cascade="all, delete-orphan"
    )
    news: Mapped[list["NewsArticle"]] = relationship(
        back_populates="ticker", cascade="all, delete-orphan"
    )


class Quote(Base):
    """Latest snapshot for a ticker. One row per ticker, updated on every scrape."""

    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker_id: Mapped[int] = mapped_column(ForeignKey("tickers.id"), unique=True)
    current_price: Mapped[Optional[float]] = mapped_column(Price)
    change: Mapped[Optional[float]] = mapped_column(Price)
    change_percent: Mapped[Optional[float]] = mapped_column(Price)
    previous_close: Mapped[Optional[float]] = mapped_column(Price)
    open_price: Mapped[Optional[float]] = mapped_column(Price)
    days_low: Mapped[Optional[float]] = mapped_column(Price)
    days_high: Mapped[Optional[float]] = mapped_column(Price)
    week52_low: Mapped[Optional[float]] = mapped_column(Price)
    week52_high: Mapped[Optional[float]] = mapped_column(Price)
    volume: Mapped[Optional[int]] = mapped_column(BigInteger)
    market_cap: Mapped[Optional[int]] = mapped_column(BigInteger)
    pe_ratio: Mapped[Optional[float]] = mapped_column(Price)
    eps: Mapped[Optional[float]] = mapped_column(Price)
    scraped_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

    ticker: Mapped["Ticker"] = relationship(back_populates="quote")


class HistoricalPrice(Base):
    __tablename__ = "historical_prices"
    __table_args__ = (
        UniqueConstraint("ticker_id", "date", name="uq_price_ticker_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker_id: Mapped[int] = mapped_column(ForeignKey("tickers.id"), index=True)
    date: Mapped[dt.date] = mapped_column(Date)
    open_price: Mapped[Optional[float]] = mapped_column(Price)
    high_price: Mapped[Optional[float]] = mapped_column(Price)
    low_price: Mapped[Optional[float]] = mapped_column(Price)
    close_price: Mapped[Optional[float]] = mapped_column(Price)
    volume: Mapped[Optional[int]] = mapped_column(BigInteger)

    ticker: Mapped["Ticker"] = relationship(back_populates="prices")


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker_id: Mapped[int] = mapped_column(ForeignKey("tickers.id"), index=True)
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(1000), unique=True)
    source: Mapped[Optional[str]] = mapped_column(String(200))
    published_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime)

    ticker: Mapped["Ticker"] = relationship(back_populates="news")


class ScrapeLog(Base):
    __tablename__ = "scrape_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tickers.id"))
    status: Mapped[str] = mapped_column(String(10))  # Success / Partial / Failed
    started_at: Mapped[dt.datetime] = mapped_column(DateTime)
    finished_at: Mapped[dt.datetime] = mapped_column(DateTime)
    records_affected: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    ticker: Mapped[Optional["Ticker"]] = relationship()

    @property
    def ticker_symbol(self) -> Optional[str]:
        return self.ticker.symbol if self.ticker else None