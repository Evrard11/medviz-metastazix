"""

cd database && SELF_URL=http://localhost:8001 uv run python app/test_api.py

"""
import os
import uuid
import requests

API_URL = os.environ.get("SELF_URL", "http://localhost:8001")
TIMEOUT = 10


def _uid(prefix="TEST"):
    return f"{prefix}_{str(uuid.uuid4())[:8]}"


# ---------- Patients ----------

def test_health():
    r = requests.get(f"{API_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200, f"code {r.status_code}"
    assert r.json()["status"] == "ok", "status pas ok"
    print("OK test_health")


def test_create_patient():
    payload = {"anonymized_id": _uid(), "first_name": "Test", "last_name": "Patient", "sex": "M"}
    r = requests.post(f"{API_URL}/patients", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201, f"code {r.status_code}"
    data = r.json()
    assert "id" in data, "pas d'id"
    assert data["anonymized_id"] == payload["anonymized_id"], "anonymized_id différent"
    print(f"OK test_create_patient — id {data['id']}")


def test_create_patient_minimal():
    """Patient avec juste anonymized_id (cas LIDC anonymisé)."""
    r = requests.post(f"{API_URL}/patients", json={"anonymized_id": _uid("LIDC")}, timeout=TIMEOUT)
    assert r.status_code == 201, f"code {r.status_code}"
    assert r.json()["first_name"] is None, "first_name devrait être null"
    print("OK test_create_patient_minimal")


def test_get_patient():
    created = requests.post(f"{API_URL}/patients", json={"anonymized_id": _uid()}, timeout=TIMEOUT).json()
    r = requests.get(f"{API_URL}/patients/{created['id']}", timeout=TIMEOUT)
    assert r.status_code == 200, f"code {r.status_code}"
    assert r.json()["id"] == created["id"], "id différent"
    print("OK test_get_patient")


def test_get_patient_404():
    r = requests.get(f"{API_URL}/patients/999999", timeout=TIMEOUT)
    assert r.status_code == 404, f"devrait être 404, reçu {r.status_code}"
    print("OK test_get_patient_404")


def test_list_patients():
    r = requests.get(f"{API_URL}/patients", timeout=TIMEOUT)
    assert r.status_code == 200, f"code {r.status_code}"
    assert isinstance(r.json(), list), "devrait être une liste"
    print(f"OK test_list_patients — {len(r.json())} patients")


# ---------- Exams ----------

def test_create_exam():
    patient = requests.post(f"{API_URL}/patients", json={"anonymized_id": _uid()}, timeout=TIMEOUT).json()
    payload = {"dicom_path": "/storage/dicom/test/", "date_exam": "2026-01-15", "modality": "CT"}
    r = requests.post(f"{API_URL}/patients/{patient['id']}/exams", json=payload, timeout=TIMEOUT)
    assert r.status_code == 201, f"code {r.status_code}"
    data = r.json()
    assert data["patient_id"] == patient["id"], "patient_id incorrect"
    assert data["status"] == "uploaded", "status par défaut devrait être uploaded"
    print(f"OK test_create_exam — id {data['id']}")


def test_update_exam_status():
    patient = requests.post(f"{API_URL}/patients", json={"anonymized_id": _uid()}, timeout=TIMEOUT).json()
    exam = requests.post(f"{API_URL}/patients/{patient['id']}/exams",
                         json={"dicom_path": "/x/", "date_exam": "2026-01-15"}, timeout=TIMEOUT).json()
    r = requests.patch(f"{API_URL}/exams/{exam['id']}", json={"status": "segmented"}, timeout=TIMEOUT)
    assert r.status_code == 200, f"code {r.status_code}"
    assert r.json()["status"] == "segmented", "status pas mis à jour"
    print("OK test_update_exam_status")


def test_list_exams_by_patient():
    patient = requests.post(f"{API_URL}/patients", json={"anonymized_id": _uid()}, timeout=TIMEOUT).json()
    requests.post(f"{API_URL}/patients/{patient['id']}/exams",
                  json={"dicom_path": "/x/", "date_exam": "2026-01-15"}, timeout=TIMEOUT)
    r = requests.get(f"{API_URL}/patients/{patient['id']}/exams", timeout=TIMEOUT)
    assert r.status_code == 200, f"code {r.status_code}"
    assert len(r.json()) == 1, f"devrait avoir 1 exam, a {len(r.json())}"
    print("OK test_list_exams_by_patient")


# ---------- Segmentations & Nodules ----------

def test_create_segmentation_and_nodule():
    patient = requests.post(f"{API_URL}/patients", json={"anonymized_id": _uid()}, timeout=TIMEOUT).json()
    exam = requests.post(f"{API_URL}/patients/{patient['id']}/exams",
                         json={"dicom_path": "/x/", "date_exam": "2026-01-15"}, timeout=TIMEOUT).json()
    seg = requests.post(f"{API_URL}/exams/{exam['id']}/segmentations",
                        json={"algorithm": "kmeans", "parameters": {"k": 3}}, timeout=TIMEOUT)
    assert seg.status_code == 201, f"seg code {seg.status_code}"
    seg_id = seg.json()["id"]

    nod = requests.post(f"{API_URL}/segmentations/{seg_id}/nodules",
                        json={"centroid_x": 1.0, "centroid_y": 2.0, "centroid_z": 3.0,
                              "malignancy_score": 0.87, "tnm_category": "T1b"}, timeout=TIMEOUT)
    assert nod.status_code == 201, f"nodule code {nod.status_code}"
    assert nod.json()["malignancy_score"] == 0.87, "score incorrect"
    print("OK test_create_segmentation_and_nodule")


def test_nodule_null_score():
    """Nodule sans score (mode dégradé sans modèle ML)."""
    patient = requests.post(f"{API_URL}/patients", json={"anonymized_id": _uid()}, timeout=TIMEOUT).json()
    exam = requests.post(f"{API_URL}/patients/{patient['id']}/exams",
                         json={"dicom_path": "/x/", "date_exam": "2026-01-15"}, timeout=TIMEOUT).json()
    seg = requests.post(f"{API_URL}/exams/{exam['id']}/segmentations",
                        json={"algorithm": "kmeans"}, timeout=TIMEOUT).json()
    nod = requests.post(f"{API_URL}/segmentations/{seg['id']}/nodules",
                        json={"centroid_x": 1.0, "centroid_y": 2.0, "centroid_z": 3.0,
                              "malignancy_score": None}, timeout=TIMEOUT)
    assert nod.status_code == 201, f"code {nod.status_code}"
    assert nod.json()["malignancy_score"] is None, "score devrait être null"
    print("OK test_nodule_null_score")


def test_list_segmentations_and_nodules():
    patient = requests.post(f"{API_URL}/patients", json={"anonymized_id": _uid()}, timeout=TIMEOUT).json()
    exam = requests.post(f"{API_URL}/patients/{patient['id']}/exams",
                         json={"dicom_path": "/x/", "date_exam": "2026-01-15"}, timeout=TIMEOUT).json()
    seg = requests.post(f"{API_URL}/exams/{exam['id']}/segmentations",
                        json={"algorithm": "xgboost"}, timeout=TIMEOUT).json()
    requests.post(f"{API_URL}/segmentations/{seg['id']}/nodules",
                  json={"centroid_x": 1.0, "centroid_y": 2.0, "centroid_z": 3.0}, timeout=TIMEOUT)

    segs = requests.get(f"{API_URL}/exams/{exam['id']}/segmentations", timeout=TIMEOUT)
    assert segs.status_code == 200 and len(segs.json()) == 1, "liste segmentations incorrecte"
    nods = requests.get(f"{API_URL}/segmentations/{seg['id']}/nodules", timeout=TIMEOUT)
    assert nods.status_code == 200 and len(nods.json()) == 1, "liste nodules incorrecte"
    print("OK test_list_segmentations_and_nodules")


if __name__ == "__main__":
    tests = [
        test_health,
        test_create_patient,
        test_create_patient_minimal,
        test_get_patient,
        test_get_patient_404,
        test_list_patients,
        test_create_exam,
        test_update_exam_status,
        test_list_exams_by_patient,
        test_create_segmentation_and_nodule,
        test_nodule_null_score,
        test_list_segmentations_and_nodules,
    ]
    passed, failed = 0, 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"FAIL {t.__name__} — {e}")
            failed += 1
    print(f"\n{passed}/{passed + failed} tests API passés")
