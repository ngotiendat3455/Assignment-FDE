from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.core.config import settings
from backend.app.core.database import Base, SessionLocal, engine
from backend.app.core.security import (
    decode_access_token,
    ensure_default_partner_user,
    get_current_user,
)
from backend.app.api.auth import router as auth_router
from backend.app.api.ingestion import router as ingestion_router
from backend.app.api.candidates import router as candidates_router

PUBLIC_API_PATHS = {
    "/",
    "/api/health",
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


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "dispatch_mode": settings.DISPATCH_MODE,
    }

