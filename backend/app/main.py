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

import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent))

from pydantic import BaseModel
from segmentation.patient_manager import PatientManager
from segmentation.segmenter import Segmenter
from skimage.measure import marching_cubes
import numpy as np

class ProcessDicomRequest(BaseModel):
    patient_id: str

@app.post("/process_dicom")
def process_dicom(req: ProcessDicomRequest):
    import os
    STORAGE_DIR = os.environ.get("STORAGE_PATH", "/storage")
    if not os.path.exists(STORAGE_DIR):
        # Fallback to local relative path
        STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage"))
    
    patient_path = os.path.join(STORAGE_DIR, "uploads", req.patient_id)
    
    # 1. Initialize PatientManager
    patient = PatientManager(patient_path=patient_path)
    patient.init()
    
    # 2. Segment
    seg = Segmenter(patient)
    candidates = seg.run()
    
    # 3. Classify
    if model is not None:
        classification_results = predict_candidates(candidates, model)
    else:
        # Mock prediction if no model
        classification_results = []
        for c in candidates:
            c['malignancy_score'] = 0.99
            classification_results.append(c)
    
    # 4. Generate 3D Volume for rendering
    volume = patient.volume
    if volume is None:
        return {"error": "Volume not loaded"}
    
    # Downsample the volume by 4x in each dimension for performance and payload size
    step_z, step_y, step_x = 2, 4, 4
    small_vol = volume[::step_z, ::step_y, ::step_x]
    
    # Normalize HU to 0-255 for better transport
    small_vol = np.clip(small_vol, -1000, 400)
    small_vol = ((small_vol + 1000) / 1400.0 * 255).astype(np.uint8)
    
    # Dimensions: X, Y, Z
    dims = [small_vol.shape[2], small_vol.shape[1], small_vol.shape[0]]
    # Spacing: dx, dy, dz
    dx = patient.voxel_size[0] * step_x
    dy = patient.voxel_size[1] * step_y
    if len(patient.voxel_size) > 2:
        dz = patient.voxel_size[2] * step_z
    else:
        dz = 1.0 * step_z
        
    response_candidates = []
    for res in classification_results:
        cz, cy, cx = res['centroid']
        response_candidates.append({
            "centroid": [float(cx), float(cy), float(cz)],
            "score": float(res["malignancy_score"]),
            "bbox": res["bbox"]
        })

    return {
        "volume": small_vol.flatten().tolist(),
        "dimensions": dims,
        "spacing": [dx, dy, dz],
        "anomalies": response_candidates
    }
