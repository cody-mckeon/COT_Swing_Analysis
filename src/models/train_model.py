import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
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
    X = df[["mm_net_pct_oi", "pm_net_pct_oi", "sd_net_pct_oi"]]
    y = (df["return"] > 0).astype(int)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", RandomForestClassifier(n_estimators=100, random_state=42))
    ])
    pipe.fit(X_train, y_train)
    preds = pipe.predict(X_test)
    acc = accuracy_score(y_test, preds)
    joblib.dump(pipe, model_out)
    logger.info(f"Saved model to {model_out} | accuracy={acc:.3f}")
    return acc

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Train model on features CSV")
    parser.add_argument("--features", default="data/processed/features.csv")
    parser.add_argument("--model", default="models/gold_crude_model.joblib")
    args = parser.parse_args()
    train(args.features, args.model)
