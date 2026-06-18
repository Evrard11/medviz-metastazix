import os
import pathlib
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from app.classification.classifier import load_model
from app.classification.pipeline import predict_candidates
from app import db_client
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

@app.post("/analyze/{exam_id}")
def analyze(exam_id: int, data: dict):
    if model is None:
        raise HTTPException(503, "Model not loaded")

    exam = db_client.get_exam(exam_id)   # lève une erreur HTTP si absent

    results = predict_candidates(data["candidates"], model)

    persisted = db_client.persist_analysis(
        exam_id=exam_id,
        algorithm="xgboost",
        results=results,
    )

    return persisted
