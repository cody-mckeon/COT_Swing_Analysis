import pandas as pd
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
if not logger.handlers:
    logger.addHandler(handler)

def merge_cot_with_price(
    cot_csv: str,
    price_csv: str,
    out_csv: str,
    market: str | None = None,
) -> pd.DataFrame:
    """Merge processed COT data with daily prices.

    Parameters
    ----------
    cot_csv:
        Path to the CSV containing disaggregated COT data for multiple markets.
    price_csv:
        Path to the daily price data for a single instrument.
    out_csv:
        Where the merged dataset should be written.
    market:
        Optional market name filter. If provided, only rows where
        ``market_name`` contains this string (case-insensitive) will be used.
    """

    cot = pd.read_csv(cot_csv, parse_dates=["report_date"])
    if market:
        cot = cot[cot["market_name"].str.contains(market, case=False, na=False)]

    price = pd.read_csv(price_csv)
    if "Date" in price.columns:
        price["report_date"] = pd.to_datetime(price["Date"])
    elif "date" in price.columns:
        price["report_date"] = pd.to_datetime(price["date"])
    elif "week" in price.columns:
        price["report_date"] = pd.to_datetime(price["week"])
    else:
        raise KeyError("Price CSV must contain a date column")

    if "Close" in price.columns:
        price = price.rename(columns={"Close": "etf_close"})
    elif "close" in price.columns:
        price = price.rename(columns={"close": "etf_close"})

    price = price[["report_date", "etf_close"]]

    merged = pd.merge(cot, price, on="report_date", how="inner")
    merged["week"] = merged["report_date"] + pd.offsets.Week(weekday=4)
    merged = merged.sort_values("report_date").reset_index(drop=True)
    merged.to_csv(out_csv, index=False)
    logger.info(f"Saved merged COT and price data to {out_csv}")
    return merged

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Merge COT and price CSVs")
    parser.add_argument("--cot", required=True)
    parser.add_argument("--price", required=True)
    parser.add_argument("--out", default="data/processed/merged.csv")
    parser.add_argument("--market", default=None, help="optional market filter")
    args = parser.parse_args()
    merge_cot_with_price(args.cot, args.price, args.out, market=args.market)
