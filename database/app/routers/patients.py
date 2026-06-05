from fastapi import APIRouter, HTTPException
from app.models import Patient, PatientCreate
from app.repositories import patient_repository

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=list[Patient])
def list_patients(limit: int = 100, offset: int = 0):
    return patient_repository.list_all(limit, offset)


@router.get("/{patient_id}", response_model=Patient)
def get_patient(patient_id: int):
    patient = patient_repository.get_by_id(patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")
    return patient


@router.post("", response_model=Patient, status_code=201)
def create_patient(payload: PatientCreate):
    return patient_repository.create(payload.model_dump())
