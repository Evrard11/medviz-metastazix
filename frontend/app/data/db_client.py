import os
import requests

DB_URL = os.environ.get("DATABASE_BACKEND_URL", "http://database-backend:8001")
TIMEOUT = 10


def get_patients():
    try:
        r = requests.get(f"{DB_URL}/patients", timeout=TIMEOUT)
        r.raise_for_status()
        patients = r.json()
        return [
            {
                "id": p["id"],                          # id numérique (pour les appels API)
                "anonymized_id": p["anonymized_id"],    # identifiant affiché
                "name": f"{p.get('last_name','')}, {p.get('first_name','')}",
                "age": p.get("birthdate", "N/A"),
                "date": p.get("created_at", "")[:10],
            }
            for p in patients
        ]
    except Exception as e:
        print(f"[db_client] erreur get_patients: {e}")
        return []


def get_exams(patient_id):
    try:
        r = requests.get(f"{DB_URL}/patients/{patient_id}/exams", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[db_client] erreur get_exams: {e}")
        return []


def get_segmentations(exam_id):
    try:
        r = requests.get(f"{DB_URL}/exams/{exam_id}/segmentations", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[db_client] erreur get_segmentations: {e}")
        return []


def get_nodules(segmentation_id):
    try:
        r = requests.get(f"{DB_URL}/segmentations/{segmentation_id}/nodules", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[db_client] erreur get_nodules: {e}")
        return []


def get_patient_nodules(patient_id):
    """
    Helper : récupère tous les nodules d'un patient en descendant
    exams → segmentations → nodules. Renvoie une liste adaptée pour anomaly_card.
    """
    nodules_out = []
    exams = get_exams(patient_id)
    for exam in exams:
        segs = get_segmentations(exam["id"])
        for seg in segs:
            nodules = get_nodules(seg["id"])
            for n in nodules:
                score = n.get("malignancy_score")
                nodules_out.append({
                    "id": f"N{n['id']}",
                    "slice": int(n["centroid_z"]) if n.get("centroid_z") is not None else "N/A",
                    "loc": f"({n.get('centroid_x','?')}, {n.get('centroid_y','?')}, {n.get('centroid_z','?')})",
                    "size": f"{n.get('volume_mm3','N/A')} mm³" if n.get("volume_mm3") else "N/A",
                    "note": f"Malignité: {score}" if score is not None else f"Algo: {seg['algorithm']} (non scoré)",
                })
    return nodules_out
