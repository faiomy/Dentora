# -*- coding: utf-8 -*-
"""
نماذج Pydantic لطلبات واستجابات الـ Dentora API.

الاستجابة دايًما بتلف على شكل:
    {"data": <value>, "meta": {...}}
حتى للأخطاء (بيتم إنتاجها في app.py بشكل موحّد):
    {"error": {"code": ..., "message": ..., "details": {}}}
"""

from typing import Generic, Literal, Optional, TypeVar
from pydantic import BaseModel, Field, ConfigDict, model_validator

T = TypeVar("T")


class Envelope(BaseModel, Generic[T]):
    data: T | None = None
    meta: dict = Field(default_factory=dict)


# ------------------------------------------------------------
# المرضى
# ------------------------------------------------------------

class PatientCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: str = Field(min_length=1, max_length=200)
    phone: str = Field(default="", max_length=50)
    birth_date: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    medical_notes: Optional[str] = None
    allergies: Optional[str] = None
    occupation: Optional[str] = None
    family_id: Optional[str] = None
    nationality: Optional[str] = None


class PatientUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=50)
    birth_date: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    medical_notes: Optional[str] = None
    allergies: Optional[str] = None
    occupation: Optional[str] = None
    family_id: Optional[str] = None
    nationality: Optional[str] = None
    discount_percent: Optional[float] = Field(default=None, ge=0, le=100)


# ------------------------------------------------------------
# المواعيد
# ------------------------------------------------------------

APPOINTMENT_STATUS_T = Literal[
    "confirmed", "arrived", "late", "completed", "cancelled", "no_show"
]


class AppointmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    patient_id: int = Field(gt=0)
    appt_date: str = Field(min_length=8, max_length=10)  # YYYY-MM-DD
    appt_time: str = Field(min_length=4, max_length=8)   # HH:MM
    doctor_name: str = Field(default="", max_length=200)
    status: APPOINTMENT_STATUS_T = "confirmed"
    notes: str = Field(default="", max_length=2000)
    duration_minutes: int = Field(default=30, ge=1, le=24 * 60)


class AppointmentUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    appt_date: Optional[str] = None
    appt_time: Optional[str] = None
    duration_minutes: Optional[int] = Field(default=None, ge=1, le=24 * 60)
    doctor_name: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[APPOINTMENT_STATUS_T] = None


# ------------------------------------------------------------
# زيارات المتابعة
# ------------------------------------------------------------

class VisitCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    notes: str = Field(min_length=1, max_length=5000)
    visit_date: Optional[str] = None
    doctor_name: Optional[str] = None


class VisitUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    notes: Optional[str] = Field(default=None, min_length=1, max_length=5000)
    visit_date: Optional[str] = None
    doctor_name: Optional[str] = None


# ------------------------------------------------------------
# الحسابات / الحركات المالية
# ------------------------------------------------------------

class TransactionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tx_type: Literal["charge", "payment"]
    amount: float = Field(gt=0, le=1_000_000_000)
    description: str = Field(default="", max_length=2000)
    tx_date: Optional[str] = None
    related_treatment_id: Optional[int] = None


class TransactionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: Optional[float] = Field(default=None, gt=0, le=1_000_000_000)
    discount_amount: Optional[float] = Field(default=None, ge=0)


# ------------------------------------------------------------
# خريطة الأسنان (Odontogram)
# ------------------------------------------------------------

TOOTH_PRESENCE_T = Literal["present", "primary_present", "unerupted", "missing", "impacted"]


class OdontogramToothUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Optional[TOOTH_PRESENCE_T] = None
    notes: Optional[str] = Field(default=None, max_length=2000)
    treatment_keys: Optional[list[str]] = None  # سيتم تطبيقه على خريطة المعالجات


class OdontogramAnnotationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note_date: Optional[str] = None
    doctor_name: Optional[str] = None
    note_text: str = Field(min_length=1, max_length=2000)


class TreatmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tooth_number: int = Field(ge=1, le=48)
    treatment_key: str = Field(min_length=1, max_length=100)
    price: float = Field(ge=0, le=1_000_000_000)
    notes: str = Field(default="", max_length=2000)
    doctor_name: Optional[str] = None


class PaginationQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)