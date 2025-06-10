import os
import sys
from pathlib import Path
import argparse
import pandas as pd

# ensure project root is on path so "src" is importable when running as script
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from src.eval.backtest import run_backtest


def main() -> None:
    parser = argparse.ArgumentParser(description="Run rolling backtests")
    parser.add_argument("--features", required=True, help="Features CSV")
    parser.add_argument("--model", required=True, help="Trained model path")
    parser.add_argument("--start", default="2017-01-01", help="Earliest test start date")
    parser.add_argument(
        "--end",
        default=pd.Timestamp.today().strftime("%Y-%m-%d"),
        help="Latest test start date",
    )
    parser.add_argument("--freq", default="6M", help="Frequency for rolling splits")
    parser.add_argument("--commission", type=float, default=0.0005, help="Commission per round trip")

    args = parser.parse_args()

    dates = pd.date_range(args.start, args.end, freq=args.freq).strftime("%Y-%m-%d")

    results = []
    for ts in dates:
        df_bt = run_backtest(
            features_csv=args.features,
            model_path=args.model,
            test_start_date=ts,
            commission_per_trade=args.commission,
        )
        cum = df_bt["cum_return"].iloc[-1]
        ret = df_bt["strategy_ret"]
        sharpe = ret.mean() / ret.std() * (52 ** 0.5) if ret.std() else 0
        maxdd = ((1 + ret).cumprod().cummax() - (1 + ret).cumprod()).max()
        results.append(
            {
                "test_start": ts,
                "cum_return": cum,
                "sharpe": sharpe,
                "max_drawdown": maxdd,
            }
        )

    df_results = pd.DataFrame(results)
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    out_path = reports_dir / "rolling_backtest_gc.csv"
    df_results.to_csv(out_path, index=False)
    print(f"Wrote rolling backtest summary to {out_path}")


if __name__ == "__main__":
    main()
