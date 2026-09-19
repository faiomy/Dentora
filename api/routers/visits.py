# -*- coding: utf-8 -*-
"""موارد زيارات المتابعة الخاصة بكل مريض."""

from fastapi import APIRouter, Depends

import database as db
from api.config import API_PREFIX
from api.security import require_scopes
from api.schemas import VisitCreate, VisitUpdate
from api.services import patient_or_404, visit_or_404

router = APIRouter(prefix=API_PREFIX, tags=["visits"])


@router.get("/patients/{patient_id}/visits")
def list_visits(patient_id: int, _key: dict = Depends(require_scopes("visits.read"))):
    patient_or_404(patient_id)
    return {"data": db.get_visits(patient_id), "meta": {}}


@router.post("/patients/{patient_id}/visits")
def create_visit(patient_id: int, body: VisitCreate,
                 _key: dict = Depends(require_scopes("visits.write"))):
    patient_or_404(patient_id)
    visit_id = db.add_visit(
        patient_id=patient_id,
        notes=body.notes,
        visit_date=body.visit_date,
        doctor_name=body.doctor_name,
    )
    return {"data": db.get_visit(visit_id), "meta": {}}


@router.patch("/visits/{visit_id}")
def update_visit(visit_id: int, body: VisitUpdate,
                 _key: dict = Depends(require_scopes("visits.write"))):
    visit_or_404(visit_id)
    fields = body.model_dump(exclude_unset=True)
    if fields:
        db.update_visit_fields(visit_id, **fields)
    return {"data": db.get_visit(visit_id), "meta": {}}


@router.delete("/visits/{visit_id}")
def delete_visit(visit_id: int, _key: dict = Depends(require_scopes("visits.delete"))):
    visit_or_404(visit_id)
    db.delete_visit(visit_id)
    return {"data": {"id": visit_id, "deleted": True}, "meta": {}}