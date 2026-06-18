from fastapi import APIRouter, HTTPException
from app.repositories import exam_repository
from app.models import Exam, ExamCreate, ExamUpdate
router = APIRouter(tags=["exams"])


@router.get("/patients/{patient_id}/exams", response_model=list[Exam])
def list_exams(patient_id: int):
    return exam_repository.list_by_patient(patient_id)


@router.get("/exams/{exam_id}", response_model=Exam)
def get_exam(exam_id: int):
    exam = exam_repository.get_by_id(exam_id)
    if not exam:
        raise HTTPException(404, "Exam not found")
    return exam


@router.post("/patients/{patient_id}/exams", response_model=Exam, status_code=201)
def create_exam(patient_id: int, payload: ExamCreate):
    return exam_repository.create(patient_id, payload.model_dump())


@router.patch("/exams/{exam_id}", response_model=Exam)
def update_exam(exam_id: int, payload: ExamUpdate):
    exam = exam_repository.update(exam_id, payload.model_dump(exclude_unset=True))
    if not exam:
        raise HTTPException(404, "Exam not found")
    return exam
