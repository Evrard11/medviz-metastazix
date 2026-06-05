from app.db import get_cursor


def list_by_patient(patient_id: int):
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM exams WHERE patient_id = %s ORDER BY date_exam DESC",
            (patient_id,),
        )
        return cur.fetchall()


def get_by_id(exam_id: int):
    with get_cursor() as cur:
        cur.execute("SELECT * FROM exams WHERE id = %s", (exam_id,))
        return cur.fetchone()


def create(patient_id: int, data: dict):
    data["patient_id"] = patient_id
    with get_cursor() as cur:
        cur.execute(
            """INSERT INTO exams
               (patient_id, dicom_path, date_exam, modality, slice_thickness, num_slices, notes, status)
               VALUES
               (%(patient_id)s, %(dicom_path)s, %(date_exam)s, %(modality)s,
                %(slice_thickness)s, %(num_slices)s, %(notes)s, %(status)s)
               RETURNING *""",
            data,
        )
        return cur.fetchone()


def update(exam_id: int, data: dict):
    if not data:
        return get_by_id(exam_id)
    fields = ", ".join(f"{k} = %({k})s" for k in data)
    data["id"] = exam_id
    with get_cursor() as cur:
        cur.execute(
            f"UPDATE exams SET {fields} WHERE id = %(id)s RETURNING *", data
        )
        return cur.fetchone()


def delete(exam_id: int):
    with get_cursor() as cur:
        cur.execute("DELETE FROM exams WHERE id = %s RETURNING id", (exam_id,))
        return cur.fetchone()
