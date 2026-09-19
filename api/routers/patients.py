# -*- coding: utf-8 -*-
"""موارد المرضى: قائمة + إنشاء + قراءة + تعديل + حذف."""

from fastapi import APIRouter, Depends, Query

import database as db
from api.config import API_PREFIX
from api.security import require_scopes
from api.schemas import PatientCreate, PatientUpdate
from api.services import paginate, patient_or_404

router = APIRouter(prefix=API_PREFIX + "/patients", tags=["patients"])


@router.get("")
def list_patients(
    search: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    _key: dict = Depends(require_scopes("patients.read")),
):
    items, meta = paginate(db.get_all_patients(search), page, page_size)
    return {"data": items, "meta": meta}


@router.post("")
def create_patient(
    body: PatientCreate,
    _key: dict = Depends(require_scopes("patients.write")),
):
    patient_id = db.add_patient(
        full_name=body.full_name,
        phone=body.phone or "",
        birth_date=body.birth_date or "",
        gender=body.gender or "",
        address=body.address or "",
        medical_notes=body.medical_notes or "",
        allergies=body.allergies or "",
        occupation=body.occupation or "",
        family_id=body.family_id or "",
        nationality=body.nationality or "",
    )
    return {"data": db.get_patient(patient_id), "meta": {}}


@router.get("/{patient_id}")
def get_patient(patient_id: int, _key: dict = Depends(require_scopes("patients.read"))):
    return {"data": patient_or_404(patient_id), "meta": {}}


@router.patch("/{patient_id}")
def update_patient(
    patient_id: int,
    body: PatientUpdate,
    _key: dict = Depends(require_scopes("patients.write")),
):
    patient_or_404(patient_id)
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        return {"data": db.get_patient(patient_id), "meta": {}}
    db.update_patient(patient_id, **fields)
    return {"data": db.get_patient(patient_id), "meta": {}}


@router.delete("/{patient_id}")
def delete_patient(patient_id: int, _key: dict = Depends(require_scopes("patients.delete"))):
    patient_or_404(patient_id)
    db.delete_patient(patient_id)
    return {"data": {"id": patient_id, "deleted": True}, "meta": {}}