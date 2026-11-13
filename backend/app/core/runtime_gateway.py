"""
Centralized Runtime Execution Gateway (`backend/app/core/runtime_gateway.py`).

Provides a single point of control and observability for all external AI (Gemini / OpenAI)
and X API v2 (Handle Lookup & OAuth 1.0a Direct Message Dispatch) interactions across `/backend`.

Supported `RUNTIME_PROFILE` modes:
1. `OFFLINE_MOCK` (Case 1 — $0 Deterministic AI + Local X Simulator + Sandbox DM):
   - AI Evaluation: Always runs local `DETERMINISTIC_RUBRIC` ($0), never calling Gemini/OpenAI even if keys exist.
   - X Handle Lookup: Routes to Local X Simulator (`http://127.0.0.1:8099/2`) with `sim_dev_bearer_token`.
   - DM Dispatch: Never makes external OAuth 1.0a network calls (`SANDBOX_SIMULATED` / `LIVE_X_DRY_RUN`).
2. `LIVE_PRODUCTION` (Case 2 — Real Gemini/OpenAI + Real X API v2, Zero Silent Fallback):
   - AI Evaluation: Requires real `GEMINI_API_KEY` or `OPENAI_API_KEY`. Forbids silent fallback to deterministic rubric; missing key or upstream failure transitions candidate to `AI_FAILED`.
   - X Handle Lookup: Requires live `https://api.twitter.com/2` and real `X_BEARER_TOKEN` (blocks localhost simulator or missing token with HTTP 503).
   - DM Dispatch: When dispatching `LIVE_X`, enforces `ALLOWED_TEST_HANDLES` AND requires all 4 OAuth 1.0a credentials with `LIVE_X_DRY_RUN=False`. Forbids silent generation of fake `sim_dm_...` IDs.
3. `HYBRID_AUTO` (Default backward-compatible mode):
   - Dynamically uses configured keys/URLs per service while stamping explicit `execution_meta` on every response.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from backend.app.core.config import settings

VALID_RUNTIME_PROFILES = ("OFFLINE_MOCK", "LIVE_PRODUCTION", "HYBRID_AUTO")
DEFAULT_SIMULATOR_BASE_URL = "http://127.0.0.1:8099/2"
DEFAULT_LIVE_X_BASE_URL = "https://api.twitter.com/2"


def _is_real_secret(value: Optional[str]) -> bool:
    v = (value or "").strip()
    return bool(v and not v.startswith("your_"))


def _is_live_x_bearer_token(value: Optional[str]) -> bool:
    v = (value or "").strip()
    return bool(v and not v.startswith("your_") and not v.startswith("sim_"))


def _is_localhost_url(url: str) -> bool:
    lowered = (url or "").strip().lower()
    return "127.0.0.1" in lowered or "localhost" in lowered or "0.0.0.0" in lowered


@dataclass
class AIExecutionPlan:
    profile: str
    ai_engine: str  # "DETERMINISTIC_RUBRIC" | "LIVE_GEMINI" | "LIVE_OPENAI" | "UNCONFIGURED_LIVE_LLM"
    model_used: str
    allow_external_llm: bool
    require_external_llm: bool
    external_network_call: bool
    strict_error: Optional[str] = None

    def to_meta(self, actual_model_used: Optional[str] = None) -> Dict[str, Any]:
        return {
            "profile": self.profile,
            "ai_engine": self.ai_engine,
            "model_used": actual_model_used or self.model_used,
            "external_network_call": self.external_network_call,
        }


@dataclass
class XLookupExecutionPlan:
    profile: str
    source_mode: str  # "X_API_SIMULATOR" | "LIVE_X_API"
    base_url: str
    bearer_token: str
    external_network_call: bool
    strict_error: Optional[str] = None

    def to_meta(self) -> Dict[str, Any]:
        return {
            "profile": self.profile,
            "source_mode": self.source_mode,
            "base_url": self.base_url,
            "external_network_call": self.external_network_call,
        }


@dataclass
class DMDispatchExecutionPlan:
    profile: str
    dispatch_mode: str  # "SANDBOX" | "LIVE_X"
    dispatch_execution: str  # "SANDBOX_SIMULATED" | "LIVE_X_DRY_RUN" | "LIVE_X_REAL_SENT"
    should_call_external_x: bool
    external_network_call: bool
    strict_error: Optional[str] = None

    def to_meta(self) -> Dict[str, Any]:
        return {
            "profile": self.profile,
            "dispatch_mode": self.dispatch_mode,
            "dispatch_execution": self.dispatch_execution,
            "external_network_call": self.external_network_call,
        }


class RuntimeGateway:
    """Single point of control and introspection for AI & X API execution modes."""

    @staticmethod
    def get_active_profile() -> str:
        raw = (getattr(settings, "RUNTIME_PROFILE", "HYBRID_AUTO") or "HYBRID_AUTO").strip().upper()
        if raw in VALID_RUNTIME_PROFILES:
            return raw
        return "HYBRID_AUTO"

    @classmethod
    def resolve_ai_plan(cls, allow_external_override: bool = True) -> AIExecutionPlan:
        profile = cls.get_active_profile()
        has_gemini = _is_real_secret(settings.GEMINI_API_KEY)
        has_openai = _is_real_secret(settings.OPENAI_API_KEY)
        gemini_model = (settings.GEMINI_MODEL or "gemini-3.5-flash").strip()
        openai_model = (settings.OPENAI_MODEL or "gpt-4o-mini").strip()

        # Case 1: Strict $0 Offline Mock
        if profile == "OFFLINE_MOCK" or not allow_external_override:
            return AIExecutionPlan(
                profile=profile,
                ai_engine="DETERMINISTIC_RUBRIC",
                model_used="tri-guard-local-v1",
                allow_external_llm=False,
                require_external_llm=False,
                external_network_call=False,
            )

        # Case 2: Strict Live Production (Zero silent fallback to deterministic rubric)
        if profile == "LIVE_PRODUCTION":
            if has_gemini:
                return AIExecutionPlan(
                    profile=profile,
                    ai_engine="LIVE_GEMINI",
                    model_used=gemini_model,
                    allow_external_llm=True,
                    require_external_llm=True,
                    external_network_call=True,
                )
            if has_openai:
                return AIExecutionPlan(
                    profile=profile,
                    ai_engine="LIVE_OPENAI",
                    model_used=openai_model,
                    allow_external_llm=True,
                    require_external_llm=True,
                    external_network_call=True,
                )
            return AIExecutionPlan(
                profile=profile,
                ai_engine="UNCONFIGURED_LIVE_LLM",
                model_used="none",
                allow_external_llm=True,
                require_external_llm=True,
                external_network_call=False,
                strict_error=(
                    "[LIVE_PRODUCTION] Missing GEMINI_API_KEY (or OPENAI_API_KEY). "
                    "Silent fallback to deterministic rubric ($0) is disabled in LIVE_PRODUCTION."
                ),
            )

        # Case 3: HYBRID_AUTO (uses live LLM if key is configured, otherwise $0 rubric)
        if has_gemini:
            return AIExecutionPlan(
                profile=profile,
                ai_engine="LIVE_GEMINI",
                model_used=gemini_model,
                allow_external_llm=True,
                require_external_llm=False,
                external_network_call=True,
            )
        if has_openai:
            return AIExecutionPlan(
                profile=profile,
                ai_engine="LIVE_OPENAI",
                model_used=openai_model,
                allow_external_llm=True,
                require_external_llm=False,
                external_network_call=True,
            )
        return AIExecutionPlan(
            profile=profile,
            ai_engine="DETERMINISTIC_RUBRIC",
            model_used="tri-guard-local-v1",
            allow_external_llm=False,
            require_external_llm=False,
            external_network_call=False,
        )

    @classmethod
    def resolve_x_lookup_plan(cls) -> XLookupExecutionPlan:
        profile = cls.get_active_profile()
        configured_base = (getattr(settings, "X_API_BASE_URL", "") or DEFAULT_LIVE_X_BASE_URL).strip().rstrip("/")
        configured_token = (getattr(settings, "X_BEARER_TOKEN", "") or "").strip()

        # Case 1: Strict $0 Offline Mock -> route to Local X Simulator
        if profile == "OFFLINE_MOCK":
            sim_base = (
                configured_base
                if _is_localhost_url(configured_base)
                else getattr(settings, "X_SIMULATOR_BASE_URL", DEFAULT_SIMULATOR_BASE_URL).strip().rstrip("/")
            )
            sim_token = configured_token if _is_real_secret(configured_token) else "sim_dev_bearer_token"
            return XLookupExecutionPlan(
                profile=profile,
                source_mode="X_API_SIMULATOR",
                base_url=sim_base,
                bearer_token=sim_token,
                external_network_call=False,
            )

        # Case 2: Strict Live Production -> must point to real X API v2 with real Bearer token
        if profile == "LIVE_PRODUCTION":
            if _is_localhost_url(configured_base):
                return XLookupExecutionPlan(
                    profile=profile,
                    source_mode="LIVE_X_API",
                    base_url=configured_base,
                    bearer_token=configured_token,
                    external_network_call=False,
                    strict_error=(
                        f"[LIVE_PRODUCTION] X_API_BASE_URL is pointing to local simulator ({configured_base}). "
                        "Set X_API_BASE_URL=https://api.twitter.com/2 for LIVE_PRODUCTION."
                    ),
                )
            if not _is_live_x_bearer_token(configured_token):
                return XLookupExecutionPlan(
                    profile=profile,
                    source_mode="LIVE_X_API",
                    base_url=configured_base,
                    bearer_token="",
                    external_network_call=False,
                    strict_error=(
                        "[LIVE_PRODUCTION] Missing or simulator X_BEARER_TOKEN. "
                        "Configure a real X API v2 Bearer Token in backend/.env for LIVE_PRODUCTION."
                    ),
                )
            return XLookupExecutionPlan(
                profile=profile,
                source_mode="LIVE_X_API",
                base_url=configured_base,
                bearer_token=configured_token,
                external_network_call=True,
            )

        # Case 3: HYBRID_AUTO
        is_sim = _is_localhost_url(configured_base)
        if not _is_real_secret(configured_token):
            return XLookupExecutionPlan(
                profile=profile,
                source_mode="X_API_SIMULATOR" if is_sim else "LIVE_X_API",
                base_url=configured_base,
                bearer_token="",
                external_network_call=False,
                strict_error=(
                    "X_BEARER_TOKEN is not configured. Set X_BEARER_TOKEN in backend/.env, or run the local "
                    "X API simulator (`python -m backend.scripts.x_simulator`) with X_API_BASE_URL=http://127.0.0.1:8099/2."
                ),
            )
        return XLookupExecutionPlan(
            profile=profile,
            source_mode="X_API_SIMULATOR" if is_sim else "LIVE_X_API",
            base_url=configured_base,
            bearer_token=configured_token,
            external_network_call=not is_sim,
        )

    @classmethod
    def has_full_x_oauth1_credentials(cls) -> bool:
        return all(
            _is_real_secret(val)
            for val in (
                settings.X_API_KEY,
                settings.X_API_SECRET,
                settings.X_ACCESS_TOKEN,
                settings.X_ACCESS_TOKEN_SECRET,
            )
        )

    @classmethod
    def get_missing_x_oauth1_keys(cls) -> List[str]:
        missing: List[str] = []
        for key_name in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"):
            if not _is_real_secret(getattr(settings, key_name, "")):
                missing.append(key_name)
        return missing

    @classmethod
    def resolve_dm_dispatch_plan(cls, requested_mode: Optional[str] = None) -> DMDispatchExecutionPlan:
        profile = cls.get_active_profile()
        normalized_mode = (requested_mode or settings.DISPATCH_MODE or "SANDBOX").strip().upper()
        has_oauth = cls.has_full_x_oauth1_credentials()
        dry_run = bool(getattr(settings, "LIVE_X_DRY_RUN", False))
        configured_base = (getattr(settings, "X_API_BASE_URL", "") or DEFAULT_LIVE_X_BASE_URL).strip()
        is_sim_base = _is_localhost_url(configured_base)

        # Case 1: Strict $0 Offline Mock -> never call external X DM endpoint
        if profile == "OFFLINE_MOCK":
            exec_label = "LIVE_X_DRY_RUN" if normalized_mode == "LIVE_X" else "SANDBOX_SIMULATED"
            return DMDispatchExecutionPlan(
                profile=profile,
                dispatch_mode=normalized_mode,
                dispatch_execution=exec_label,
                should_call_external_x=False,
                external_network_call=False,
            )

        # Case 2: Strict Live Production -> forbid silent sim_dm fallback when LIVE_X is requested
        if profile == "LIVE_PRODUCTION":
            if normalized_mode == "LIVE_X":
                missing_oauth = cls.get_missing_x_oauth1_keys()
                if missing_oauth:
                    return DMDispatchExecutionPlan(
                        profile=profile,
                        dispatch_mode="LIVE_X",
                        dispatch_execution="BLOCKED_MISSING_OAUTH",
                        should_call_external_x=False,
                        external_network_call=False,
                        strict_error=(
                            f"[LIVE_PRODUCTION] Cannot dispatch LIVE_X DM: missing OAuth 1.0a credentials "
                            f"({', '.join(missing_oauth)}). Silent fallback to simulated DM (sim_dm_...) is disabled."
                        ),
                    )
                if dry_run:
                    return DMDispatchExecutionPlan(
                        profile=profile,
                        dispatch_mode="LIVE_X",
                        dispatch_execution="BLOCKED_DRY_RUN_ACTIVE",
                        should_call_external_x=False,
                        external_network_call=False,
                        strict_error=(
                            "[LIVE_PRODUCTION] Cannot dispatch LIVE_X DM while LIVE_X_DRY_RUN=True. "
                            "Set LIVE_X_DRY_RUN=False in backend/.env for real X DM delivery."
                        ),
                    )
                if is_sim_base:
                    return DMDispatchExecutionPlan(
                        profile=profile,
                        dispatch_mode="LIVE_X",
                        dispatch_execution="BLOCKED_SIMULATOR_URL",
                        should_call_external_x=False,
                        external_network_call=False,
                        strict_error=(
                            f"[LIVE_PRODUCTION] Cannot dispatch LIVE_X DM while X_API_BASE_URL points to local simulator ({configured_base})."
                        ),
                    )
                return DMDispatchExecutionPlan(
                    profile=profile,
                    dispatch_mode="LIVE_X",
                    dispatch_execution="LIVE_X_REAL_SENT",
                    should_call_external_x=True,
                    external_network_call=True,
                )

            return DMDispatchExecutionPlan(
                profile=profile,
                dispatch_mode="SANDBOX",
                dispatch_execution="SANDBOX_SIMULATED",
                should_call_external_x=False,
                external_network_call=False,
            )

        # Case 3: HYBRID_AUTO
        if normalized_mode == "LIVE_X" and has_oauth and not dry_run:
            return DMDispatchExecutionPlan(
                profile=profile,
                dispatch_mode="LIVE_X",
                dispatch_execution="LIVE_X_REAL_SENT",
                should_call_external_x=True,
                external_network_call=not is_sim_base,
            )
        if normalized_mode == "LIVE_X":
            return DMDispatchExecutionPlan(
                profile=profile,
                dispatch_mode="LIVE_X",
                dispatch_execution="LIVE_X_DRY_RUN",
                should_call_external_x=False,
                external_network_call=False,
            )
        return DMDispatchExecutionPlan(
            profile=profile,
            dispatch_mode="SANDBOX",
            dispatch_execution="SANDBOX_SIMULATED",
            should_call_external_x=False,
            external_network_call=False,
        )

    @classmethod
    def get_runtime_status_summary(cls) -> Dict[str, Any]:
        """Return a centralized snapshot of active profile, drivers, and live-readiness diagnostics."""
        profile = cls.get_active_profile()
        ai_plan = cls.resolve_ai_plan()
        x_lookup_plan = cls.resolve_x_lookup_plan()
        dm_plan = cls.resolve_dm_dispatch_plan(settings.DISPATCH_MODE)

        missing_for_live: List[str] = []
        if not (_is_real_secret(settings.GEMINI_API_KEY) or _is_real_secret(settings.OPENAI_API_KEY)):
            missing_for_live.append("GEMINI_API_KEY (or OPENAI_API_KEY)")
        if not _is_live_x_bearer_token(settings.X_BEARER_TOKEN):
            missing_for_live.append("X_BEARER_TOKEN (live token, not sim_*)")
        if _is_localhost_url(getattr(settings, "X_API_BASE_URL", "")):
            missing_for_live.append("X_API_BASE_URL (must be https://api.twitter.com/2)")
        missing_for_live.extend(cls.get_missing_x_oauth1_keys())

        return {
            "runtime_profile": profile,
            "supported_profiles": list(VALID_RUNTIME_PROFILES),
            "ai_evaluation": {
                "ai_engine": ai_plan.ai_engine,
                "model_used": ai_plan.model_used,
                "external_network_call": ai_plan.external_network_call,
                "require_external_llm": ai_plan.require_external_llm,
                "strict_error": ai_plan.strict_error,
            },
            "x_lookup": {
                "source_mode": x_lookup_plan.source_mode,
                "base_url": x_lookup_plan.base_url,
                "bearer_token_configured": bool(x_lookup_plan.bearer_token),
                "external_network_call": x_lookup_plan.external_network_call,
                "strict_error": x_lookup_plan.strict_error,
            },
            "dm_dispatch": {
                "default_dispatch_mode": settings.DISPATCH_MODE,
                "dispatch_execution": dm_plan.dispatch_execution,
                "oauth_10a_configured": cls.has_full_x_oauth1_credentials(),
                "missing_oauth_keys": cls.get_missing_x_oauth1_keys(),
                "live_x_dry_run": settings.LIVE_X_DRY_RUN,
                "allowed_test_handles": settings.ALLOWED_TEST_HANDLES,
                "external_network_call": dm_plan.external_network_call,
                "strict_error": dm_plan.strict_error,
            },
            "live_production_readiness": {
                "ready": len(missing_for_live) == 0,
                "missing_requirements": missing_for_live,
            },
        }

