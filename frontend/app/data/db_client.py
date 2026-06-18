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
                "id": p["anonymized_id"],
                "name": f"{p.get('last_name','')}, {p.get('first_name','')}",
                "age": p.get("birthdate", "N/A"),
                "date": p.get("created_at", "")[:10],
            }
            for p in patients
        ]
    except Exception as e:
        print(f"[db_client] erreur: {e}")
        return []
