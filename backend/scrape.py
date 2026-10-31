import argparse
import json
import time
from pathlib import Path

from app import config
from app.database import SessionLocal
from app.scraper.service import scrape_ticker


def main():
    parser = argparse.ArgumentParser(description="Scrape Yahoo Finance data into the database.")
    parser.add_argument("symbols", nargs="*", help="Ticker symbols, e.g. AAPL MSFT INFY.NS")
    parser.add_argument("--all", action="store_true", help="Scrape every symbol in tickers.json")
    args = parser.parse_args()

    symbols = [s.upper() for s in args.symbols]
    if args.all:
        seed_file = Path(__file__).with_name("tickers.json")
        seed = json.loads(seed_file.read_text(encoding="utf-8"))
        symbols += [item["symbol"] for item in seed if item["symbol"] not in symbols]
    if not symbols:
        parser.error("Give at least one symbol (python scrape.py AAPL) or use --all")

    db = SessionLocal()
    try:
        for i, symbol in enumerate(symbols):
            if i > 0:
                time.sleep(config.REQUEST_DELAY_SECONDS)
            print(f"Scraping {symbol} ...")
            log = scrape_ticker(db, symbol)
            line = f"  [{log.status}] {symbol}: {log.records_affected} records"
            if log.error_message:
                line += f" - {log.error_message}"
            print(line)
    finally:
        db.close()


if __name__ == "__main__":
    main()