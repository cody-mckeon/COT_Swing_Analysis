"""Download weekly continuous futures from Nasdaq Data Link CHRIS.

This helper is deprecated because Nasdaq Data Link often fails or
times out. Prefer :mod:`src.data.load_price` which pulls prices from
Yahoo Finance instead.
"""

import os
import logging
import pandas as pd
import nasdaqdatalink

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
if not logger.handlers:
    logger.addHandler(handler)


def fetch_weekly_chris(
    dataset_code: str,
    start_date: str = "2016-01-01",
    api_key: str = None,
    save_path: str = None
) -> pd.DataFrame:
    """Download weekly continuous futures from Nasdaq Data Link CHRIS."""
    if api_key:
        nasdaqdatalink.ApiConfig.api_key = api_key

    logger.info(f"Fetching CHRIS data for {dataset_code} since {start_date}")
    try:
        raw = nasdaqdatalink.get(
            dataset_code,
            start_date=start_date,
            collapse="weekly",
            order="asc",
        )
    except Exception as e:
        logger.error(f"Failed to fetch {dataset_code}: {e}")
        return None

    df = raw.to_frame() if hasattr(raw, "to_frame") else raw.copy()

    if "Settle" in df.columns:
        df = df[["Settle"]].rename(columns={"Settle": "close"})
    elif "Last" in df.columns:
        df = df[["Last"]].rename(columns={"Last": "close"})
    else:
        logger.warning(
            f"No 'Settle' or 'Last' column found for {dataset_code}. Returning all columns."
        )

    df.index = pd.to_datetime(df.index)
    df.index.name = "date"

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        df.to_csv(save_path)
        logger.info(f"Saved weekly CHRIS closes to {save_path}")

    return df
