import os
import requests

DB_URL = os.environ.get("DATABASE_BACKEND_URL", "http://database-backend:8001")
TIMEOUT = 10
def get_patient(patient_id: int) -> dict:
    r = requests.get(f"{DB_URL}/patients/{patient_id}", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def get_exam(exam_id: int) -> dict:
    r = requests.get(f"{DB_URL}/exams/{exam_id}", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def list_exams(patient_id: int) -> list[dict]:
    r = requests.get(f"{DB_URL}/patients/{patient_id}/exams", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def create_segmentation(exam_id: int, algorithm: str, **kwargs) -> dict:
    payload = {"algorithm": algorithm, **kwargs}
    r = requests.post(
        f"{DB_URL}/exams/{exam_id}/segmentations", json=payload, timeout=TIMEOUT
    )
    r.raise_for_status()
    return r.json()


def save_nodules(segmentation_id: int, results: list[dict]) -> list[dict]:
    saved = []
    for res in results:
        cz, cy, cx = res["centroid"]
        payload = {
            "centroid_z": float(cz),
            "centroid_y": float(cy),
            "centroid_x": float(cx),
            "malignancy_score": res.get("malignancy_score"),
        }
        r = requests.post(
            f"{DB_URL}/segmentations/{segmentation_id}/nodules",
            json=payload,
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        saved.append(r.json())
    return saved


def update_exam_status(exam_id: int, status: str) -> dict:
    r = requests.patch(
        f"{DB_URL}/exams/{exam_id}", json={"status": status}, timeout=TIMEOUT
    )
    r.raise_for_status()
    return r.json()



def persist_analysis(exam_id: int, algorithm: str, results: list[dict],
                     mask_path: str | None = None, parameters: dict | None = None) -> dict:
    seg = create_segmentation(
        exam_id,
        algorithm=algorithm,
        parameters=parameters,
        mask_path=mask_path,
        nodule_count=len(results),
    )
    nodules = save_nodules(seg["id"], results)
    update_exam_status(exam_id, "segmented")
    return {"segmentation": seg, "nodules": nodules}
