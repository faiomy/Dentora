# -*- coding: utf-8 -*-
"""موارد خريطة الأسنان (Odontogram): القراءة الكاملة + تعديل سن واحد +
إضافة ملحوظة مفصّلة + تسجيل معالجة بتحصيل مالي."""

from datetime import datetime

from fastapi import APIRouter, Depends

import database as db
from api.config import API_PREFIX
from api.security import require_scopes
from api.schemas import (OdontogramAnnotationUpdate, OdontogramToothUpdate,
                         TreatmentCreate)
from api.services import add_treatment_with_charge, build_odontogram, patient_or_404

router = APIRouter(prefix=API_PREFIX + "/patients", tags=["odontogram"])


@router.get("/{patient_id}/odontogram")
def get_odontogram(patient_id: int, _key: dict = Depends(require_scopes("odontogram.read"))):
    patient_or_404(patient_id)
    return {"data": build_odontogram(patient_id), "meta": {}}


@router.patch("/{patient_id}/odontogram/tooth/{tooth_number}")
def update_tooth(patient_id: int, tooth_number: int, body: OdontogramToothUpdate,
                 _key: dict = Depends(require_scopes("odontogram.write"))):
    patient_or_404(patient_id)
    if body.status is not None:
        # بتمسح أي ملحوظة مفصّلة قديمة للسن لأن الحالة الجديدة اتحددت فعليًا
        db.set_tooth_presence(patient_id, tooth_number, body.status)
    if body.notes is not None:
        db.set_tooth_note(patient_id, tooth_number, body.notes)
    return {"data": build_odontogram(patient_id), "meta": {}}


@router.put("/{patient_id}/odontogram/annotation/{tooth_number}")
def upsert_annotation(patient_id: int, tooth_number: int, body: OdontogramAnnotationUpdate,
                      _key: dict = Depends(require_scopes("odontogram.write"))):
    patient_or_404(patient_id)
    db.upsert_tooth_annotation(
        patient_id=patient_id,
        tooth_number=tooth_number,
        note_date=body.note_date or datetime.now().strftime("%Y-%m-%d"),
        doctor_name=body.doctor_name or "",
        note_text=body.note_text,
    )
    return {"data": build_odontogram(patient_id), "meta": {}}


@router.delete("/{patient_id}/odontogram/annotation/{tooth_number}")
def delete_annotation(patient_id: int, tooth_number: int,
                      _key: dict = Depends(require_scopes("odontogram.write"))):
    patient_or_404(patient_id)
    db.delete_tooth_annotation(patient_id, tooth_number)
    return {"data": {"tooth_number": tooth_number, "deleted": True}, "meta": {}}


@router.post("/{patient_id}/odontogram/treatments")
def create_treatment(patient_id: int, body: TreatmentCreate,
                     _key: dict = Depends(require_scopes("odontogram.write"))):
    patient_or_404(patient_id)
    record_id, label = add_treatment_with_charge(
        patient_id=patient_id,
        tooth_number=body.tooth_number,
        treatment_key=body.treatment_key,
        price=body.price,
        notes=body.notes or "",
        doctor_name=body.doctor_name or "",
    )
    rec = db.get_treatment_record(record_id)
    return {"data": {"record": rec, "label": label}, "meta": {}}