import pandas as pd
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
if not logger.handlers:
    logger.addHandler(handler)

def merge_cot_with_price(cot_csv: str, price_csv: str, out_csv: str) -> pd.DataFrame:
    """Merge processed COT data with weekly CHRIS prices."""
    cot = pd.read_csv(cot_csv, parse_dates=["report_date"])
    price = pd.read_csv(price_csv, parse_dates=["date"])
    cot = cot.rename(columns={"report_date": "week"})
    price = price.rename(columns={"date": "week", "close": "etf_close"})
    merged = pd.merge(cot, price, on="week", how="inner")
    merged = merged.sort_values("week").reset_index(drop=True)
    merged.to_csv(out_csv, index=False)
    logger.info(f"Saved merged COT and price data to {out_csv}")
    return merged

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Merge COT and price CSVs")
    parser.add_argument("--cot", required=True)
    parser.add_argument("--price", required=True)
    parser.add_argument("--out", default="data/processed/merged.csv")
    args = parser.parse_args()
    merge_cot_with_price(args.cot, args.price, args.out)
