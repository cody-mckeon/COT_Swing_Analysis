import argparse
from pathlib import Path
from src.eval.backtest import holdout_validation, run_backtest


def main() -> None:
    parser = argparse.ArgumentParser(description="Run evaluation pipeline")
    parser.add_argument("--features", required=True, help="Features CSV")
    parser.add_argument("--model", required=True, help="Model path")
    parser.add_argument("--test-start", required=True, help="Test start date")
    parser.add_argument("--commission", type=float, default=0.0005)
    args = parser.parse_args()

    holdout_validation(args.features, args.model, args.test_start)
    df = run_backtest(args.features, args.model, args.test_start, args.commission)
    Path("reports").mkdir(exist_ok=True)
    out_path = Path("reports/backtest_results.csv")
    df.to_csv(out_path, index=False)
    print(f"Results saved to {out_path}")


if __name__ == "__main__":
    main()
