# -*- coding: utf-8 -*-
"""الدوال المساعدة لطبقة الـ API (لا يوجد أي SQL هنا - كل منطق البيانات
في database.py وإحنا بنعيد الاستخدام بس)."""

import math

from fastapi import HTTPException
from starlette.status import HTTP_404_NOT_FOUND

import database as db


def paginate(items: list, page: int, page_size: int):
    """بيرجّع (شريحة الصفحة, meta) لردود القوائم المتسقة."""
    total = len(items)
    pages = int(math.ceil(total / page_size)) if total else 0
    if page > max(pages, 1):
        return [], {"page": page, "page_size": page_size,
                    "total": total, "pages": max(pages, 1)}
    start = (page - 1) * page_size
    slice_items = items[start:start + page_size]
    return slice_items, {
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": max(pages, 1),
    }


def patient_or_404(patient_id) -> dict:
    """بيرجّع المريض أو بيعمل 404 بترميز موحّد"""
    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail={"code": "patient_not_found",
                    "message": f"لا يوجد مريض بالرقم {patient_id}."},
        )
    return patient


def appointment_or_404(appt_id) -> dict:
    appt = db.get_appointment(appt_id)
    if not appt:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail={"code": "appointment_not_found",
                    "message": f"لا يوجد موعد بالرقم {appt_id}."},
        )
    return appt


def visit_or_404(visit_id) -> dict:
    visit = db.get_visit(visit_id)
    if not visit:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail={"code": "visit_not_found",
                    "message": f"لا توجد زيارة بالرقم {visit_id}."},
        )
    return visit


def transaction_or_404(tx_id) -> dict:
    tx = db.get_transaction(tx_id)
    if not tx:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail={"code": "transaction_not_found",
                    "message": f"لا توجد حركة مالية بالرقم {tx_id}."},
        )
    return tx


def build_odontogram(patient_id):
    """بيركّب عرض كامل لخريطة الأسنان من مصادر database.py المتعددة."""
    chart = {str(k): v for k, v in (db.get_tooth_chart(patient_id) or {}).items()}
    presence = {
        str(k): v for k, v in (db.get_tooth_presence(patient_id) or {}).items()
    }
    notes = {str(k): v for k, v in (db.get_tooth_notes(patient_id) or {}).items()}
    annotations = {
        str(k): v for k, v in (db.get_tooth_annotations_map(patient_id) or {}).items()
    }
    conditions = db.get_active_tooth_conditions(patient_id) or []

    # معالجات مسجلة على كل سن (من سجل المعالجات)
    treatments_by_tooth: dict[str, list] = {}
    for rec in db.get_treatment_records(patient_id):
        tooth = rec.get("tooth_number")
        if tooth is None:
            continue
        treatments_by_tooth.setdefault(str(tooth), []).append({
            "id": rec.get("id"),
            "treatment_key": rec.get("treatment_key"),
            "treatment_label": rec.get("treatment_label"),
            "price": rec.get("price"),
            "treatment_date": rec.get("treatment_date"),
            "doctor_name": rec.get("doctor_name"),
        })

    return {
        "tooth_chart": chart,
        "presence": presence,
        "notes": notes,
        "annotations": annotations,
        "active_conditions": conditions,
        "treatments_by_tooth": treatments_by_tooth,
    }


def add_treatment_with_charge(patient_id, tooth_number, treatment_key, price,
                              notes="", doctor_name=""):
    """تسجيل معالجة على سن معين + الحركة المالية (charge) المرتبطة بيها -
    نفس سلوك نافذة إضافة علاج في شارت الأسنان (add_transaction بعلاقة
    related_treatment_id عشان يفضلوا متطابقين دايًما)."""
    from pages import tooth_symbols

    label = tooth_symbols.BUILTIN_DISPLAY_SYMBOLS.get(
        treatment_key, treatment_key)
    record_id = db.add_treatment_record(
        patient_id=patient_id,
        tooth_number=tooth_number,
        treatment_key=treatment_key,
        treatment_label=label,
        price=price,
        notes=notes,
        doctor_name=doctor_name,
    )
    if price and price > 0:
        db.add_transaction(
            patient_id, "charge", price,
            description=f"{label} - سن {tooth_number}",
            related_treatment_id=record_id,
        )
    return record_id, label