# COT_Swing_Analysis

This repo demonstrates a minimal pipeline for analyzing CFTC Commitments of Traders (COT) data alongside micro-futures prices.

## Directory Structure
```
COT_Swing_Analysis/
├── data/
│   ├── raw/               # yearly COT Excel files
│   ├── processed/         # cleaned datasets and features
│   └── prices/            # price data downloaded from Nasdaq Data Link
├── src/
│   ├── data/              # dataset utilities
│   ├── features/          # feature engineering
│   ├── models/            # training and inference
│   └── api/               # FastAPI microservice
└── tests/                 # pytest tests
```

## Quickstart
1. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```
2. Build the dataset, split by market and fetch micro-futures prices:
   ```bash
   python data/make_dataset.py --raw-dir data/raw --out-csv data/processed/cot_disagg_futures_2016_2025.csv
   python -m src.data.split_cot --in-csv data/processed/cot_disagg_futures_gold_crude_2016_2025.csv \
       --gold data/processed/cot_gold.csv --crude data/processed/cot_crude.csv
   # download crude and gold futures prices from Yahoo Finance
   python -m src.data.load_price
   ```
3. Reproduce the entire pipeline with DVC
   ```bash
   # example for gold
    python -m src.data.merge_cot_price \
        --cot data/processed/cot_gold.csv \
        --price data/prices/gc_daily.csv \
        --out data/processed/merged_gold.csv \
        --market "GOLD"
    python -m src.features.build_features \
       --merged data/processed/merged_gold.csv \
       --out data/processed/features_gc.csv
    python -m src.data.build_classification_features \
       --in data/processed/features_gc.csv \
       --out data/processed/class_features_gc_extreme.csv
    python -m src.models.train_model \
       --features data/processed/features_gc.csv \
       --model models/model_gc.joblib
   # or run the classification pipeline and save the best estimator
    python -m src.models.train_classifier \
        --features data/processed/class_features_gc_extreme.csv \
        --model-out models/best_model_gc.pkl
   # repeat for crude oil with the CL price file and market filter
    python -m src.data.merge_cot_price \
        --cot data/processed/cot_crude.csv \
        --price data/prices/cl_daily.csv \
        --out data/processed/merged_crude.csv \
        --market "CRUDE OIL"
    python -m src.features.build_features \
        --merged data/processed/merged_crude.csv \
        --out data/processed/features_cl.csv
    python -m src.data.build_classification_features \
        --in data/processed/features_cl.csv \
        --out data/processed/class_features_cl_extreme.csv
    python -m src.models.train_model \
        --features data/processed/features_cl.csv \
        --model models/model_cl.joblib
   # classification pipeline for crude oil
    python -m src.models.train_classifier \
        --features data/processed/class_features_cl_extreme.csv \
        --model-out models/best_model_cl.pkl

   dvc repro -f

   ```
   Running the steps manually does not modify `dvc.lock`. After your manual
   execution, either:

   1. Run `dvc commit` (or `dvc commit <stage>`/`dvc commit <output>`) to record
      the new output hashes, or
   2. Invoke `dvc repro` as shown in the README to have DVC refresh the stage
      hashes for you.

   This ensures DVC tracks the updated artifacts even when you execute the
   underlying commands yourself.

4. Reproduce the entire pipeline with DVC
   ```bash
   dvc repro -f
   ```
5. Serve predictions
   ```bash
    uvicorn src.api.app:app --reload
    ```

## Core Feature Set

The feature builder creates a small set of weekly signals used for modeling:

- `mm_net_pct_oi`, `sd_net_pct_oi`, `pm_net_pct_oi` – each group’s net position
  divided by open interest so bullish/bearish exposure is comparable week to
  week.
- `mm_net_pct_oi_chg_1w`, `sd_net_pct_oi_chg_1w`, `pm_net_pct_oi_chg_1w` –
  one‑week changes in those ratios. Sharp swings in speculative positioning often
  precede price rotations.
- `return_1w` – next week’s percentage change in close. This serves as the
  modeling target.
- `vol_26w` – 26‑week rolling volatility of log returns to capture regime
  shifts.
- `rsi_14` – short‑term momentum oscillator.
- `ema_13` – 13‑week exponential moving average of the close.
- `macd_hist` – MACD line minus signal line, highlighting momentum
  acceleration.

These seven provide a compact mix of COT positioning and basic technical
context. Once a simple cross‑validated model (e.g. logistic regression or a tiny
random forest) is fit, you can inspect feature importances and iteratively prune
or expand the set.

## Running the Backtest

After training your classifiers, use `scripts/run_eval.py` to evaluate holdout
performance and generate a simple trading backtest.

### Gold Backtest

```bash
python scripts/run_eval.py \
  --features "/content/drive/MyDrive/Colab Notebooks/COT_Trading_System/src/data/processed/class_features_gc_extreme.csv" \
  --model    "src/models/best_model_gc.pkl" \
  --test-start 2023-01-01 \
  --commission 0.0005 \
  --allow-shorts
