import datetime as dt
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    count: int
    page: int
    page_size: int
    total_pages: int
    results: list[T]


class QuoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    current_price: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    previous_close: Optional[float] = None
    open_price: Optional[float] = None
    days_low: Optional[float] = None
    days_high: Optional[float] = None
    week52_low: Optional[float] = None
    week52_high: Optional[float] = None
    volume: Optional[int] = None
    market_cap: Optional[int] = None
    pe_ratio: Optional[float] = None
    eps: Optional[float] = None
    scraped_at: Optional[dt.datetime] = None


class TickerListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    company_name: Optional[str] = None
    exchange: Optional[str] = None
    currency: Optional[str] = None
    last_scraped_at: Optional[dt.datetime] = None
    quote: Optional[QuoteOut] = None


class TickerDetailOut(TickerListOut):
    sector: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    business_summary: Optional[str] = None
    full_time_employees: Optional[int] = None


class HistoricalPriceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: dt.date
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    close_price: Optional[float] = None
    volume: Optional[int] = None


class NewsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    url: str
    source: Optional[str] = None
    published_at: Optional[dt.datetime] = None


class ScrapeLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker_symbol: Optional[str] = None
    status: str
    started_at: dt.datetime
    finished_at: dt.datetime
    records_affected: int
    error_message: Optional[str] = None


class AddTickerRequest(BaseModel):
    symbol: str