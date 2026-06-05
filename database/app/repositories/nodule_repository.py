import json
from app.db import get_cursor


def list_by_segmentation(segmentation_id: int):
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM nodules WHERE segmentation_id = %s",
            (segmentation_id,),
        )
        return cur.fetchall()


def get_by_id(nodule_id: int):
    with get_cursor() as cur:
        cur.execute("SELECT * FROM nodules WHERE id = %s", (nodule_id,))
        return cur.fetchone()


def create(segmentation_id: int, data: dict):
    data["segmentation_id"] = segmentation_id
    if data.get("features") is not None:
        data["features"] = json.dumps(data["features"])
    with get_cursor() as cur:
        cur.execute(
            """INSERT INTO nodules
               (segmentation_id, centroid_x, centroid_y, centroid_z,
                volume_mm3, max_diameter_mm, tnm_category, features)
               VALUES
               (%(segmentation_id)s, %(centroid_x)s, %(centroid_y)s, %(centroid_z)s,
                %(volume_mm3)s, %(max_diameter_mm)s, %(tnm_category)s, %(features)s)
               RETURNING *""",
            data,
        )
        return cur.fetchone()


def delete(nodule_id: int):
    with get_cursor() as cur:
        cur.execute(
            "DELETE FROM nodules WHERE id = %s RETURNING id", (nodule_id,)
        )
        return cur.fetchone()
