import pandas as pd
from src.data.load_price import fetch_daily_history, resample_to_weekly


def test_fetch_and_resample(monkeypatch):
    # dummy yfinance download returning 5 days of data
    def dummy_download(*args, **kwargs):
        idx = pd.date_range('2024-01-01', periods=5, freq='D')
        return pd.DataFrame({'Close': range(5)}, index=idx)

    monkeypatch.setattr('yfinance.download', dummy_download)
    df_daily = fetch_daily_history('GC=F', start='2024-01-01', end='2024-01-06', max_retries=3, retry_delay=0)
    assert not df_daily.empty
    weekly = resample_to_weekly(df_daily)
    assert not weekly.empty
    assert weekly.index.freq is not None