```

- `--features`: the classification‑ready feature file for Gold (must include
  `target_dir`).
- `--model`: the RandomForest you saved as `best_model_gc.pkl`.
- `--test-start`: first date of the hold‑out period (e.g. `2023-01-01`).
- `--commission`: round‑trip cost per trade (`0.0005` = `0.05%`).
- `--allow-shorts`: enable taking short trades when the model predicts a down move.

### Crude Backtest

```bash
python scripts/run_eval.py \
  --features "/content/drive/MyDrive/Colab Notebooks/COT_Trading_System/src/data/processed/class_features_cl_extreme.csv" \
  --model    "src/models/best_model_cl.pkl" \
  --test-start 2023-01-01 \
  --commission 0.0005 \
 --allow-shorts
```

Swap in your Crude feature file (`class_features_cl_extreme.csv`) and model
(`best_model_cl.pkl`). The `--test-start` date can be earlier or later (e.g.
`2022-07-01` to backtest the last 18 months). Commission stays at `0.0005`
unless you want to model tighter or wider spreads. Include `--allow-shorts` if you wish to open short positions.

### Rolling Window Backtests

To gauge robustness over time, run the rolling evaluation script. It retrains at
multiple start dates and summarizes returns, Sharpe ratios and drawdowns.

```bash
python scripts/rolling_eval.py \
  --features data/processed/class_features_gc_extreme.csv \
  --model    src/models/best_model_gc.pkl \
  --start    2017-01-01 \
  --end      2024-01-01 \
  --freq     6M \
  --commission 0.0005 \
  --thresholds 0.85,0.90,0.95
```

Results are written to `reports/rolling_thresholds_gc.csv`.

## Contrarian Overlay

When money managers' net-OI exceeds the 90th percentile, we invert the model's LONG
signal to SHORT, to fade the speculator crowd.


### NOTES

Add a regime flag (e.g. vol_26w > threshold) and train separate models for high- vs low-vol regimes.

Adjust rolling frequency

Try 3-month windows instead of 6-month to see more granular shifts.

Or longer (annual) windows to smooth out noise.

Add risk filters

In the low-CAGR 2023 regime, perhaps filter out weeks when VIX > X or range_pct_w < Y.

Ensemble old & new

Combine predictions from models trained on different eras (2017–2020 vs 2020–2023) weighted by recent performance.

Threshold Sensitivity

Try the 85th or 95th percentile instead of 90th and re-plot the rolling CAGR to see if you can eke out a bit more performance or smoother equity (fewer false-positives).

Apply to Crude

Repeat the exact same overlay logic on your crude dataset so you can compare Gold vs. Crude robustness under the same contrarian rule.

Combine with Vol Filter

Add a flag for vol_26w > X (say X = its 75th percentile) and only apply the contrarian flip when volatility is “normal” (to avoid fading during flash crashes).

Drawdown Analysis

Compute max drawdown in each rolling window and check if the overlay also reduced drawdowns in 2023 (it should).

Productionize Your Data Pipeline
Weekly COT Ingestion

Schedule a job (cron / GitHub Action / Cloud Scheduler) each Friday after 5 pm ET to:
• Pull new COT tables via Nasdaq Data Link or direct download
• Run make_dataset.py → update cot_disagg_futures…csv in your DVC-tracked data store

Daily Price Update

Likewise schedule a daily job to:
• Fetch yesterday’s close for GC (or GLD) and CL (or USO) via yfinance or a broker API
• Append to prices/*.csv

scripts/weekly_etl.py is meant for either a Colab or CI/Docker environment and requires several environment variables. At the top of the script it states:

# This script is intended to run in GitHub Actions or a Docker container.
# Ensure `GDRIVE_SA_KEY`, `RAW_DATA_FOLDER_ID` and `RAW_DATA_DIR` are set.

The script detects the COLAB_ENV variable to decide whether to mount Google Drive:

IS_COLAB = os.getenv("COLAB_ENV") == "1"
if IS_COLAB:
    RAW_DIR = Path("/content/drive/MyDrive/COT_Swing_Analysis/src/data/raw")
else:
    RAW_DIR = Path(os.getenv("RAW_DATA_DIR", "src/data/raw"))

Its main entry point expects the folder ID and credentials:

def main() -> None:
    folder_id = os.getenv("RAW_DATA_FOLDER_ID")
    if not folder_id:
        logging.error({"error": "RAW_DATA_FOLDER_ID not set"})
        sys.exit(1)

    service = build_drive_service()
    exit_code = download_folder(service, folder_id, RAW_DIR)
    sys.exit(exit_code)

To run it:

Install dependencies from requirements.txt (pip install -r requirements.txt).

Export the following environment variables:

GDRIVE_SA_KEY – the service‑account JSON contents.

RAW_DATA_FOLDER_ID – the Google Drive folder ID containing your raw files.

RAW_DATA_DIR – local destination directory (defaults to src/data/raw).

Optional COLAB_ENV=1 when running in Colab; otherwise omit.

Execute the script:

python scripts/weekly_etl.py
The script will authenticate with Google Drive using the service account, download all files from the specified folder, and place them in RAW_DATA_DIR. It logs progress and exits with a non‑zero code if a problem occurs.

Feature Engineering Orchestrator

Chain the two above so that once price + COT are updated, you re‐run your build_classification_features.py (with the 95% threshold) to produce today’s feature row.
