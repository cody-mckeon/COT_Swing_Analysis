import pandas as pd
from src.data.load_price import fetch_weekly_close

class DummyDf(pd.DataFrame):
    @property
    def empty(self):
        return False

def test_fetch_weekly_close(tmp_path, monkeypatch):
    def dummy_download(*args, **kwargs):
        idx = pd.date_range('2024-01-01', periods=5, freq='D')
        return pd.DataFrame({'Close': [1,2,3,4,5]}, index=idx)
    monkeypatch.setattr('yfinance.download', dummy_download)
    df = fetch_weekly_close("MGC=F", start_date="2024-01-01", save_dir=str(tmp_path))
    assert not df.empty
    assert set(df.columns) == {"week", "etf_close"}
    csv_path = tmp_path / "MGC_F.csv"
    assert csv_path.exists()
