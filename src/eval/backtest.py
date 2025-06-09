import argparse
from pathlib import Path
from typing import Optional

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score


def _load_split(features_csv: str, test_start_date: str):
    df = pd.read_csv(features_csv, parse_dates=["week"])
    df = df.sort_values("week").reset_index(drop=True)
    test_start = pd.to_datetime(test_start_date)
    train_df = df[df.week < test_start]
    test_df = df[df.week >= test_start].reset_index(drop=True)
    return train_df, test_df


def _prep_X(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(
        columns=["target_dir", "contract_code", "week", "report_date"],
        errors="ignore",
    )


def holdout_validation(features_csv: str, model_path: str, test_start_date: str) -> None:
    train_df, test_df = _load_split(features_csv, test_start_date)
    model = joblib.load(model_path)

    X_train = _prep_X(train_df)
    y_train = train_df["target_dir"]
    model.fit(X_train, y_train)

    X_test = _prep_X(test_df)
    y_test = test_df["target_dir"]
    preds = model.predict(X_test)

    metrics = {
        "accuracy": accuracy_score(y_test, preds),
        "precision": precision_score(y_test, preds, zero_division=0),
        "recall": recall_score(y_test, preds, zero_division=0),
        "f1": f1_score(y_test, preds, zero_division=0),
    }

    table = pd.DataFrame([metrics])
    print(table.to_string(index=False))


def run_backtest(
    features_csv: str,
    model_path: str,
    test_start_date: str,
    commission_per_trade: float = 0.0005,
) -> pd.DataFrame:
    train_df, test_df = _load_split(features_csv, test_start_date)
    model = joblib.load(model_path)

    X_train = _prep_X(train_df)
    y_train = train_df["target_dir"]
    model.fit(X_train, y_train)

    X_test = _prep_X(test_df)
    signals = model.predict(X_test)

    df_bt = test_df.copy()
    df_bt["signal"] = signals
    df_bt["entry_price"] = df_bt["etf_close"]
    df_bt["exit_price"] = df_bt["etf_close"].shift(-1)
    df_bt["raw_ret"] = (df_bt["exit_price"] - df_bt["entry_price"]) / df_bt["entry_price"]
    df_bt["strategy_ret"] = df_bt["raw_ret"] * df_bt["signal"] - 2 * commission_per_trade

    ret_series = df_bt["strategy_ret"].dropna()
    cum_return = (1 + ret_series).cumprod()
    df_bt.loc[ret_series.index, "cum_return"] = cum_return

    if not cum_return.empty:
        peak = cum_return.cummax()
        drawdown = (peak - cum_return) / peak
        max_drawdown = drawdown.max()
        sharpe = ret_series.mean() / ret_series.std() * (52 ** 0.5) if ret_series.std() else 0.0
        downside = ret_series[ret_series < 0]
        sortino = (
            ret_series.mean() / downside.std() * (52 ** 0.5)
            if downside.std()
            else 0.0
        )
    else:
        max_drawdown = 0.0
        sharpe = 0.0
        sortino = 0.0

    print(
        f"Cumulative Return: {cum_return.iloc[-1] if not cum_return.empty else 1:.4f} "
        f"MaxDD: {max_drawdown:.4f} Sharpe: {sharpe:.4f} Sortino: {sortino:.4f}"
    )

    return df_bt[["week", "entry_price", "exit_price", "signal", "strategy_ret", "cum_return"]].dropna()


def main(argv: Optional[list] = None) -> None:
    parser = argparse.ArgumentParser(description="Backtesting utilities")
    subparsers = parser.add_subparsers(dest="command")

    holdout_p = subparsers.add_parser("holdout")
    holdout_p.add_argument("features_csv")
    holdout_p.add_argument("model")
    holdout_p.add_argument("test_start")

    backtest_p = subparsers.add_parser("backtest")
    backtest_p.add_argument("features_csv")
    backtest_p.add_argument("model")
    backtest_p.add_argument("test_start")
    backtest_p.add_argument("--commission", type=float, default=0.0005)

    args = parser.parse_args(argv)

    if args.command == "holdout":
        holdout_validation(args.features_csv, args.model, args.test_start)
    elif args.command == "backtest":
        df = run_backtest(
            args.features_csv,
            args.model,
            args.test_start,
            commission_per_trade=args.commission,
        )
        Path("reports").mkdir(exist_ok=True)
        out_path = Path("reports/backtest_results.csv")
        df.to_csv(out_path, index=False)
        print(f"Results saved to {out_path}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
