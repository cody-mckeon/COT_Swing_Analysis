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
    python -m src.models.train_model \
       --features data/processed/features_gc.csv \
       --model models/model_gc.joblib
   # repeat for crude oil with the CL price file and market filter
    python -m src.data.merge_cot_price \
        --cot data/processed/cot_crude.csv \
        --price data/prices/cl_daily.csv \
        --out data/processed/merged_crude.csv \
        --market "CRUDE OIL"
    python -m src.features.build_features \
        --merged data/processed/merged_crude.csv \
        --out data/processed/features_cl.csv
    python -m src.models.train_model \
        --features data/processed/features_cl.csv \
        --model models/model_cl.joblib

   dvc repro -f

   ```
4. Reproduce the entire pipeline with DVC
   ```bash
   dvc repro -f
   ```
5. Serve predictions
   ```bash
   uvicorn src.api.app:app --reload
   ```
