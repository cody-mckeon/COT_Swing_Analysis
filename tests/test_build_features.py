import pandas as pd
from src.features.build_features import build_features

def test_build_features(tmp_path):
    periods = 32
    merged = pd.DataFrame({
        'week': pd.date_range('2024-01-05', periods=periods, freq='W-FRI'),
        'mm_long': range(10, 10 + periods),
        'mm_short': range(5, 5 + periods),
        'pm_long': range(8, 8 + periods),
        'pm_short': range(3, 3 + periods),
        'sd_long': range(6, 6 + periods),
        'sd_short': range(2, 2 + periods),
        'open_interest': [100]*periods,
        'etf_close': range(50, 50 + periods)
    })
    merged_path = tmp_path / 'merged.csv'
    merged.to_csv(merged_path, index=False)
    features_path = tmp_path / 'features.csv'
    df = build_features(str(merged_path), str(features_path))
    assert not df.empty
    expected_cols = {
        'mm_net_pct_oi',
        'pm_net_pct_oi',
        'sd_net_pct_oi',
        'mm_net_pct_oi_chg_1w',
        'pm_net_pct_oi_chg_1w',
        'sd_net_pct_oi_chg_1w',
        'return_1w',
        'vol_26w',
        'rsi_14',
        'ema_13',
        'macd_hist'
    }
    assert expected_cols.issubset(df.columns)
    assert features_path.exists()
