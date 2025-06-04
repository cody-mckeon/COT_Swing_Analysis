import os
import time
import pandas as pd
import yfinance as yf
import logging
from yfinance.exceptions import YFRateLimitError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
if not logger.handlers:
    logger.addHandler(handler)


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
    for attempt in range(1, max_retries + 1):
        try:
            df = yf.download(
                ticker, start=start_date, progress=False, auto_adjust=True
            )
            break
        except YFRateLimitError as exc:
            if attempt == max_retries:
                raise RuntimeError(
                    f"Rate limit hit for {ticker} after {max_retries} attempts"
                ) from exc
            wait = retry_delay * attempt
            logger.warning(f"Rate limited, retrying in {wait}s (attempt {attempt}/{max_retries})")
            time.sleep(wait)
    else:
        # Should never reach here
        raise RuntimeError(f"Failed to download data for {ticker}")
    if df.empty:
        raise RuntimeError(f"No data found for {ticker}")
    df = df[["Close"]].rename(columns={"Close": "etf_close"})
    df.index = pd.to_datetime(df.index)
    weekly = df["etf_close"].resample("W-FRI").last().dropna().reset_index().rename(columns={"index": "week"})
    os.makedirs(save_dir, exist_ok=True)
    safe_name = ticker.replace("=", "_").replace("/", "_")
    out_path = os.path.join(save_dir, f"{safe_name}.csv")
    weekly.to_csv(out_path, index=False)
    logger.info(f"Saved weekly prices to {out_path}")
    return weekly

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Download and resample price data")
    parser.add_argument("ticker", help="Yahoo Finance ticker, e.g. MGC=F")
    parser.add_argument("--start", default="2016-01-01")
    parser.add_argument("--out-dir", default="data/prices/")
    parser.add_argument("--max-retries", type=int, default=3, help="Number of retries when rate limited")
    parser.add_argument("--retry-delay", type=int, default=5, help="Base delay between retries in seconds")
    args = parser.parse_args()
    fetch_weekly_close(
        args.ticker,
        start_date=args.start,
        save_dir=args.out_dir,
        max_retries=args.max_retries,
        retry_delay=args.retry_delay,
    )
