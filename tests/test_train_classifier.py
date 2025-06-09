import pandas as pd
import subprocess
from src.features.build_features import build_features


def test_train_classifier(tmp_path):
    periods = 60
    merged = pd.DataFrame({
        'week': pd.date_range('2024-01-05', periods=periods, freq='W-FRI'),
        'mm_long': range(10, 10 + periods),
        'mm_short': range(5, 5 + periods),
        'pm_long': range(8, 8 + periods),
        'pm_short': range(3, 3 + periods),
        'sd_long': range(6, 6 + periods),
        'sd_short': range(2, 2 + periods),
        'open_interest': [100] * periods,
        'etf_close': [50 + (-1)**i * i for i in range(periods)]
    })
    merged_path = tmp_path / 'merged.csv'
    merged.to_csv(merged_path, index=False)

    features_path = tmp_path / 'features.csv'
    df = build_features(str(merged_path), str(features_path))
    df['target_dir'] = (df['return_1w'] > 0).astype(int)
    df.to_csv(features_path, index=False)

    model_path = tmp_path / 'best_model.pkl'
    result = subprocess.run([
        'python', '-m', 'src.models.train_classifier',
        '--features', str(features_path),
        '--model-out', str(model_path)
    ], capture_output=True, text=True)

    assert model_path.exists()
    assert 'F1' in result.stdout

    model_path.unlink()
