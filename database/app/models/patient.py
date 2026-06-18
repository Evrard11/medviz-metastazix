from pydantic import BaseModel
from datetime import date, datetime
from typing import Literal


class PatientBase(BaseModel):
    anonymized_id: str
    first_name: str | None = None
    last_name: str | None = None
    birthdate: date | None = None
    sex: Literal["M", "F", "O", "U"] | None = None


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    birthdate: date | None = None
    sex: Literal["M", "F", "O", "U"] | None = None


class Patient(PatientBase):
    id: int
    created_at: datetime
