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

try:
    from yfinance.exceptions import YFRateLimitError, YFInvalidPeriodError
except Exception:  # fall back if yfinance lacks these exceptions
    YFRateLimitError = Exception
    YFInvalidPeriodError = Exception
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
            if df is None or df.empty:
                raise ValueError("No data returned from yfinance")
            df.index.name = "Date"
            return df
        except YFRateLimitError as e:
            attempt += 1
            if attempt >= max_retries:
                logger.error(f"Rate limit exceeded for {ticker}: {e}")
                raise
            logger.warning(f"Rate limit error for {ticker}: {e}. Retrying in {retry_delay}s…")
            time.sleep(retry_delay)
        except YFInvalidPeriodError as e:
            # Some tickers require omitting the end date
            logger.warning(f"YFInvalidPeriodError for {ticker} with explicit end: {e}. Retrying with start-only…")
        except Exception as e:
            attempt += 1
            if attempt >= max_retries:
                logger.error(f"Failed to download {ticker} after {max_retries} attempts: {e}")
                raise
            logger.warning(f"Error downloading {ticker}: {e}. Retrying in {retry_delay}s…")
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

def fetch_weekly_close(dataset_code: str, start_date: str = "2016-01-01", save_dir: str = "data/prices/"):
    slug = dataset_code.replace('/', '_')
    out_path = os.path.join(save_dir, f"{slug}_weekly.csv")
    return fetch_weekly_chris(dataset_code, start_date=start_date, api_key=os.getenv("NASDAQ_DATA_LINK"), save_path=out_path)


def fetch_weekly_close(
    ticker: str,
    start_date: str = "2016-01-01",
    save_dir: str = "data/prices/",
    max_retries: int = 3,
    retry_delay: int = 5,
) -> pd.DataFrame:
    """Download daily prices for ``ticker`` and resample to weekly Friday close.

    The function retries downloads when Yahoo Finance responds with a
    :class:`~yfinance.exceptions.YFRateLimitError`.
    """
    logger.info(
        f"Downloading price for {ticker} since {start_date} via yfinance…"
    )

    attempt = 0
    while attempt < max_retries:
        logger.info(
            f"[Attempt {attempt+1}/{max_retries}] Downloading price for {ticker} since {start_date} (explicit start/end)…"
        )
        try:
            df = yf.download(
                ticker,
                start=start_date,
                end=pd.Timestamp.today().strftime("%Y-%m-%d"),
                progress=False,
                auto_adjust=True,
                threads=False,
            )
        except YFInvalidPeriodError as e:
            logger.warning(
                f"⚠️ YFInvalidPeriodError for {ticker} with explicit end: {e}. Retrying with start-only…"
            )
            df = yf.download(
                ticker,
                start=start_date,
                progress=False,
                auto_adjust=True,
                threads=False,
            )

        try:
            if df is None or df.empty:
                raise ValueError(f"No data returned for {ticker} (empty response)")

            df = df[["Close"]].rename(columns={"Close": "etf_close"})
            df.index = pd.to_datetime(df.index)
            weekly = (
                df["etf_close"]
                .resample("W-FRI")
                .last()
                .dropna()
                .reset_index()
                .rename(columns={"index": "week"})
            )
            os.makedirs(save_dir, exist_ok=True)
            safe_name = ticker.replace("=", "_").replace("/", "_")
            out_path = os.path.join(save_dir, f"{safe_name}.csv")
            weekly.to_csv(out_path, index=False)
            logger.info(f"Saved weekly prices to {out_path}")
            return weekly

        except YFRateLimitError as e:
            attempt += 1
            if attempt < max_retries:
                logger.warning(
                    f"⚠️ Rate‑limited by yfinance on {ticker}: {e}. Retrying in {retry_delay} seconds…"
                )
                time.sleep(retry_delay)
                continue
            else:
                logger.error(
                    f"❌ Exhausted retries for {ticker} (rate-limit). Giving up."
                )
                raise
        except Exception as e:
            attempt += 1
            if attempt < max_retries:
                logger.warning(
                    f"⚠️ Download failed for {ticker}: {e}. Retrying in {retry_delay} seconds…"
                )
                time.sleep(retry_delay)
                continue
            else:
                logger.error(
                    f"❌ Exhausted retries for {ticker}. Last error: {e}"
                )
                raise

    raise RuntimeError(
        f"Failed to fetch data for {ticker} after {max_retries} attempts"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download CHRIS front-month futures")
    parser.add_argument("dataset_code", help="CHRIS dataset code, e.g. CHRIS/CME_CL1")
    parser.add_argument("--start", default="2016-01-01")
    parser.add_argument("--out-dir", default="data/prices/")
    args = parser.parse_args()
    fetch_weekly_close(args.dataset_code, start_date=args.start, save_dir=args.out_dir)
