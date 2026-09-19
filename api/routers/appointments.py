# -*- coding: utf-8 -*-
"""موارد المواعيد: قائمة (بفلاتر) + إنشاء + قراءة + تعديل + إلغاء + حذف."""

from fastapi import APIRouter, Depends, Query

import database as db
from api.config import API_PREFIX
from api.security import require_scopes
from api.schemas import AppointmentCreate, AppointmentUpdate
from api.services import appointment_or_404 as appt_or_404, paginate

router = APIRouter(prefix=API_PREFIX + "/appointments", tags=["appointments"])


@router.get("")
def list_appointments(
    appt_date: str = "",
    patient_id: int | None = None,
    status: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    _key: dict = Depends(require_scopes("appointments.read")),
):
    rows = db.get_appointments(date_filter=appt_date or None)
    if patient_id is not None:
        rows = [r for r in rows if r.get("patient_id") == patient_id]
    if status:
        rows = [r for r in rows if r.get("status") == status]
    items, meta = paginate(rows, page, page_size)
    return {"data": items, "meta": meta}


@router.post("")
def create_appointment(
    body: AppointmentCreate,
    _key: dict = Depends(require_scopes("appointments.write")),
):
    from api.services import patient_or_404
    patient_or_404(body.patient_id)
    appt_id = db.add_appointment(
        patient_id=body.patient_id,
        appt_date=body.appt_date,
        appt_time=body.appt_time,
        doctor_name=body.doctor_name or "",
        status=body.status,
        notes=body.notes or "",
        duration_minutes=body.duration_minutes,
    )
    return {"data": db.get_appointment(appt_id), "meta": {}}


@router.get("/{appt_id}")
def get_appointment(appt_id: int, _key: dict = Depends(require_scopes("appointments.read"))):
    return {"data": appt_or_404(appt_id), "meta": {}}


@router.patch("/{appt_id}")
def update_appointment(
    appt_id: int,
    body: AppointmentUpdate,
    _key: dict = Depends(require_scopes("appointments.write")),
):
    current = appt_or_404(appt_id)
    fields = body.model_dump(exclude_unset=True)

    new_status = fields.pop("status", None)
    if new_status and new_status != current.get("status"):
        db.update_appointment_status(appt_id, new_status)

    # باقي الحقول (تاريخ/وقت/مدة/طبيب/ملاحظات) - update_appointment بيحافظ
    # على القيم الحالية لأي حقل مرسل كـ None
    edit = {k: v for k, v in fields.items()
            if k in ("appt_date", "appt_time", "duration_minutes", "doctor_name", "notes")}
    if edit:
        db.update_appointment(appt_id, **edit)
    return {"data": db.get_appointment(appt_id), "meta": {}}


@router.post("/{appt_id}/cancel")
def cancel_appointment(appt_id: int, _key: dict = Depends(require_scopes("appointments.write"))):
    appt_or_404(appt_id)
    db.update_appointment_status(appt_id, "cancelled")
    return {"data": db.get_appointment(appt_id), "meta": {}}


@router.delete("/{appt_id}")
def delete_appointment(appt_id: int, _key: dict = Depends(require_scopes("appointments.delete"))):
    appt_or_404(appt_id)
    db.delete_appointment(appt_id)
    return {"data": {"id": appt_id, "deleted": True}, "meta": {}}