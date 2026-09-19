# -*- coding: utf-8 -*-
"""موارد الحسابات المالية بكل مريض (حركات + رصيد + معالجات + سجل قديم)."""

from fastapi import APIRouter, Depends

import database as db
from api.config import API_PREFIX
from api.security import require_scopes
from api.schemas import TransactionCreate, TransactionUpdate
from api.services import patient_or_404, transaction_or_404

router = APIRouter(prefix=API_PREFIX, tags=["financials"])


@router.get("/patients/{patient_id}/financials")
def get_financials(patient_id: int, _key: dict = Depends(require_scopes("financials.read"))):
    patient_or_404(patient_id)
    return {"data": {
        "transactions": db.get_transactions(patient_id),
        "treatment_records": db.get_treatment_records(patient_id),
        "balance": db.get_patient_balance(patient_id),
    }, "meta": {}}


@router.get("/patients/{patient_id}/balance")
def get_balance(patient_id: int, _key: dict = Depends(require_scopes("financials.read"))):
    patient_or_404(patient_id)
    return {"data": db.get_patient_balance(patient_id), "meta": {}}


@router.post("/patients/{patient_id}/transactions")
def create_transaction(patient_id: int, body: TransactionCreate,
                       _key: dict = Depends(require_scopes("financials.write"))):
    patient_or_404(patient_id)
    tx_id = db.add_transaction(
        patient_id=patient_id,
        tx_type=body.tx_type,
        amount=body.amount,
        description=body.description or "",
        tx_date=body.tx_date,
        related_treatment_id=body.related_treatment_id,
    )
    return {"data": db.get_transaction(tx_id), "meta": {}}


@router.patch("/transactions/{tx_id}")
def update_transaction(tx_id: int, body: TransactionUpdate,
                       _key: dict = Depends(require_scopes("financials.write"))):
    transaction_or_404(tx_id)
    fields = body.model_dump(exclude_none=True)
    if fields.get("amount") is not None:
        db.update_transaction_amount(tx_id, float(fields["amount"]))
    if fields.get("discount_amount") is not None:
        db.update_transaction_discount(tx_id, float(fields["discount_amount"]))
    return {"data": db.get_transaction(tx_id), "meta": {}}


@router.delete("/transactions/{tx_id}")
def delete_transaction(tx_id: int, _key: dict = Depends(require_scopes("financials.delete"))):
    transaction_or_404(tx_id)
    db.delete_transaction(tx_id)
    return {"data": {"id": tx_id, "deleted": True}, "meta": {}}