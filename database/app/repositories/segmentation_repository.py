import json
from app.db import get_cursor


def list_by_exam(exam_id: int):
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM segmentations WHERE exam_id = %s ORDER BY created_at DESC",
            (exam_id,),
        )
        return cur.fetchall()


def get_by_id(segmentation_id: int):
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM segmentations WHERE id = %s", (segmentation_id,)
        )
        return cur.fetchone()


def create(exam_id: int, data: dict):
    data["exam_id"] = exam_id
    if data.get("parameters") is not None:
        data["parameters"] = json.dumps(data["parameters"])
    with get_cursor() as cur:
        cur.execute(
            """INSERT INTO segmentations
               (exam_id, algorithm, algorithm_version, parameters, mask_path, nodule_count, is_validated)
               VALUES
               (%(exam_id)s, %(algorithm)s, %(algorithm_version)s, %(parameters)s,
                %(mask_path)s, %(nodule_count)s, %(is_validated)s)
               RETURNING *""",
            data,
        )
        return cur.fetchone()


def update(segmentation_id: int, data: dict):
    if not data:
        return get_by_id(segmentation_id)
    fields = ", ".join(f"{k} = %({k})s" for k in data)
    data["id"] = segmentation_id
    with get_cursor() as cur:
        cur.execute(
            f"UPDATE segmentations SET {fields} WHERE id = %(id)s RETURNING *",
            data,
        )
        return cur.fetchone()


def delete(segmentation_id: int):
    with get_cursor() as cur:
        cur.execute(
            "DELETE FROM segmentations WHERE id = %s RETURNING id",
            (segmentation_id,),
        )
        return cur.fetchone()
