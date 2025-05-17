# src/cot_fetcher.py
import nasdaqdatalink
import pandas as pd
import logging
from typing import List, Tuple

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def get_active_liquid_contracts(date: str = '2024-04-23', oi_threshold: int = 200_000) -> pd.DataFrame:
    df = nasdaqdatalink.get_table("QDL/FON", date=date)
    """
    Fetches COT data and filters for contracts with:
    - Non-zero key trader activity
    - Open interest above threshold
    """
    logger.info(f"Fetching COT data for {date}")
    df = nasdaqdatalink.get_table("QDL/FON", date=date)
    
    key_traders = [
        'money_manager_longs', 'money_manager_shorts',
        'swap_dealer_longs', 'swap_dealer_shorts',
        'producer_merchant_processor_user_longs', 'producer_merchant_processor_user_shorts'
    ]

    grouped = df.groupby('contract_code')[key_traders].sum()
    active_contract = grouped[grouped.abs().sum(axis=1) > 0].index
    
    df['open_interest'] = df['total_reportable_longs'] + df['non_reportable_longs']
    liquid_df = df[df['contract_code'].isin(valid_codes)]
    liquid_df = liquid_df[liquid_df['open_interest'] > oi_threshold]

    summary = liquid_df.groupby('contract_code')['open_interest'].sum().sort_values(ascending=False)
    return summary.reset_index()

