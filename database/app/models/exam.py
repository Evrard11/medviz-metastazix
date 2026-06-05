from pydantic import BaseModel
from datetime import date, datetime
from enum import Enum


class ExamStatus(str, Enum):
    uploaded = "uploaded"
    processing = "processing"
    segmented = "segmented"
    validated = "validated"
    error = "error"


class ExamBase(BaseModel):
    dicom_path: str
    date_exam: date
    modality: str = "CT"
    slice_thickness: float | None = None
    num_slices: int | None = None
    notes: str | None = None
    status: ExamStatus = ExamStatus.uploaded


class ExamCreate(ExamBase):
    pass


class ExamUpdate(BaseModel):
    notes: str | None = None
    status: ExamStatus | None = None


class Exam(ExamBase):
    id: int
    patient_id: int
    created_at: datetime
