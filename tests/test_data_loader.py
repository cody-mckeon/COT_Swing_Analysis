import os
import pandas as pd
from cot_fetcher.fetch import fetch_cot_snapshot


def test_fetch_cot_snapshot():
    # Run with known snapshot date
    df = fetch_cot_snapshot("2024-04-23", open_interest_threshold=200_000)

    # Basic validation
    assert not df.empty, "Returned DataFrame is empty"
    assert 'contract_code' in df.columns, "Missing 'contract_code' column"
    assert df['open_interest'].min() > 200_000, "Found contract with open interest below threshold"

    # Check a known high-liquidity contract
    known_code = "023391"  # Natural Gas Henry LD1 Fixed Price
    assert known_code in df['contract_code'].values, f"Expected contract {known_code} not found"

    # Persist to CSV for modeling
    out_path = "data/high_liquidity_snapshot_2024-04-23.csv"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"✅ Saved: {out_path}")
