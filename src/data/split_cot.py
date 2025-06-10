import os
import argparse
import pandas as pd
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
if not logger.handlers:
    logger.addHandler(_handler)


def split_cot(in_csv: str, gold_csv: str, crude_csv: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split combined COT CSV into separate gold and crude files."""
    df = pd.read_csv(in_csv, parse_dates=["report_date"], low_memory=False)
    df["contract_code"] = df["contract_code"].astype(str)
    # Use contract_code which stays constant even when market_name values change
    gold = df[df["contract_code"] == "088691"].copy()
    crude = df[df["contract_code"] == "067651"].copy()

    for out_path, subset in ((gold_csv, gold), (crude_csv, crude)):
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        subset.sort_values("report_date").to_csv(out_path, index=False)
        logger.info(f"Wrote {len(subset)} rows to {out_path}")

    return gold, crude


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Split combined COT data")
    parser.add_argument("--in-csv", required=True, help="Combined COT CSV")
    parser.add_argument("--gold", default="data/processed/cot_gold.csv")
    parser.add_argument("--crude", default="data/processed/cot_crude.csv")
    args = parser.parse_args()
    split_cot(args.in_csv, args.gold, args.crude)
