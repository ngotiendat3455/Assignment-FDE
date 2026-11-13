"""
Global Pytest Isolation Fixture (Hermetic Offline Guarantee).

Ensures `python -m pytest backend/tests/` NEVER makes accidental external calls to
live Gemini, OpenAI, or X APIs even when developers populate real keys in `backend/.env`
for manual testing.
"""

import pytest

from backend.app.core.config import settings


@pytest.fixture(autouse=True)
def hermetic_offline_env(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    monkeypatch.setattr(settings, "X_BEARER_TOKEN", "")
    monkeypatch.setattr(settings, "X_API_KEY", "")
    monkeypatch.setattr(settings, "X_API_SECRET", "")
    monkeypatch.setattr(settings, "X_ACCESS_TOKEN", "")
    monkeypatch.setattr(settings, "X_ACCESS_TOKEN_SECRET", "")
    monkeypatch.setattr(settings, "DISPATCH_MODE", "SANDBOX")
    monkeypatch.setattr(settings, "LIVE_X_DRY_RUN", False)

