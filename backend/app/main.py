from contextlib import asynccontextmanager
import time
from typing import List, Optional
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from backend.app.core.config import settings
from backend.app.core.database import Base, SessionLocal, engine, get_db
from backend.app.core.runtime_gateway import RuntimeGateway
from backend.app.core.security import (
    decode_access_token,
    ensure_default_partner_user,
    get_current_user,
)
from backend.app.core.tracing import (
    capture_db_snapshot,
    finish_flow_session,
    get_active_testcase,
    record_flow_step,
    record_http_trace,
    start_flow_session,
)
from backend.app.api.auth import router as auth_router
from backend.app.api.ingestion import router as ingestion_router
from backend.app.api.candidates import router as candidates_router
from backend.app.api.queue import router as queue_router
from backend.app.api.ledger import router as ledger_router

PUBLIC_API_PATHS = {
    "/",
    "/api/health",
    "/api/system/runtime",
    "/api/_trace/session",
    "/api/_trace/step",
    "/api/_trace/finish",
    "/api/auth/login",
    "/api/auth/demo-login",
    "/api/auth/register",
    "/api/auth/logout",
    "/docs",
    "/redoc",
    "/openapi.json",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_default_partner_user(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)


@app.middleware("http")
async def auth_guard_middleware(request: Request, call_next):
    """
    Global FastAPI HTTP Middleware blocking unauthenticated requests to all private /api/* routes.
    Checks 'Authorization: Bearer <jwt>' header or 'session_token' HttpOnly cookie.
    """
    if request.method == "OPTIONS":
        return await call_next(request)

    path = request.url.path.rstrip("/") or "/"
    if path in PUBLIC_API_PATHS or not path.startswith("/api"):
        return await call_next(request)

    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    if not token:
        token = request.cookies.get("session_token")

    if not token:
        return JSONResponse(
            status_code=401,
            content={
                "detail": "Not authenticated. Missing Bearer token or session_token cookie."
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or expired authentication token."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    request.state.user_email = payload.get("sub")
    return await call_next(request)


def _read_active_db_snapshot():
    """Capture DB state snapshot using test DB override when active, else SessionLocal."""
    try:
        override = app.dependency_overrides.get(get_db)
        if override is not None:
            gen = override()
            try:
                snap_db = next(gen)
                return capture_db_snapshot(snap_db)
            finally:
                gen.close()
        with SessionLocal() as snap_db:
            return capture_db_snapshot(snap_db)
    except Exception:
        return None


@app.middleware("http")
async def contract_trace_middleware(request: Request, call_next):
    """
    Opt-in per-testcase HTTP & JSON contract tracer for E2E/Contract debugging.
    Active only when TRACE_REQUESTS=true (e.g. .env.e2e or contract test suite).
    """
    path = request.url.path.rstrip("/") or "/"
    if (
        not settings.TRACE_REQUESTS
        or request.method == "OPTIONS"
        or path == "/api/health"
        or path.startswith("/api/_trace")
    ):
        return await call_next(request)

    req_body = await request.body()
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - started) * 1000.0

    resp_chunks = [chunk async for chunk in response.body_iterator]
    resp_body = b"".join(resp_chunks)

    testcase_id = get_active_testcase(request.headers.get("X-Test-Case-Id"))
    db_snap = _read_active_db_snapshot() if request.method != "GET" else None
    record_http_trace(
        testcase_id=testcase_id,
        method=request.method,
        path=path,
        query=request.url.query,
        status_code=response.status_code,
        duration_ms=duration_ms,
        req_bytes=req_body,
        res_bytes=resp_body,
        db_snapshot=db_snap,
    )

    preserved_headers = [
        (k, v)
        for k, v in response.raw_headers
        if k.lower() != b"content-length"
    ]
    preserved_headers.append((b"content-length", str(len(resp_body)).encode("latin-1")))
    rebuilt = Response(
        content=resp_body,
        status_code=response.status_code,
        media_type=response.media_type,
    )
    rebuilt.raw_headers = preserved_headers
    return rebuilt


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(
    ingestion_router,
    prefix=settings.API_V1_PREFIX,
    dependencies=[Depends(get_current_user)],
)
app.include_router(
    candidates_router,
    prefix=settings.API_V1_PREFIX,
    dependencies=[Depends(get_current_user)],
)
app.include_router(
    queue_router,
    prefix=settings.API_V1_PREFIX,
    dependencies=[Depends(get_current_user)],
)
app.include_router(
    ledger_router,
    prefix=settings.API_V1_PREFIX,
    dependencies=[Depends(get_current_user)],
)


@app.get("/api/health")
def health_check():
    ai_plan = RuntimeGateway.resolve_ai_plan()
    x_plan = RuntimeGateway.resolve_x_lookup_plan()
    dm_plan = RuntimeGateway.resolve_dm_dispatch_plan(settings.DISPATCH_MODE)
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "runtime_profile": RuntimeGateway.get_active_profile(),
        "dispatch_mode": settings.DISPATCH_MODE,
        "active_drivers": {
            "ai_engine": ai_plan.ai_engine,
            "ai_model": ai_plan.model_used,
            "x_lookup_mode": x_plan.source_mode,
            "dm_dispatch_execution": dm_plan.dispatch_execution,
        },
    }


@app.get("/api/system/runtime")
def read_runtime_gateway_status():
    """Return centralized RuntimeGateway execution table (OFFLINE_MOCK vs LIVE_PRODUCTION vs HYBRID_AUTO)."""
    return RuntimeGateway.get_runtime_status_summary()


class _TraceSessionRequest(BaseModel):
    testcase_id: str
    flow_ref: str = ""
    title: str = ""
    expected_states: List[str] = []
    forbidden_transitions: List[str] = []
    reset_file: bool = True


class _TraceStepRequest(BaseModel):
    testcase_id: str
    step: str
    ui_action: str = ""
    expected: str = ""
    include_db_snapshot: bool = True


class _TraceFinishRequest(BaseModel):
    testcase_id: str
    status: str = "PASSED"
    notes: str = ""


@app.post("/api/_trace/session")
def trace_start_session(payload: _TraceSessionRequest):
    if not settings.TRACE_REQUESTS:
        raise HTTPException(status_code=404, detail="Not found")
    snap = _read_active_db_snapshot()
    md_path = start_flow_session(
        testcase_id=payload.testcase_id,
        flow_ref=payload.flow_ref,
        title=payload.title,
        expected_states=payload.expected_states,
        forbidden_transitions=payload.forbidden_transitions,
        db_snapshot=snap,
        reset_file=payload.reset_file,
    )
    return {"status": "ok", "trace_file": str(md_path), "db_snapshot": snap}


@app.post("/api/_trace/step")
def trace_record_step(payload: _TraceStepRequest):
    if not settings.TRACE_REQUESTS:
        raise HTTPException(status_code=404, detail="Not found")
    snap = _read_active_db_snapshot() if payload.include_db_snapshot else None
    record_flow_step(
        testcase_id=payload.testcase_id,
        step=payload.step,
        ui_action=payload.ui_action,
        expected=payload.expected,
        db_snapshot=snap,
    )
    return {"status": "ok", "db_snapshot": snap}


@app.post("/api/_trace/finish")
def trace_finish_session(payload: _TraceFinishRequest):
    if not settings.TRACE_REQUESTS:
        raise HTTPException(status_code=404, detail="Not found")
    snap = _read_active_db_snapshot()
    finish_flow_session(
        testcase_id=payload.testcase_id,
        status=payload.status,
        notes=payload.notes,
        db_snapshot=snap,
    )
    return {"status": "ok", "db_snapshot": snap}

