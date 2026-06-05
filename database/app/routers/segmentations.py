from fastapi import APIRouter, HTTPException
from app.models import Segmentation, SegmentationCreate
from app.repositories import segmentation_repository

router = APIRouter(tags=["segmentations"])


@router.get("/exams/{exam_id}/segmentations", response_model=list[Segmentation])
def list_segmentations(exam_id: int):
    return segmentation_repository.list_by_exam(exam_id)


@router.get("/segmentations/{segmentation_id}", response_model=Segmentation)
def get_segmentation(segmentation_id: int):
    seg = segmentation_repository.get_by_id(segmentation_id)
    if not seg:
        raise HTTPException(404, "Segmentation not found")
    return seg


@router.post("/exams/{exam_id}/segmentations", response_model=Segmentation, status_code=201)
def create_segmentation(exam_id: int, payload: SegmentationCreate):
    return segmentation_repository.create(exam_id, payload.model_dump())
