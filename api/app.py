# -*- coding: utf-8 -*-
"""تجميع تطبيق FastAPI الخاص بـ Dentora + معالجات الأخطاء الموحّدة."""

import json

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status

from api.config import API_PREFIX, API_VERSION, APP_DESCRIPTION, APP_TITLE
from api.routers import (
    appointments,
    financials,
    odontogram,
    patients,
    system,
    visits,
)

app = FastAPI(
    title=APP_TITLE,
    version=API_VERSION,
    description=APP_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.include_router(patients.router)
app.include_router(appointments.router)
app.include_router(visits.router)
app.include_router(financials.router)
app.include_router(odontogram.router)
app.include_router(system.router)


def _error_response(code: str, message: str, status_code: int, details=None):
    return JSONResponse(
        status_code=status_code,
        content={"error": {
            "code": code,
            "message": message,
            **({"details": details} if details else {}),
        }},
    )


@app.exception_handler(HTTPException)
async def _http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        return _error_response(
            code=exc.detail.get("code", "http_error"),
            message=exc.detail.get("message", "طلب مرفوض."),
            status_code=exc.status_code,
            details=exc.detail.get("details"),
        )
    return _error_response(
        code="http_error", message=str(exc.detail), status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def _validation_exception_handler(request: Request, exc: RequestValidationError):
    return _error_response(
        code="validation_error",
        message="البيانات المرسلة غير صحيحة - راجع الحقول الخطأ.",
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        details={"errors": json.loads(json.dumps(exc.errors(), ensure_ascii=False,
                                                 default=str))},
    )


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception):
    return _error_response(
        code="internal_error",
        message="خطأ غير متوقع في الخادم.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )