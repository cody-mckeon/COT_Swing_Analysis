import joblib
import pandas as pd

def load_model(model_path: str):
    return joblib.load(model_path)

def predict(model, features: pd.DataFrame):
    return model.predict_proba(features)[:,1]
