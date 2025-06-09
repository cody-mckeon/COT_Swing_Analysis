import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from src.eval.backtest import run_backtest


def test_run_backtest(tmp_path):
    df = pd.DataFrame({
        'week': pd.date_range('2024-01-02', periods=4, freq='W-TUE'),
        'feature1': [1, 2, 3, 4],
        'target_dir': [1, 0, 1, 0],
        'etf_close': [100, 101, 102, 103]
    })
    csv_path = tmp_path / 'features.csv'
    df.to_csv(csv_path, index=False)

    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model_path = tmp_path / 'model.pkl'
    joblib.dump(model, model_path)

    result = run_backtest(str(csv_path), str(model_path), str(df.week.iloc[2].date()))
    assert result.shape[1] == 6
    assert not result.isna().any().any()

