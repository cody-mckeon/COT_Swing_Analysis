# src/cot_fetcher/fetch.py
import nasdaqdatalink
import pandas as pd
from .logging_config import setup_logger
from .constants import KEY_TRADER_COLUMNS

logger = setup_logger(__name__)

def fetch_cot_snapshot(date: str = '2024-04-23', open_interest_threshold: int = 200_000) -> pd.DataFrame:
    logger.info(f"Fetching COT data for {date}")
    df = nasdaqdatalink.get_table("QDL/FON", date=date)

    grouped = df.groupby('contract_code')[KEY_TRADER_COLUMNS].sum()
    active_contracts = grouped[grouped.abs().sum(axis=1) > 0].index

    df['open_interest'] = df['total_reportable_longs'] + df['non_reportable_longs']
    liquid_df = df[df['contract_code'].isin(active_contracts)]
    liquid_df = liquid_df[liquid_df['open_interest'] > open_interest_threshold]

    summary = liquid_df.groupby('contract_code')['open_interest'].sum().sort_values(ascending=False)
    return summary.reset_index()
