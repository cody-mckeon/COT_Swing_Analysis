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
       --out data/processed/class_features_gc.csv
    python -m src.models.train_model \
       --features data/processed/features_gc.csv \
       --model models/model_gc.joblib
   # or run the classification pipeline and save the best estimator
    python -m src.models.train_classifier \
        --features data/processed/class_features_gc.csv \
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
        --out data/processed/class_features_cl.csv
    python -m src.models.train_model \
        --features data/processed/features_cl.csv \
        --model models/model_cl.joblib
   # classification pipeline for crude oil
    python -m src.models.train_classifier \
        --features data/processed/class_features_cl.csv \
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
  --features "/content/drive/MyDrive/Colab Notebooks/COT_Trading_System/src/data/processed/features_gc_clf.csv" \
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
  --features "/content/drive/MyDrive/Colab Notebooks/COT_Trading_System/src/data/processed/features_clf.csv" \
  --model    "src/models/best_model_cl.pkl" \
  --test-start 2023-01-01 \
  --commission 0.0005 \
 --allow-shorts
```

Swap in your Crude feature file (`features_clf.csv`) and model
(`best_model_cl.pkl`). The `--test-start` date can be earlier or later (e.g.
`2022-07-01` to backtest the last 18 months). Commission stays at `0.0005`
unless you want to model tighter or wider spreads. Include `--allow-shorts` if you wish to open short positions.
