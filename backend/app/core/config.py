import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Search for ENV_FILE override first (e.g. .env.e2e), then backend/.env or root .env
_override_env = os.getenv("ENV_FILE")
env_path = Path(_override_env) if _override_env else Path(__file__).resolve().parent.parent.parent / ".env"
if not env_path.exists():
    env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)


class Settings:
    PROJECT_NAME: str = "X-Scout AI – Autonomous Scouting & Outreach System"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"

    # Server & CORS
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    _cors_origins: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3100,http://127.0.0.1:3100",
    )

    @property
    def CORS_ORIGINS(self) -> List[str]:
        return [o.strip() for o in self._cors_origins.split(",") if o.strip()]

    # Security (7-day default session = 10080 minutes for zero-friction evaluation)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "genai-fund-fde-secret-key-change-in-production-2026")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./outreach.db")
    # Only auto-seed historical OUT-101..104 rows on GET /api/ledger when explicitly enabled
    AUTO_SEED_LEDGER_BASELINE: bool = os.getenv("AUTO_SEED_LEDGER_BASELINE", "False").lower() in (
        "true",
        "1",
        "yes",
    )

    # Request/Response Contract Tracing (E2E & Contract Test Debugging)
    TRACE_REQUESTS: bool = os.getenv("TRACE_REQUESTS", "False").lower() in ("true", "1", "yes")
    TRACE_OUTPUT_DIR: str = os.getenv(
        "TRACE_OUTPUT_DIR",
        str(Path(__file__).resolve().parent.parent.parent.parent / "tests" / "manual" / "results" / "traces"),
    )

    # Centralized Runtime Profile ("OFFLINE_MOCK" | "LIVE_PRODUCTION" | "HYBRID_AUTO")
    RUNTIME_PROFILE: str = os.getenv("RUNTIME_PROFILE", "HYBRID_AUTO").upper()

    # Dispatch & Safety
    DISPATCH_MODE: str = os.getenv("DISPATCH_MODE", "SANDBOX").upper()
    LIVE_X_DRY_RUN: bool = os.getenv("LIVE_X_DRY_RUN", "False").lower() in ("true", "1", "yes")
    _allowed_test_handles: str = os.getenv("ALLOWED_TEST_HANDLES", "linhtran_robo,minh_quant,test_builder_sea")

    @property
    def ALLOWED_TEST_HANDLES(self) -> List[str]:
        return [h.strip().lower().lstrip("@") for h in self._allowed_test_handles.split(",") if h.strip()]

    # LLM API Keys & Models
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    GEMINI_FALLBACK_MODELS: List[str] = [
        m.strip()
        for m in os.getenv(
            "GEMINI_FALLBACK_MODELS",
            "gemini-3.1-flash-lite,gemini-2.5-flash,gemini-2.5-flash-lite",
        ).split(",")
        if m.strip()
    ]
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # X API v2 Base URL & Keys (override X_API_BASE_URL for $0 local dev simulator)
    X_API_BASE_URL: str = os.getenv("X_API_BASE_URL", "https://api.twitter.com/2")
    X_SIMULATOR_BASE_URL: str = os.getenv("X_SIMULATOR_BASE_URL", "http://127.0.0.1:8099/2")
    X_BEARER_TOKEN: str = os.getenv("X_BEARER_TOKEN", "")
    X_API_KEY: str = os.getenv("X_API_KEY", "")
    X_API_SECRET: str = os.getenv("X_API_SECRET", "")
    X_ACCESS_TOKEN: str = os.getenv("X_ACCESS_TOKEN", "")
    X_ACCESS_TOKEN_SECRET: str = os.getenv("X_ACCESS_TOKEN_SECRET", "")


settings = Settings()
