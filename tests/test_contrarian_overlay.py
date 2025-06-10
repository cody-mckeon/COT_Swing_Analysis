import pandas as pd
import joblib
from pathlib import Path
from src.eval.backtest import run_backtest


class DummyModel:
    def fit(self, X, y):
        pass

    def predict(self, X):
        return [1] * len(X)


def test_contrarian_overlay(tmp_path):
    df = pd.DataFrame({
        "week": pd.date_range("2024-01-02", periods=4, freq="W-TUE"),
        "etf_close": [100, 101, 102, 103],
        "mm_net_pct_oi": [0.1, 0.2, 0.9, 0.3],
        "target_dir": [1, 1, 1, 1],
    })
    p90 = df["mm_net_pct_oi"].quantile(0.90)
    df["extreme_spec_long"] = (df["mm_net_pct_oi"] >= p90).astype(int)

    features_path = tmp_path / "features.csv"
    df.to_csv(features_path, index=False)

    model_path = tmp_path / "model.pkl"
    joblib.dump(DummyModel(), model_path)

    result = run_backtest(
        str(features_path),
        str(model_path),
        str(df.week.iloc[1].date()),
    )

    # first row not extreme -> signal stays 1
    # second row extreme -> signal flipped to -1
    assert list(result["signal"]) == [1, -1]
    assert result["strategy_ret"].iloc[0] > 0
    assert result["strategy_ret"].iloc[1] < 0
