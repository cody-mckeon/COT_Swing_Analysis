"""Deprecated wrapper that now delegates to CHRIS futures downloader."""
import os
import argparse
from src.data.load_chris import fetch_weekly_chris


def fetch_weekly_close(dataset_code: str, start_date: str = "2016-01-01", save_dir: str = "data/prices/"):
    slug = dataset_code.replace('/', '_')
    out_path = os.path.join(save_dir, f"{slug}_weekly.csv")
    return fetch_weekly_chris(dataset_code, start_date=start_date, api_key=os.getenv("NASDAQ_DATA_LINK"), save_path=out_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download CHRIS front-month futures")
    parser.add_argument("dataset_code", help="CHRIS dataset code, e.g. CHRIS/CME_CL1")
    parser.add_argument("--start", default="2016-01-01")
    parser.add_argument("--out-dir", default="data/prices/")
    args = parser.parse_args()
    fetch_weekly_close(args.dataset_code, start_date=args.start, save_dir=args.out_dir)
