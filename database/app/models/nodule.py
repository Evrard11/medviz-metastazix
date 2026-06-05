from pydantic import BaseModel
from datetime import datetime
from typing import Any


class NoduleBase(BaseModel):
    centroid_x: float | None = None
    centroid_y: float | None = None
    centroid_z: float | None = None
    volume_mm3: float | None = None
    max_diameter_mm: float | None = None
    tnm_category: str | None = None
    features: dict[str, Any] | None = None


class NoduleCreate(NoduleBase):
    pass


class Nodule(NoduleBase):
    id: int
    segmentation_id: int
    created_at: datetime
