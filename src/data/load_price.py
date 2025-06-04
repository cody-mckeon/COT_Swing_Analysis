import os
import pandas as pd
import yfinance as yf
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
if not logger.handlers:
    logger.addHandler(handler)


def fetch_weekly_close(ticker: str, start_date: str = "2016-01-01", save_dir: str = "data/prices/") -> pd.DataFrame:
    """Download daily prices for `ticker`, resample to weekly Friday close and save to CSV."""
    logger.info(f"Downloading price for {ticker} since {start_date} via yfinance…")
    df = yf.download(ticker, start=start_date, progress=False, auto_adjust=True)
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
    args = parser.parse_args()
    fetch_weekly_close(args.ticker, start_date=args.start, save_dir=args.out_dir)
