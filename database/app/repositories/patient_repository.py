from app.db import get_cursor


def list_all(limit: int = 100, offset: int = 0):
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM patients ORDER BY id LIMIT %s OFFSET %s",
            (limit, offset),
        )
        return cur.fetchall()


def get_by_id(patient_id: int):
    with get_cursor() as cur:
        cur.execute("SELECT * FROM patients WHERE id = %s", (patient_id,))
        return cur.fetchone()


def create(data: dict):
    with get_cursor() as cur:
        cur.execute(
            """INSERT INTO patients (anonymized_id, first_name, last_name, birthdate, sex)
               VALUES (%(anonymized_id)s, %(first_name)s, %(last_name)s, %(birthdate)s, %(sex)s)
               RETURNING *""",
            data,
        )
        return cur.fetchone()


def update(patient_id: int, data: dict):
    if not data:
        return get_by_id(patient_id)
    fields = ", ".join(f"{k} = %({k})s" for k in data)
    data["id"] = patient_id
    with get_cursor() as cur:
        cur.execute(
            f"UPDATE patients SET {fields} WHERE id = %(id)s RETURNING *", data
        )
        return cur.fetchone()


def delete(patient_id: int):
    with get_cursor() as cur:
        cur.execute(
            "DELETE FROM patients WHERE id = %s RETURNING id", (patient_id,)
        )
        return cur.fetchone()
