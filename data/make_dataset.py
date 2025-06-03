# src/data/make_dataset.py

import os
import glob
import pandas as pd

def load_one_year(path_to_excel: str) -> pd.DataFrame:
    """
    Load one “Disaggregated Futures Only” COT Excel sheet into a DataFrame.
    We detect the header row by finding "Market_and_Exchange_Names",
    read from there, filter for FutOnly_or_Combined == "F", and
    keep only the columns needed for downstream processing.
    """
    # 1) Read the raw file without headers to find where the real header is.
    raw = pd.read_excel(path_to_excel, header=None, dtype=str)
    print("Raw columns from Excel:\n", raw.columns.tolist())

    header_row_idx = None
    for idx, row in raw.iterrows():
        if "Market_and_Exchange_Names" in row.values:
            header_row_idx = idx
            break

    if header_row_idx is None:
        raise ValueError(f"Could not locate header row in {path_to_excel!r}")

    # 2) Re‐read with the proper header.
    df = pd.read_excel(path_to_excel, header=header_row_idx, dtype=str)
    print("Parsed header columns:\n", df.columns.tolist())


    # 3) Standardize column‐names: strip whitespace, replace spaces with underscores
    df.columns = [
        col.strip().lower().replace(" ", "_")
        for col in df.columns
    ]

    # 4) Filter only “futures only” rows (the sheet includes Combined and Futures-Only).
    #    The column is called `futonly_or_combined` after cleaning.
    if "futonly_or_combined" not in df.columns:
        raise KeyError(f"'FutOnly_or_Combined' column not found in {path_to_excel!r}")
    df = df[df["futonly_or_combined"].str.strip().str.lower() == "futonly"].copy()

    # 5) Convert numeric columns to proper dtype
    numeric_cols = [
        "open_interest_all",
        "prod_merc_positions_long_all", "prod_merc_positions_short_all",
        "swap_positions_long_all", "swap__positions_short_all", "swap__positions_spread_all",
        "m_money_positions_long_all", "m_money_positions_short_all", "m_money_positions_spread_all",
        "other_rept_positions_long_all", "other_rept_positions_short_all", "other_rept_positions_spread_all",
        "tot_rept_positions_long_all", "tot_rept_positions_short_all",
        "nonrept_positions_long_all", "nonrept_positions_short_all",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 6) Parse the report date. In your sheet, it’s "report_date_as_mm_dd_yyyy"
    # Look for report_date_as_mm_dd_yyyy regardless of casing
    report_date_col = [col for col in df.columns if col.lower() == "report_date_as_mm_dd_yyyy"]
    if report_date_col:
        print(f"\n📆 Values in '{report_date_col[0]}' column:")
        print(df[report_date_col[0]].head(10))
        df["report_date"] = df["report_date_as_mm_dd_yyyy"]
    else:
        raise KeyError(f"No 'Report_Date_as_MM_DD_YYYY' column in {path_to_excel!r}")


    # 7) Rename contract code to a simpler name
    if "cftc_contract_market_code" in df.columns:
        df["contract_code"] = df["cftc_contract_market_code"].astype(str)
    else:
        raise KeyError(f"No 'CFTC_Contract_Market_Code' in {path_to_excel!r}")

    # 8) Keep only the columns we care about, and rename them to a consistent schema:
    #    – report_date
    #    – contract_code
    #    – type (we already filtered for “Futures Only”—but we keep it if needed)
    #    – open_interest_all  (i.e. total open interest)
    #    – m_money_positions_long_all / short_all  (Money Managers)
    #    – swap_positions_long_all / short_all
    #    – prod_merc_positions_long_all / short_all
    #    – tot_rept_positions_long_all / short_all
    #    – nonrept_positions_long_all / short_all
    #
    #    If a column is missing, we simply drop it; but by 2025’s schema, they all exist.

    keep_cols_map = {
        "market_and_exchange_names": "market_name",
        "report_date": "report_date",
        "contract_code": "contract_code",
        "open_interest_all": "open_interest",
        "m_money_positions_long_all": "mm_long",
        "m_money_positions_short_all": "mm_short",
        "swap_positions_long_all": "sd_long",
        "swap__positions_short_all": "sd_short",
        "prod_merc_positions_long_all": "pm_long",
        "prod_merc_positions_short_all": "pm_short",
        "tot_rept_positions_long_all": "tot_long",
        "tot_rept_positions_short_all": "tot_short",
        "nonrept_positions_long_all": "nrep_long",
        "nonrept_positions_short_all": "nrep_short",
    }

    # Build the subset DataFrame
    subset = {}
    for original_col, new_col in keep_cols_map.items():
        if original_col in df.columns:
            subset[new_col] = df[original_col].copy()
        else:
            # Column not found—skip it but warn
            print(f"⚠️  Warning: '{original_col}' not found in {os.path.basename(path_to_excel)}")
            subset[new_col] = pd.NA

    out = pd.DataFrame(subset)

    print("Renamed columns:\n", df.columns.tolist())
    # Let's try printing the first few rows to see what values are in the 'futonly_or_combined'-like column
    futonly_candidates = [col for col in df.columns if "futonly" in col]
    print("FutOnly-related columns:", futonly_candidates)
    for col in futonly_candidates:
        print(f"\nFirst 5 values in column '{col}':\n", df[col].head())


    # 9) Add net‐position columns for each key trader group:
    #     mm_net = mm_long – mm_short
    #     sd_net = sd_long – sd_short
    #     pm_net = pm_long – pm_short
    out["mm_net"] = out["mm_long"] - out["mm_short"]
    out["sd_net"] = out["sd_long"] - out["sd_short"]
    out["pm_net"] = out["pm_long"] - out["pm_short"]

    # 10) Tag “year” so you can see it later if needed
    basename = os.path.basename(path_to_excel)
    # Expecting a filename like "cot_2016.xlsx" → split & parse “2016”
    year_str = basename.replace("cot_", "").split(".")[0]
    try:
        out["year"] = int(year_str)
    except ValueError:
        out["year"] = pd.NA

    return out


def build_full_dataset(raw_dir: str, processed_csv: str):
    """
    For every file matching “cot_*.xls*” in raw_dir,
    load it via load_one_year(), concatenate them,
    and write one large CSV to 'processed_csv'.
    """
    all_files = sorted(glob.glob(os.path.join(raw_dir, "cot_*.xls*")))
    if not all_files:
        raise FileNotFoundError(f"No files found in {raw_dir!r} (looking for cot_*.xls or cot_*.xlsx)")

    pieces = []
    for path in all_files:
        print(f"→ Loading {os.path.basename(path)} …")
        try:
            one = load_one_year(path)
            pieces.append(one)
        except Exception as e:
            print(f"❌ Error loading {path}: {e}")
            continue

    # Concatenate them all
    big = pd.concat(pieces, ignore_index=True)
    big = big.sort_values(["report_date", "contract_code"]).reset_index(drop=True)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(processed_csv), exist_ok=True)
    big.to_csv(processed_csv, index=False)
    print(f"✅ Wrote consolidated CSV to {processed_csv}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Build a consolidated COT dataset from yearly Disaggregated Futures Only Excel files."
    )
    parser.add_argument(
        "--raw-dir",
        type=str,
        default="data/raw",
        help="Directory containing yearly cot_YYYY.xls or cot_YYYY.xlsx files",
    )
    parser.add_argument(
        "--out-csv",
        type=str,
        default="data/processed/cot_disagg_futures_2016_2025.csv",
        help="Path where the consolidated CSV will be written",
    )
    args = parser.parse_args()

    build_full_dataset(raw_dir=args.raw_dir, processed_csv=args.out_csv)
