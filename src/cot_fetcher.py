# src/cot_fetcher.py
import nasdaqdatalink
import pandas as pd

def get_active_liquid_contracts(date: str = '2024-04-23', oi_threshold: int = 200_000):
    df = nasdaqdatalink.get_table("QDL/FON", date=date)
    trader_cols = [
        'money_manager_longs', 'money_manager_shorts',
        'swap_dealer_longs', 'swap_dealer_shorts',
        'producer_merchant_processor_user_longs', 'producer_merchant_processor_user_shorts'
    ]

    active = df.groupby('contract_code')[trader_cols].sum()
    valid_codes = active[active.abs().sum(axis=1) > 0].index
    df['open_interest'] = df['total_reportable_longs'] + df['non_reportable_longs']
    
    liquid_df = df[df['contract_code'].isin(valid_codes)]
    liquid_df = liquid_df[liquid_df['open_interest'] > oi_threshold]

    summary = liquid_df.groupby('contract_code')['open_interest'].sum().sort_values(ascending=False)
    return summary.reset_index()

