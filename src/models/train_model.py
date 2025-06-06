import pandas as pd
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
import joblib
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
if not logger.handlers:
    logger.addHandler(handler)

def train(features_csv: str, model_out: str) -> float:
    df = pd.read_csv(features_csv)
    feature_cols = [
        "mm_net_pct_oi",
        "pm_net_pct_oi",
        "sd_net_pct_oi",
        "mm_net_pct_oi_chg_1w",
        "pm_net_pct_oi_chg_1w",
        "sd_net_pct_oi_chg_1w",
        "vol_26w",
        "rsi_14",
        "ema_13",
        "macd_hist",
    ]

    X = df[feature_cols]
    y = (df["return_1w"] > 0).astype(int)

    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=1000))
    ])

    tscv = TimeSeriesSplit(n_splits=5)
    scores = cross_val_score(pipe, X, y, cv=tscv, scoring="accuracy")

    pipe.fit(X, y)
    joblib.dump(pipe, model_out)
    logger.info(
        f"Saved model to {model_out} | cv_accuracy={scores.mean():.3f}"
    )
    return scores.mean()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Train model on features CSV")
    parser.add_argument("--features", default="data/processed/features.csv")
    parser.add_argument("--model", default="models/gold_crude_model.joblib")
    args = parser.parse_args()
    train(args.features, args.model)
