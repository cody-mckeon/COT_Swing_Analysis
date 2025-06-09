import os, sys

# ─── insert project root on sys.path ─────────────────────────────────────────
# scripts is at <repo>/scripts/run_eval.py, so project root is one level up:
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)
# ───────────────────────────────────────────────────────────────────────────────

import argparse
from pathlib import Path
from src.eval.backtest import holdout_validation, run_backtest


def main() -> None:
    parser = argparse.ArgumentParser(description="Run evaluation pipeline")
    parser.add_argument("--features", required=True, help="Features CSV")
    parser.add_argument("--model", required=True, help="Model path")
    parser.add_argument("--test-start", required=True, help="Test start date")
    parser.add_argument("--commission", type=float, default=0.0005)
    parser.add_argument("--allow-shorts", action="store_true", help="Enable short trades")
    args = parser.parse_args()

    holdout_validation(args.features, args.model, args.test_start)
    df = run_backtest(
        args.features,
        args.model,
        args.test_start,
        args.commission,
        allow_shorts=args.allow_shorts,
    )
    Path("reports").mkdir(exist_ok=True)
    out_path = Path("reports/backtest_results.csv")
    df.to_csv(out_path, index=False)
    print(f"Results saved to {out_path}")


if __name__ == "__main__":
    main()
