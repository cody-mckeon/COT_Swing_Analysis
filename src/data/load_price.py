"""
Download historical crude oil and gold futures prices from Yahoo Finance.

This script fetches daily data for ``CL=F`` and ``GC=F`` back to
January 1, 2016 and saves both the raw daily prices and weekly
(Friday-close) resampled series under ``data/prices``.

It supports retry logic to handle transient network or rate-limit errors.
The number of retries and delay between them can be configured via
command-line arguments.

Usage:
    python -m src.data.load_price [--start YYYY-MM-DD] [--end YYYY-MM-DD] \
        [--max-retries N] [--retry-delay SECONDS]

This will create files like ``cl_daily.csv`` and ``cl_weekly.csv`` in the
``data/prices`` directory.
"""

import os
import time
import argparse
import logging

import pandas as pd
import yfinance as yf
from yfinance.exceptions import YFRateLimitError, YFInvalidPeriodError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
if not logger.handlers:
    logger.addHandler(_handler)

SYMBOLS = {
    "CL": "CL=F",
    "GC": "GC=F",
}

DEFAULT_START = "2016-01-01"
DEFAULT_END = pd.Timestamp.today().strftime("%Y-%m-%d")
DEFAULT_RETRIES = 5
DEFAULT_DELAY = 5

DATA_DIR = os.path.join("data", "prices")
os.makedirs(DATA_DIR, exist_ok=True)


def fetch_daily_history(ticker: str, start: str, end: str, max_retries: int, retry_delay: int) -> pd.DataFrame:
    """Download daily history for ``ticker`` with retry logic."""
    attempt = 0
    while attempt < max_retries:
        try:
            logger.info(
                f"Downloading {ticker} from {start} to {end} (attempt {attempt + 1}/{max_retries})"
            )
            df = yf.download(
                ticker,
                start=start,
                end=end,
                progress=False,
                auto_adjust=False,
            )
        except YFInvalidPeriodError as e:
            # Some tickers require omitting the end date
            logger.warning(
                f"YFInvalidPeriodError for {ticker} with explicit end: {e}. Retrying with start-only…"
            )
            df = yf.download(
                ticker,
                start=start,
                progress=False,
                auto_adjust=False,
            )
        except YFRateLimitError as e:
            attempt += 1
            if attempt >= max_retries:
                logger.error(f"Rate limit exceeded for {ticker}: {e}")
                raise
            logger.warning(
                f"Rate limit error for {ticker}: {e}. Retrying in {retry_delay}s…"
            )
            time.sleep(retry_delay)
            continue
        except Exception as e:
            attempt += 1
            if attempt >= max_retries:
                logger.error(f"Failed to download {ticker} after {max_retries} attempts: {e}")
                raise
            logger.warning(f"Error downloading {ticker}: {e}. Retrying in {retry_delay}s…")
            time.sleep(retry_delay)
            continue

        if df is not None and not df.empty:
            df.index.name = "Date"
            return df

        # Empty DataFrame triggers retry
        attempt += 1
        if attempt >= max_retries:
            break
        logger.warning(
            f"No data returned for {ticker}. Retrying in {retry_delay}s…"
        )
        time.sleep(retry_delay)

    raise RuntimeError(f"Unable to fetch {ticker} after {max_retries} attempts")


def resample_to_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """Resample a daily price DataFrame to weekly Friday closes."""
    if "Close" not in df.columns:
        raise KeyError("DataFrame must contain a 'Close' column")
    weekly = df[["Close"]].resample("W-FRI").last()
    weekly.index.name = "Date"
    return weekly


def main() -> None:
    parser = argparse.ArgumentParser(description="Download crude and gold futures via yfinance")
    parser.add_argument("--start", default=DEFAULT_START, help="start date YYYY-MM-DD")
    parser.add_argument("--end", default=DEFAULT_END, help="end date YYYY-MM-DD")
    parser.add_argument("--max-retries", type=int, default=DEFAULT_RETRIES, help="number of download retries")
    parser.add_argument("--retry-delay", type=int, default=DEFAULT_DELAY, help="seconds between retries")
    args = parser.parse_args()

    for short, ticker in SYMBOLS.items():
        daily = fetch_daily_history(ticker, args.start, args.end, args.max_retries, args.retry_delay)
        daily_csv = os.path.join(DATA_DIR, f"{short.lower()}_daily.csv")
        logger.info(f"Saving daily prices to {daily_csv}")
        daily.to_csv(daily_csv)

        weekly = resample_to_weekly(daily)
        weekly_csv = os.path.join(DATA_DIR, f"{short.lower()}_weekly.csv")
        logger.info(f"Saving weekly prices to {weekly_csv}")
        weekly.to_csv(weekly_csv)


if __name__ == "__main__":
    main()
