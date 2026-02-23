"""
FastAPI 應用程式進入點。
職責：建立 app 物件、掛載全域 Exception Handlers、Include 各路由。
使用 Swagger UI 下拉選單切換 API 版本。
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
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
from app.controllers.api_v2 import items_controller as items_v2_controller

# ── 確保所有 ORM Model 在 Base.metadata 中註冊 ─────────────────
from app.infra.db import Base, engine, SessionLocal
from app.repositories.department_repo import DepartmentModel  # noqa: F401
from app.repositories.formula_repo import FormulaModel  # noqa: F401
from app.repositories.patient_field_repo import PatientFieldModel  # noqa: F401

# ── 開發用：自動建立資料表（正式環境請改用 Alembic）
Base.metadata.create_all(bind=engine)

# ── 建立 FastAPI App（關閉預設 docs，改用自訂版本選單）──────────
app = FastAPI(
    title="Module Scoring API",
    description="醫療評分公式管理系統 API",
    version="1.0.0",
    docs_url=None,        # 關閉預設 /docs
    redoc_url=None,       # 關閉預設 /redoc
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
# V1：科別、公式、病人欄位、AI 聊天
app.include_router(departments_controller.router)
app.include_router(formulas_controller.router)
app.include_router(patient_fields_controller.router)
app.include_router(scoring_controller.router)

# V2：Items
app.include_router(items_v2_controller.router)


# ── 版本分組定義 ─────────────────────────────────────────────
_VERSION_SPECS = {
    "v1": {
        "title": "Module Scoring API - V1",
        "description": "科別、公式、病人欄位管理 + AI 聊天",
        "version": "1.0.0",
        "path_prefixes": ["/v1/"],
    },
    "v2": {
        "title": "Module Scoring API - V2",
        "description": "Items CRUD",
        "version": "2.0.0",
        "path_prefixes": ["/v2/"],
    },
}


def _build_filtered_openapi(spec_key: str) -> dict:
    """根據路徑前綴過濾完整 OpenAPI schema，產出版本專屬 spec。"""
    full = app.openapi()
    cfg = _VERSION_SPECS[spec_key]
    prefixes = cfg["path_prefixes"]

    # 過濾 paths
    filtered_paths = {
        path: ops
        for path, ops in full.get("paths", {}).items()
        if any(path.startswith(p) for p in prefixes)
    }

    # 收集被引用的 schemas
    import json
    paths_json = json.dumps(filtered_paths)
    used_schemas = set()
    for schema_name in full.get("components", {}).get("schemas", {}):
        if f'"#/components/schemas/{schema_name}"' in paths_json:
            used_schemas.add(schema_name)

    # 遞迴收集巢狀引用
    all_schemas = full.get("components", {}).get("schemas", {})
    to_check = list(used_schemas)
    while to_check:
        name = to_check.pop()
        schema_json = json.dumps(all_schemas.get(name, {}))
        for other_name in all_schemas:
            if other_name not in used_schemas:
                if f'"#/components/schemas/{other_name}"' in schema_json:
                    used_schemas.add(other_name)
                    to_check.append(other_name)

    filtered_schemas = {
        k: v for k, v in all_schemas.items() if k in used_schemas
    }

    return {
        "openapi": full.get("openapi", "3.1.0"),
        "info": {
            "title": cfg["title"],
            "description": cfg["description"],
            "version": cfg["version"],
        },
        "paths": filtered_paths,
        "components": {"schemas": filtered_schemas} if filtered_schemas else {},
    }


@app.get("/openapi-v1.json", include_in_schema=False)
async def openapi_v1():
    return _build_filtered_openapi("v1")


@app.get("/openapi-v2.json", include_in_schema=False)
async def openapi_v2():
    return _build_filtered_openapi("v2")


# ── 自訂 Swagger UI：版本下拉選單 ────────────────────────────
_SWAGGER_UI_HTML = """
<!DOCTYPE html>
<html><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Module Scoring API</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css"/>
</head><body>
<div id="swagger-ui"></div>
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
<script>
SwaggerUIBundle({
    urls: [
        {url: "/openapi-v1.json", name: "V1 - Scoring System"},
        {url: "/openapi-v2.json", name: "V2 - Items"}
    ],
    "urls.primaryName": "V1 - Scoring System",
    dom_id: "#swagger-ui",
    presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
    layout: "StandaloneLayout"
});
</script>
</body></html>
"""


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui():
    return HTMLResponse(_SWAGGER_UI_HTML)

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
