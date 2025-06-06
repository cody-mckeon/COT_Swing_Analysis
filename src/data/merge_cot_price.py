import pandas as pd
import logging
import csv



def _load_and_clean_price(price_csv: str) -> pd.DataFrame:
    """Read a price CSV and ensure a single-row header with standard columns."""
    # Peek at the first row to detect yfinance's "Ticker" prefix row
    with open(price_csv, newline="") as fh:
        reader = csv.reader(fh)
        first = next(reader, [])

    if first and first[0].strip().lower() == "ticker":
        df = pd.read_csv(price_csv, header=1)
    else:
        df = pd.read_csv(price_csv)
        if any(col.startswith("Unnamed") for col in df.columns):
            try:
                df = pd.read_csv(price_csv, header=[0, 1], index_col=0)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(-1)
                    df.reset_index(inplace=True)
            except Exception:
                df = pd.read_csv(price_csv, header=1)

    # Normalize column names
    df.columns = [c.strip().lower() for c in df.columns]
    if "adj close" in df.columns:
        df = df.drop(columns=["adj close"])

    if "date" not in df.columns:
        if df.index.name and "date" in df.index.name.lower():
            df = df.reset_index()
        else:
            df = df.rename(columns={df.columns[0]: "date"})

    keep = ["date", "open", "high", "low", "close", "volume"]
    df = df[[c for c in keep if c in df.columns]]
    return df


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


    price = _load_and_clean_price(price_csv)

    if "date" not in price.columns:
        raise KeyError("Price CSV must contain a date column")

    # `_load_and_clean_price` normalizes column names to lowercase and removes
    # any additional header rows.  Convert the date column to a timestamp and
    # standardize the close column name.
    price["report_date"] = pd.to_datetime(
        price["date"], format="%Y-%m-%d", errors="coerce"
    )
    price = price.dropna(subset=["report_date"])

    if "close" in price.columns:
        price = price.rename(columns={"close": "etf_close"})
    elif "Close" in price.columns:
        # In case the cleaning step failed to normalize for some reason
        price = price.rename(columns={"Close": "etf_close"})

    cols = ["report_date", "open", "high", "low", "etf_close", "volume"]
    price = price[[c for c in cols if c in price.columns]]

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
