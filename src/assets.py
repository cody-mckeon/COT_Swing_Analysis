# src/assets.py

def enrich_assets_with_yf_symbols(assets_dict):
    for k, v in assets_dict.items():
        ticker = v.get("micro_ticker") or v.get("ticker")
        if ticker:
            v["yf_symbol"] = f"{ticker}=F"
    return assets_dict

