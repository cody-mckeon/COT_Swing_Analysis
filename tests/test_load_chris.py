import pandas as pd
from src.data.load_chris import fetch_weekly_chris


def test_fetch_weekly_chris(tmp_path, monkeypatch):
    def dummy_get(*args, **kwargs):
        idx = pd.date_range('2024-01-05', periods=3, freq='W-FRI')
        return pd.DataFrame({'Settle': [1, 2, 3]}, index=idx)

    monkeypatch.setattr('nasdaqdatalink.get', dummy_get)
    out_path = tmp_path / "out.csv"
    df = fetch_weekly_chris("CHRIS/CME_GC1", start_date="2024-01-01", save_path=str(out_path))
    assert not df.empty
    assert set(df.columns) == {"close"}
    assert out_path.exists()
