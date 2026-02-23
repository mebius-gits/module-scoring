"""
FastAPI 應用程式進入點。
職責：建立 app 物件、掛載全域 Exception Handlers、Include 各路由。
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.common.exceptions import (
    NotFoundException,
    RateLimitException,
    UnauthorizedException,
    ValidationException,
)

# ── Controllers ───────────────────────────────────────────────
from app.controllers.api_v1 import items_controller
from app.controllers.api_v1 import departments_controller
from app.controllers.api_v1 import formulas_controller
from app.controllers.api_v1 import patient_fields_controller
from app.controllers.ai_v1 import scoring_controller

# ── 確保所有 ORM Model 在 Base.metadata 中註冊 ─────────────────
from app.infra.db import Base, engine, SessionLocal
from app.repositories.department_repo import DepartmentModel  # noqa: F401
from app.repositories.formula_repo import FormulaModel  # noqa: F401
from app.repositories.patient_field_repo import PatientFieldModel  # noqa: F401

# ── 開發用：自動建立資料表（正式環境請改用 Alembic）
Base.metadata.create_all(bind=engine)

# ── 建立 FastAPI App ──────────────────────────────────────────
app = FastAPI(
    title="Clean Architecture FastAPI",
    description="前端互動 API (/api/v1) 與 AI 任務 API (/ai/v1) 分離設計",
    version="1.0.0",
)

# ── CORS（開發用，允許前端跨域呼叫）──────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 全域 Domain Exception → HTTP Exception 映射 ──────────────
@app.exception_handler(NotFoundException)
async def not_found_handler(request: Request, exc: NotFoundException):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(UnauthorizedException)
async def unauthorized_handler(request: Request, exc: UnauthorizedException):
    return JSONResponse(status_code=401, content={"detail": str(exc)})


@app.exception_handler(RateLimitException)
async def rate_limit_handler(request: Request, exc: RateLimitException):
    return JSONResponse(status_code=429, content={"detail": str(exc)})


@app.exception_handler(ValidationException)
async def validation_handler(request: Request, exc: ValidationException):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


# ── 掛載路由 ─────────────────────────────────────────────────
# 前端互動 API（/api/v1）
app.include_router(items_controller.router)
app.include_router(departments_controller.router)
app.include_router(formulas_controller.router)
app.include_router(patient_fields_controller.router)

# AI 任務 API（/ai/v1）
app.include_router(scoring_controller.router)

# ── 掛載前端靜態檔案 ─────────────────────────────────────────
_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if _FRONTEND_DIR.is_dir():
    app.mount("/frontend", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")


# ── Startup Event：建表 + Seed 預設病人欄位 ─────────────────────


def _seed_default_patient_fields():
    """若 patient_fields 資料表為空，自動注入預設欄位。"""
    from app.models.patient_fields import PatientFieldCreate
    from app.repositories.patient_field_repo import PatientFieldRepo

    DEFAULT_FIELDS = [
        PatientFieldCreate(field_name="age",         label="年齡 (歲)",      field_type="int"),
        PatientFieldCreate(field_name="height",      label="身高 (公尺)",    field_type="float"),
        PatientFieldCreate(field_name="weight",      label="體重 (公斤)",    field_type="float"),
        PatientFieldCreate(field_name="cholesterol", label="膽固醇 (mg/dL)", field_type="float"),
        PatientFieldCreate(field_name="has_disease", label="是否患有常見疾病", field_type="boolean"),
    ]
    db = SessionLocal()
    try:
        repo = PatientFieldRepo(db)
        if repo.count() > 0:
            return  # 已有資料，跳過
        for f in DEFAULT_FIELDS:
            try:
                repo.create(f)
            except Exception:
                pass  # 跳過重複
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    """應用程式啟動時自動 seed 預設資料"""
    _seed_default_patient_fields()


@app.get("/health", tags=["Health"])
def health_check():
    """健康檢查端點"""
    return {"status": "ok"}
