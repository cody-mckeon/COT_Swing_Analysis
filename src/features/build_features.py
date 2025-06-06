import pandas as pd
import numpy as np
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
    # COT net position ratios (relative exposure)
    df["mm_net_pct_oi"] = (df["mm_long"] - df["mm_short"]) / df["open_interest"]
    df["pm_net_pct_oi"] = (df["pm_long"] - df["pm_short"]) / df["open_interest"]
    df["sd_net_pct_oi"] = (df["sd_long"] - df["sd_short"]) / df["open_interest"]

    # one week change in the ratios
    df["mm_net_pct_oi_chg_1w"] = df["mm_net_pct_oi"].diff()
    df["pm_net_pct_oi_chg_1w"] = df["pm_net_pct_oi"].diff()
    df["sd_net_pct_oi_chg_1w"] = df["sd_net_pct_oi"].diff()

    # price/technical indicators
    df["return_1w"] = df["etf_close"].pct_change().shift(-1)
    log_returns = np.log(df["etf_close"]).diff()
    df["vol_26w"] = log_returns.rolling(window=26).std()

    delta = df["etf_close"].diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.rolling(14).mean()
    roll_down = down.rolling(14).mean()
    rs = roll_up / roll_down
    df["rsi_14"] = 100 - (100 / (1 + rs))

    df["ema_13"] = df["etf_close"].ewm(span=13, adjust=False).mean()

    ema_12 = df["etf_close"].ewm(span=12, adjust=False).mean()
    ema_26 = df["etf_close"].ewm(span=26, adjust=False).mean()
    macd_line = ema_12 - ema_26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    df["macd_hist"] = macd_line - signal_line

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
