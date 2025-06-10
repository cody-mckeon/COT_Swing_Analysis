import pandas as pd
import subprocess
from sklearn.ensemble import RandomForestClassifier
import joblib
from pathlib import Path


def test_rolling_eval(tmp_path):
    # build small features dataset
    periods = 10
    df = pd.DataFrame({
        'week': pd.date_range('2024-01-02', periods=periods, freq='W-TUE'),
        'feature1': range(periods),
        'target_dir': [0, 1] * (periods // 2) + ([0] if periods % 2 else []),
        'etf_close': 100 + pd.Series(range(periods))
    })
    features_path = tmp_path / 'features.csv'
    df.to_csv(features_path, index=False)

    model = RandomForestClassifier(n_estimators=5, random_state=42)
    model_path = tmp_path / 'model.pkl'
    joblib.dump(model, model_path)

    reports_dir = Path('reports')
    if reports_dir.exists():
        for f in reports_dir.iterdir():
            f.unlink()
    else:
        reports_dir.mkdir()

    result = subprocess.run([
        'python', 'scripts/rolling_eval.py',
        '--features', str(features_path),
        '--model', str(model_path),
        '--start', str(df.week.iloc[0].date()),
        '--end', str(df.week.iloc[-2].date()),
        '--freq', '2W',
        '--commission', '0.0'
    ], capture_output=True, text=True)

    out_path = Path('reports/rolling_backtest_gc.csv')
    assert out_path.exists(), result.stderr
    out_df = pd.read_csv(out_path)
    assert not out_df.empty
