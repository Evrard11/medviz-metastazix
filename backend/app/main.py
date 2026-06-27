import os
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from app.classification.classifier import load_model
from app.classification.pipeline import predict_candidates
from app import db_client

import sys
import pathlib

sys.path.append(str(pathlib.Path(__file__).parent.parent))

from pydantic import BaseModel
from app.segmentation.patient_manager import PatientManager
from app.segmentation.segmenter import Segmenter
import numpy as np

BASE_DIR = pathlib.Path(__file__).parent
PKL_FP_REDUCER = BASE_DIR / "classification" / "model_fp_reducer.pkl"
PKL_MALIGNANCY = BASE_DIR / "classification" / "model_classifier.pkl"

fp_reducer_model = None
malignancy_model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global fp_reducer_model, malignancy_model
    missing = [p for p in (PKL_FP_REDUCER, PKL_MALIGNANCY) if not p.exists()]
    if missing:
        print(f"Model(s) not found: {missing}")
        exit(1)
    fp_reducer_model = load_model(str(PKL_FP_REDUCER))
    malignancy_model = load_model(str(PKL_MALIGNANCY))
    print("Models loaded (fp_reducer + malignancy classifier)")
    yield


app = FastAPI(lifespan=lifespan)


class ProcessDicomRequest(BaseModel):
    patient_id: str


@app.post("/process_dicom")
def process_dicom(req: ProcessDicomRequest):
    print("Processing dicom")
    if fp_reducer_model is None or malignancy_model is None:
        raise HTTPException(503, "Models not loaded")

    STORAGE_DIR = os.environ.get("STORAGE_PATH", "/storage")
    if not os.path.exists(STORAGE_DIR):
        # Fallback to local relative path
        STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage"))

    patient_path = os.path.join(STORAGE_DIR, "uploads", req.patient_id)

    if os.path.exists(patient_path):
        print("Patient path exists")
    else:
        print("Patient path does not exist")
        raise HTTPException(404, "Patient path does not exist")

    # Initialize PatientManager
    patient = PatientManager()
    patient.init(patient_path)

    # Segment
    seg = Segmenter(patient)
    candidates = seg.run()

    print(f"{len(candidates)} candidates found after segmentation")

    # Classify
    classification_results = predict_candidates(candidates, fp_reducer_model, malignancy_model, seg.nodules_mask)
    print(f"{len(classification_results)} candidates found after classification")

    # Get volume to render
    volume = patient.volume
    if volume is None:
        return {"error": "Volume not loaded"}

    # Downsample volume 4x (performance, payload size)
    step_z, step_y, step_x = 2, 4, 4
    small_vol = volume[::step_z, ::step_y, ::step_x]

    # Normalize HU to 0-255 (performance, payload size)
    small_vol = np.clip(small_vol, -1000, 400).astype(np.float32)
    small_vol = ((small_vol + 1000) / 1400.0 * 255).astype(np.uint8)

    # ZYX => XYZ
    dims = [small_vol.shape[2], small_vol.shape[1], small_vol.shape[0]]

    # Spacing
    dx = patient.voxel_size[0] * step_x
    dy = patient.voxel_size[1] * step_y
    if len(patient.voxel_size) > 2:
        dz = patient.voxel_size[2] * step_z
    else:
        dz = 1.0 * step_z

    response_candidates = []
    for res in classification_results:
        cz, cy, cx = res['centroid']
        z1, y1, x1, z2, y2, x2 = res["bbox"]
        response_candidates.append({
            "centroid": [float(cx), float(cy), float(cz)],
            "score": float(res["malignancy_score"]),
            "bbox": [
                z1 / step_z, y1 / step_y, x1 / step_x,
                z2 / step_z, y2 / step_y, x2 / step_x,
            ]
        })

    return {
        "volume": small_vol.flatten().tolist(),
        "dimensions": dims,
        "spacing": [dx, dy, dz],
        "anomalies": response_candidates
    }