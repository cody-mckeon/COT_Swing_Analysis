import pandas as pd
import pytest
from src.data.merge_cot_price import merge_cot_with_price


@pytest.mark.parametrize("ticker", ["MGC=F", "MCL=F"])
def test_merge(ticker, tmp_path):
    cot = pd.DataFrame({
        'report_date': pd.date_range('2024-01-05', periods=3, freq='W-FRI'),
        'open_interest': [100, 120, 110],
        'mm_long': [10,11,12],
        'mm_short': [5,4,6],
        'pm_long': [8,7,9],
        'pm_short': [3,2,4],
        'sd_long': [6,5,7],
        'sd_short': [2,3,1]
    })
    price = pd.DataFrame({
        'week': pd.date_range('2024-01-05', periods=3, freq='W-FRI'),
        'etf_close': [50,51,52]
    })
    cot_path = tmp_path / 'cot.csv'
    price_path = tmp_path / f"price_{ticker.replace('=', '_')}.csv"
    out_path = tmp_path / 'out.csv'
    cot.to_csv(cot_path, index=False)
    price.to_csv(price_path, index=False)
    merged = merge_cot_with_price(str(cot_path), str(price_path), str(out_path))
    assert not merged.empty
    assert 'etf_close' in merged.columns
    assert out_path.exists()
