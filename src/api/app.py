from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd
from ..models.predict_model import load_model, predict

app = FastAPI()
model = load_model("models/gold_crude_model.joblib")

class Features(BaseModel):
    mm_net_pct_oi: float
    pm_net_pct_oi: float
    sd_net_pct_oi: float

@app.post("/predict")
def predict_endpoint(feat: Features):
    df = pd.DataFrame([feat.dict()])
    prob = float(predict(model, df))
    return {"probability_up": prob}
