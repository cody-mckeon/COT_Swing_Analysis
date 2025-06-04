import pandas as pd
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
if not logger.handlers:
    logger.addHandler(handler)

def build_features(merged_csv: str, out_csv: str) -> pd.DataFrame:
    """Given merged COT and price data, compute feature set."""
    df = pd.read_csv(merged_csv, parse_dates=["week"])
    df = df.sort_values("week").reset_index(drop=True)
    # example features: net positions as pct of open interest
    df["mm_net_pct_oi"] = (df["mm_long"] - df["mm_short"]) / df["open_interest"]
    df["pm_net_pct_oi"] = (df["pm_long"] - df["pm_short"]) / df["open_interest"]
    df["sd_net_pct_oi"] = (df["sd_long"] - df["sd_short"]) / df["open_interest"]
    # price return for next week as target
    df["return"] = df["etf_close"].pct_change().shift(-1)
    df.dropna(inplace=True)
    df.to_csv(out_csv, index=False)
    logger.info(f"Saved features to {out_csv}")
    return df

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build ML features")
    parser.add_argument("--merged", required=True)
    parser.add_argument("--out", default="data/processed/features.csv")
    args = parser.parse_args()
    build_features(args.merged, args.out)
