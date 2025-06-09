import pandas as pd
from src.data.build_classification_features import build_classification_features


def test_build_classification_features(tmp_path):
    df = pd.DataFrame({
        'return_1w': [0.05, -0.02, 0.1],
        'other': [1, 2, 3]
    })
    in_path = tmp_path / 'features.csv'
    df.to_csv(in_path, index=False)
    out_path = tmp_path / 'class.csv'
    result = build_classification_features(str(in_path), str(out_path), th=0.0)
    assert 'target_dir' in result.columns
    assert set(result['target_dir'].unique()) <= {0, 1}
    assert out_path.exists()
