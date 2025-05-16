# src/asset_mapper.py
def merge_contract_names(summary_df: pd.DataFrame, path_to_excel: str) -> pd.DataFrame:
    df_strikes = pd.read_excel(path_to_excel)[['ContractName', 'ContractMarketCode']].dropna()
    df_strikes = df_strikes.drop_duplicates()
    return summary_df.merge(df_strikes, left_on='contract_code', right_on='ContractMarketCode', how='left')

