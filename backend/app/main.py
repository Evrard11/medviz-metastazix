import os
import pathlib
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from app.classification.classifier import load_model
from app.classification.pipeline import predict_candidates

BASE_DIR = pathlib.Path(__file__).parent
PKL_PATH = BASE_DIR / "classification" / "modele_xgb.pkl"

model = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    if PKL_PATH.exists():
        model = load_model(str(PKL_PATH))
        print("Model loaded")
    else:
        print("No model found, /predict unavailable")
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/hello")
async def get_hello():
    return "hello world!"

@app.post("/predict")
def predict(data: dict):
    if model is None:
        raise HTTPException(503, "Model not loaded")
    return predict_candidates(data["candidates"], model)