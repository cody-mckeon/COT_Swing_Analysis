import pandas as pd
from src.features.build_features import build_features

def test_build_features(tmp_path):
    merged = pd.DataFrame({
        'week': pd.date_range('2024-01-05', periods=5, freq='W-FRI'),
        'mm_long': [10,11,12,13,14],
        'mm_short': [5,4,6,5,7],
        'pm_long': [8,9,7,6,7],
        'pm_short': [3,2,4,3,2],
        'sd_long': [6,7,8,7,8],
        'sd_short': [2,3,1,2,3],
        'open_interest': [100]*5,
        'etf_close': [50,51,52,53,54]
    })
    merged_path = tmp_path / 'merged.csv'
    merged.to_csv(merged_path, index=False)
    features_path = tmp_path / 'features.csv'
    df = build_features(str(merged_path), str(features_path))
    assert not df.empty
    assert {'mm_net_pct_oi', 'return'}.issubset(df.columns)
    assert features_path.exists()
