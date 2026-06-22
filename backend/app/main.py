from pathlib import Path
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from app.classification.classifier import load_model
from app.classification.pipeline import predict_candidates
from app import db_client
from app.segmentation import Segmenter, PatientManager
BASE_DIR = Path(__file__).parent
PKL_PATH = BASE_DIR / "classification" / "modele_xgb.pkl"

model = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    if PKL_PATH.exists():
        model = load_model(str(PKL_PATH))
        print("Model loaded")
    else:
        print("No model found, /analyse unavailable")
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/hello")
async def get_hello():
    return "hello world!"

@app.post("/analyze/{exam_id}")
def analyze(exam_id: int):
    if model is None:
        raise HTTPException(503, "Model not loaded")

    exam = db_client.get_exam(exam_id)   # lève une erreur HTTP si absent

    patient_path = Path(exam.dicom_path)
    if not patient_path.exists():
        raise HTTPException(status_code=404, detail=f"No such patient directory at {patient_path}")

    # Segmentation
    patient = PatientManager()
    patient.init(patient_path)
    seg = Segmenter(patient)
    seg.run()

    # Classification
    results = predict_candidates(seg.candidates, model)

    persisted = db_client.persist_analysis(
        exam_id=exam_id,
        algorithm="xgboost",
        results=results,
    )

    return persisted
