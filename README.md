# COT_Swing_Analysis

This repo demonstrates a minimal pipeline for analyzing CFTC Commitments of Traders (COT) data alongside micro-futures prices.

## Directory Structure
```
COT_Swing_Analysis/
├── data/
│   ├── raw/               # yearly COT Excel files
│   ├── processed/         # cleaned datasets and features
│   └── prices/            # price data downloaded from yfinance
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

2. Build the dataset and fetch micro-futures prices:
   ```bash
   python data/make_dataset.py --raw-dir data/raw --out-csv data/processed/cot_disagg_futures_2016_2025.csv
   # micro gold and micro crude oil
   python -m src.data.load_price MGC=F
   python -m src.data.load_price MCL=F
   ```
3. Merge, build features and train a model
   ```bash
   # example for gold
   python -m src.data.merge_cot_price \
       --cot data/processed/cot_disagg_futures_2016_2025.csv \
       --price data/prices/MGC_F.csv \
       --out data/processed/merged_gold.csv
   python -m src.features.build_features \
       --merged data/processed/merged_gold.csv \
       --out data/processed/features_gold.csv
   # repeat for crude oil if desired
   python -m src.models.train_model --features data/processed/features_gold.csv --model models/gold_crude_model.joblib
=======


   ```
4. Serve predictions
   ```bash
   uvicorn src.api.app:app --reload
   ```
