import datetime as dt
import logging
import math
import re
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import config, models, schemas
from app.database import get_db
from app.scraper.service import INVALID_PREFIX, scrape_ticker

app = FastAPI(title="Yahoo Finance Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

SYMBOL_RE = re.compile(r"^[A-Za-z0-9.\-^=]{1,20}$")


@app.exception_handler(Exception)
async def unhandled_error(request, exc):
    logging.exception("Unhandled error")
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong. Please try again."},
    )


def paginate(query, page: int, page_size: int, schema):
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "count": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, math.ceil(total / page_size)),
        "results": [schema.model_validate(row) for row in rows],
    }


def get_ticker_or_404(db: Session, symbol: str) -> models.Ticker:
    ticker = db.query(models.Ticker).filter(models.Ticker.symbol == symbol.upper()).first()
    if ticker is None:
        raise HTTPException(status_code=404, detail=f"Ticker '{symbol.upper()}' is not tracked yet.")
    return ticker


@app.get("/api/health")
def health():
    return {"status": "ok"}


SORTABLE = {
    "symbol": models.Ticker.symbol,
    "company_name": models.Ticker.company_name,
    "current_price": models.Quote.current_price,
    "change": models.Quote.change,
    "change_percent": models.Quote.change_percent,
    "market_cap": models.Quote.market_cap,
}


@app.get("/api/tickers", response_model=schemas.Page[schemas.TickerListOut])
def list_tickers(
    search: Optional[str] = None,
    sort_by: str = "symbol",
    order: str = "asc",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(models.Ticker).outerjoin(
        models.Quote, models.Quote.ticker_id == models.Ticker.id
    )
    if search and search.strip():
        like = f"%{search.strip()}%"
        query = query.filter(
            or_(models.Ticker.symbol.ilike(like), models.Ticker.company_name.ilike(like))
        )
    column = SORTABLE.get(sort_by, models.Ticker.symbol)
    column = column.desc() if order == "desc" else column.asc()
    query = query.order_by(column.nulls_last(), models.Ticker.id)
    return paginate(query, page, page_size, schemas.TickerListOut)


@app.post("/api/tickers", response_model=schemas.TickerDetailOut, status_code=201)
def add_ticker(payload: schemas.AddTickerRequest, db: Session = Depends(get_db)):
    symbol = payload.symbol.strip().upper()
    if not SYMBOL_RE.match(symbol):
        raise HTTPException(status_code=400, detail="That doesn't look like a valid ticker symbol.")

    log = scrape_ticker(db, symbol)
    if log.status == models.ScrapeStatus.FAILED:
        if (log.error_message or "").startswith(INVALID_PREFIX):
            raise HTTPException(
                status_code=404,
                detail=f"We couldn't find a ticker called '{symbol}'. Please check the symbol and try again.",
            )
        raise HTTPException(
            status_code=502,
            detail="Yahoo Finance couldn't be reached right now. Please try again in a minute.",
        )
    return get_ticker_or_404(db, symbol)


@app.get("/api/tickers/{symbol}", response_model=schemas.TickerDetailOut)
def get_ticker(symbol: str, db: Session = Depends(get_db)):
    return get_ticker_or_404(db, symbol)


@app.get(
    "/api/tickers/{symbol}/history",
    response_model=schemas.Page[schemas.HistoricalPriceOut],
)
def get_history(
    symbol: str,
    start: Optional[dt.date] = None,
    end: Optional[dt.date] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    ticker = get_ticker_or_404(db, symbol)
    query = db.query(models.HistoricalPrice).filter(models.HistoricalPrice.ticker_id == ticker.id)
    if start:
        query = query.filter(models.HistoricalPrice.date >= start)
    if end:
        query = query.filter(models.HistoricalPrice.date <= end)
    query = query.order_by(models.HistoricalPrice.date.asc())
    return paginate(query, page, page_size, schemas.HistoricalPriceOut)


@app.get("/api/tickers/{symbol}/news", response_model=schemas.Page[schemas.NewsOut])
def get_news(
    symbol: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    ticker = get_ticker_or_404(db, symbol)
    query = (
        db.query(models.NewsArticle)
        .filter(models.NewsArticle.ticker_id == ticker.id)
        .order_by(models.NewsArticle.published_at.desc().nulls_last(), models.NewsArticle.id.desc())
    )
    return paginate(query, page, page_size, schemas.NewsOut)


@app.get("/api/scrape-logs", response_model=schemas.Page[schemas.ScrapeLogOut])
def list_scrape_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(models.ScrapeLog).order_by(models.ScrapeLog.id.desc())
    return paginate(query, page, page_size, schemas.ScrapeLogOut)