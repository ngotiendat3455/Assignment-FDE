import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Search for .env in current directory or backend directory
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if not env_path.exists():
    env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    PROJECT_NAME: str = "GenAI Fund – Autonomous Scouting & Outreach System"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"

    # Server
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "genai-fund-fde-secret-key-change-in-production-2026")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./outreach.db")

    # Dispatch & Safety
    DISPATCH_MODE: str = os.getenv("DISPATCH_MODE", "SANDBOX").upper()
    _allowed_test_handles: str = os.getenv("ALLOWED_TEST_HANDLES", "linhtran_robo,minh_quant,test_builder_sea")

    @property
    def ALLOWED_TEST_HANDLES(self) -> List[str]:
        return [h.strip().lower().lstrip("@") for h in self._allowed_test_handles.split(",") if h.strip()]

    # LLM API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # X API v2 Keys
    X_BEARER_TOKEN: str = os.getenv("X_BEARER_TOKEN", "")
    X_API_KEY: str = os.getenv("X_API_KEY", "")
    X_API_SECRET: str = os.getenv("X_API_SECRET", "")
    X_ACCESS_TOKEN: str = os.getenv("X_ACCESS_TOKEN", "")
    X_ACCESS_TOKEN_SECRET: str = os.getenv("X_ACCESS_TOKEN_SECRET", "")


settings = Settings()
