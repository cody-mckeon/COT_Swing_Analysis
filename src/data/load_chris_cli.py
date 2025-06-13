"""CLI wrapper for :func:`src.data.load_chris.fetch_weekly_chris`.

This command is no longer actively used because Nasdaq Data Link
requests are unreliable. Keeping it for reference only.
"""

import argparse
import os
from src.data.load_chris import fetch_weekly_chris


def main():
    parser = argparse.ArgumentParser(
        description="Fetch weekly front-month futures from CHRIS and save to CSV."
    )
    parser.add_argument(
        "chris_code",
        type=str,
        help="CHRIS dataset code, e.g. 'CHRIS/CME_CL1' or 'CHRIS/CME_GC1'"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default="2016-01-01",
        help="Earliest date to fetch, in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--save-dir",
        type=str,
        default="data/prices",
        help="Directory to save output CSV"
    )
    args = parser.parse_args()

    ticker_slug = args.chris_code.replace("/", "_")
    out_path = os.path.join(args.save_dir, f"{ticker_slug}_weekly.csv")

    fetch_weekly_chris(
        dataset_code=args.chris_code,
        start_date=args.start_date,
        api_key=os.getenv("NASDAQ_DATA_LINK"),
        save_path=out_path,
    )


if __name__ == "__main__":
    main()
