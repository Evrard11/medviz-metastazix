from fastapi import APIRouter
from app.models import Nodule, NoduleCreate
from app.repositories import nodule_repository

router = APIRouter(tags=["nodules"])


@router.get("/segmentations/{segmentation_id}/nodules", response_model=list[Nodule])
def list_nodules(segmentation_id: int):
    return nodule_repository.list_by_segmentation(segmentation_id)


@router.post("/segmentations/{segmentation_id}/nodules", response_model=Nodule, status_code=201)
def create_nodule(segmentation_id: int, payload: NoduleCreate):
    return nodule_repository.create(segmentation_id, payload.model_dump())
