import os
import sys
from pathlib import Path
from typing import Optional
import argparse
import pandas as pd
import numpy as np

# ensure project root is on path so "src" is importable when running as script
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from src.eval.backtest import run_backtest


def main(argv: Optional[list] = None) -> None:
    parser = argparse.ArgumentParser(description="Run rolling backtests")
    parser.add_argument("--features", required=True, help="path to base features CSV")
    parser.add_argument("--model", required=True, help="path to joblib model file")
    parser.add_argument("--start", default="2017-01-01", help="first test-start date")
    parser.add_argument(
        "--end",
        default=pd.Timestamp.today().strftime("%Y-%m-%d"),
        help="last test-start date",
    )
    parser.add_argument("--freq", default="6M", help="frequency for rolling splits")
    parser.add_argument("--commission", type=float, default=0.0005, help="round-trip cost per trade")
    parser.add_argument(
        "--thresholds",
        default="0.90",
        help="comma-separated percentile(s) for contrarian overlay (e.g. 0.85,0.90,0.95)",
    )

    args = parser.parse_args(argv)

    # parse thresholds into list of floats
    thresh_list = [float(x) for x in args.thresholds.split(",")]

    # generate test_start dates
    test_starts = pd.date_range(args.start, args.end, freq=args.freq).strftime("%Y-%m-%d")

    # container for all results
    results = []

    for q in thresh_list:
        # 1) load & flag extreme weeks based on percentile q
        df = pd.read_csv(args.features, parse_dates=["week"])
        p = df["mm_net_pct_oi"].quantile(q)
        df["extreme_spec_long"] = (df["mm_net_pct_oi"] >= p).astype(int)
        temp_csv = f"/tmp/features_gc_q{int(q*100)}.csv"
        df.to_csv(temp_csv, index=False)

        # 2) run rolling backtest for each split
        for ts in test_starts:
            bt = run_backtest(temp_csv, args.model, ts, args.commission)
            if bt.empty:
                cum, sharpe, maxdd = (np.nan, np.nan, np.nan)
            else:
                cum = bt["cum_return"].iloc[-1]
                ret = bt["strategy_ret"]
                sharpe = ret.mean() / ret.std() * np.sqrt(52) if ret.std() else np.nan
                peak = (1 + ret).cumprod().cummax()
                maxdd = ((peak - (1 + ret).cumprod()) / peak).max()
            results.append({
                "threshold": q,
                "test_start": ts,
                "cum_return": cum,
                "sharpe": sharpe,
                "max_drawdown": maxdd,
            })

    # dump full summary
    out_path = Path("reports/rolling_thresholds_gc.csv")
    out_path.parent.mkdir(exist_ok=True)
    pd.DataFrame(results).to_csv(out_path, index=False)
    print(f"Wrote rolling threshold comparison to {out_path}")


if __name__ == "__main__":
    main()
