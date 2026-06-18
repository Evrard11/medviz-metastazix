from pydantic import BaseModel
from datetime import datetime
from enum import Enum
from typing import Any


class AlgorithmName(str, Enum):
    kmeans = "kmeans"
    random_forest = "random_forest"
    xgboost = "xgboost"
    manual = "manual"


class SegmentationBase(BaseModel):
    algorithm: AlgorithmName
    algorithm_version: str | None = None
    parameters: dict[str, Any] | None = None
    mask_path: str | None = None
    nodule_count: int | None = None
    is_validated: bool = False


class SegmentationCreate(SegmentationBase):
    pass


class SegmentationUpdate(BaseModel):
    mask_path: str | None = None
    nodule_count: int | None = None
    is_validated: bool | None = None


class Segmentation(SegmentationBase):
    id: int
    exam_id: int
    created_at: datetime
