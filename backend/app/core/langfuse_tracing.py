"""
SDK-First Langfuse Distributed Tracing Wrapper (`backend/app/core/langfuse_tracing.py`).

Supports both Langfuse Python SDK v3/v5 (`from langfuse import observe, get_client`)
and legacy v2 (`from langfuse.decorators import observe, langfuse_context`).

When configured with valid `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` (and not locked to
`OFFLINE_MOCK`), traces, token usage, costs, and evaluation scores are automatically sent
to your Langfuse Dashboard (`https://cloud.langfuse.com` or `https://us.cloud.langfuse.com`).

When running in `OFFLINE_MOCK` ($0 pytest / Playwright E2E) or when Langfuse keys are unset,
operates in zero-network `no-op` mode while keeping an in-memory 4-Span snapshot for local
inspection and CLI verification.
"""

from contextvars import ContextVar
from functools import wraps
import os
import time
from typing import Any, Callable, Dict, List, Optional

from backend.app.core.config import settings
from backend.app.core.runtime_gateway import RuntimeGateway

_LANGFUSE_SDK_MODE: Optional[str] = None
_sdk_observe: Any = None
_sdk_context: Any = None
_sdk_get_client: Any = None

try:
    # Langfuse SDK v3 / v4 / v5+
    from langfuse import observe as _v5_observe, get_client as _v5_get_client

    _sdk_observe = _v5_observe
    _sdk_get_client = _v5_get_client
    _LANGFUSE_SDK_MODE = "v5"
    HAS_LANGFUSE_SDK = True
except Exception:
    try:
        # Langfuse SDK v2.x
        from langfuse.decorators import observe as _v2_observe, langfuse_context as _v2_context

        _sdk_observe = _v2_observe
        _sdk_context = _v2_context
        _LANGFUSE_SDK_MODE = "v2"
        HAS_LANGFUSE_SDK = True
    except Exception:
        HAS_LANGFUSE_SDK = False

_active_trace_spans: ContextVar[Optional[List[Dict[str, Any]]]] = ContextVar(
    "_active_trace_spans", default=None
)
_active_trace_scores: ContextVar[Optional[List[Dict[str, Any]]]] = ContextVar(
    "_active_trace_scores", default=None
)
_active_observation_meta: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "_active_observation_meta", default=None
)
_active_observation_type: ContextVar[str] = ContextVar("_active_observation_type", default="span")

_LAST_TRACES_BY_HANDLE: Dict[str, Dict[str, Any]] = {}


def _sync_langfuse_env_vars() -> None:
    """Ensure os.environ mirrors settings so Langfuse v5 get_client() uses configured credentials."""
    if getattr(settings, "LANGFUSE_PUBLIC_KEY", "").strip():
        os.environ["LANGFUSE_PUBLIC_KEY"] = settings.LANGFUSE_PUBLIC_KEY.strip()
    if getattr(settings, "LANGFUSE_SECRET_KEY", "").strip():
        os.environ["LANGFUSE_SECRET_KEY"] = settings.LANGFUSE_SECRET_KEY.strip()
    if getattr(settings, "LANGFUSE_HOST", "").strip():
        os.environ["LANGFUSE_HOST"] = settings.LANGFUSE_HOST.strip()


def update_current_observation(
    model: Optional[str] = None,
    usage: Optional[Dict[str, int]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    cost_usd: Optional[float] = None,
) -> None:
    """Forward observation metadata (model, input/output tokens, cost) to Langfuse SDK & local snapshot."""
    cur = _active_observation_meta.get()
    if cur is not None:
        if model:
            cur["model"] = model
        if usage:
            cur["usage"] = usage
        if metadata:
            cur.setdefault("metadata", {}).update(metadata)
        if cost_usd is not None:
            cur["cost_usd"] = cost_usd

    if not (HAS_LANGFUSE_SDK and RuntimeGateway.is_langfuse_enabled()):
        return

    _sync_langfuse_env_vars()
    try:
        if _LANGFUSE_SDK_MODE == "v5" and _sdk_get_client is not None:
            client = _sdk_get_client()
            obs_type = _active_observation_type.get()
            if obs_type == "generation":
                usage_details = (
                    {k: int(v) for k, v in usage.items() if isinstance(v, (int, float))}
                    if usage
                    else None
                )
                cost_details = {"total": float(cost_usd)} if cost_usd is not None else None
                client.update_current_generation(
                    model=model,
                    usage_details=usage_details,
                    cost_details=cost_details,
                    metadata=metadata,
                )
            else:
                client.update_current_span(metadata=metadata)
        elif _LANGFUSE_SDK_MODE == "v2" and _sdk_context is not None:
            kwargs: Dict[str, Any] = {}
            if model:
                kwargs["model"] = model
            if usage:
                kwargs["usage"] = usage
            if metadata:
                kwargs["metadata"] = metadata
            if kwargs:
                _sdk_context.update_current_observation(**kwargs)
    except Exception:
        pass


def score_current_trace(name: str, value: float, comment: Optional[str] = None) -> None:
    """Push an evaluation score (`verify_gate_2_verbatim`, `llm_judge_dm_pass`, etc.) to Langfuse SDK."""
    scores = _active_trace_scores.get()
    if scores is not None:
        scores.append({"name": name, "value": value, "comment": comment})

    if not (HAS_LANGFUSE_SDK and RuntimeGateway.is_langfuse_enabled()):
        return

    _sync_langfuse_env_vars()
    try:
        if _LANGFUSE_SDK_MODE == "v5" and _sdk_get_client is not None:
            _sdk_get_client().score_current_trace(name=name, value=float(value), comment=comment)
        elif _LANGFUSE_SDK_MODE == "v2" and _sdk_context is not None:
            _sdk_context.score_current_trace(name=name, value=value, comment=comment)
    except Exception:
        pass


def flush_langfuse() -> None:
    """Flush pending Langfuse SDK events to Langfuse Cloud / self-hosted server."""
    if not (HAS_LANGFUSE_SDK and RuntimeGateway.is_langfuse_enabled()):
        return

    _sync_langfuse_env_vars()
    try:
        if _LANGFUSE_SDK_MODE == "v5" and _sdk_get_client is not None:
            _sdk_get_client().flush()
        elif _LANGFUSE_SDK_MODE == "v2" and _sdk_context is not None:
            _sdk_context.flush()
    except Exception:
        pass


def check_langfuse_auth() -> Dict[str, Any]:
    """Verify live Langfuse credentials against configured LANGFUSE_HOST."""
    if not HAS_LANGFUSE_SDK:
        return {"ok": False, "detail": "langfuse package is not installed in Python environment."}
    if not RuntimeGateway.is_langfuse_enabled():
        return {"ok": False, "detail": "LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY unset or OFFLINE_MOCK."}
    _sync_langfuse_env_vars()
    try:
        if _LANGFUSE_SDK_MODE == "v5" and _sdk_get_client is not None:
            ok = bool(_sdk_get_client().auth_check())
            return {"ok": ok, "sdk_mode": "v5", "host": settings.LANGFUSE_HOST}
        return {"ok": True, "sdk_mode": _LANGFUSE_SDK_MODE, "host": settings.LANGFUSE_HOST}
    except Exception as exc:
        return {"ok": False, "sdk_mode": _LANGFUSE_SDK_MODE, "host": settings.LANGFUSE_HOST, "detail": str(exc)}


def observe(name: Optional[str] = None, as_type: Optional[str] = None) -> Callable:
    """
    Drop-in `@observe(name=..., as_type=...)` decorator powered by the `langfuse` Python SDK (v5/v2).
    - When `RuntimeGateway.is_langfuse_enabled()` is True, delegates directly to Langfuse SDK `@observe`.
    - Always captures lightweight span timing & token/score metadata for local inspection and Gate 4 verification.
    """

    def decorator(func: Callable) -> Callable:
        span_name = name or func.__name__
        sdk_wrapped = None
        if HAS_LANGFUSE_SDK and _sdk_observe is not None:
            try:
                sdk_kwargs: Dict[str, Any] = {"name": span_name}
                if as_type:
                    sdk_kwargs["as_type"] = as_type
                sdk_wrapped = _sdk_observe(**sdk_kwargs)(func)
            except Exception:
                sdk_wrapped = None

        @wraps(func)
        def wrapper(*args, **kwargs):
            is_root = _active_trace_spans.get() is None
            if is_root:
                spans_token = _active_trace_spans.set([])
                scores_token = _active_trace_scores.set([])
            else:
                spans_token = None
                scores_token = None

            obs_meta: Dict[str, Any] = {}
            meta_token = _active_observation_meta.set(obs_meta)
            type_token = _active_observation_type.set(as_type or "span")
            t0 = time.perf_counter()
            error_str: Optional[str] = None
            try:
                if sdk_wrapped is not None and RuntimeGateway.is_langfuse_enabled():
                    _sync_langfuse_env_vars()
                    result = sdk_wrapped(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                return result
            except Exception as exc:
                error_str = str(exc)
                raise
            finally:
                elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
                _active_observation_meta.reset(meta_token)
                _active_observation_type.reset(type_token)

                spans_list = _active_trace_spans.get()
                if spans_list is not None and not is_root:
                    spans_list.append(
                        {
                            "name": span_name,
                            "type": as_type or "span",
                            "latency_ms": elapsed_ms,
                            "model": obs_meta.get("model"),
                            "usage": obs_meta.get("usage"),
                            "cost_usd": obs_meta.get("cost_usd", 0.0),
                            "metadata": obs_meta.get("metadata", {}),
                            "status": "ERROR" if error_str else "SUCCESS",
                        }
                    )

                if is_root:
                    collected_spans = list(_active_trace_spans.get() or [])
                    collected_scores = list(_active_trace_scores.get() or [])
                    if spans_token is not None:
                        _active_trace_spans.reset(spans_token)
                    if scores_token is not None:
                        _active_trace_scores.reset(scores_token)

                    handle = obs_meta.get("metadata", {}).get("handle")
                    if not handle and args:
                        first_arg = args[0]
                        handle = getattr(first_arg, "handle", None)
                    if handle:
                        h_key = str(handle).lower()
                        total_cost = round(
                            sum(float(s.get("cost_usd") or 0.0) for s in collected_spans), 6
                        )
                        existing_trace = _LAST_TRACES_BY_HANDLE.get(h_key)
                        if (
                            existing_trace
                            and len(existing_trace.get("spans") or []) >= 2
                            and len(collected_spans) == 0
                        ):
                            existing_trace["scores"].extend(collected_scores)
                            existing_trace["spans"].append(
                                {
                                    "name": span_name,
                                    "type": as_type or "span",
                                    "latency_ms": elapsed_ms,
                                    "model": obs_meta.get("model"),
                                    "usage": obs_meta.get("usage"),
                                    "cost_usd": obs_meta.get("cost_usd", 0.0),
                                    "metadata": obs_meta.get("metadata", {}),
                                    "status": "ERROR" if error_str else "SUCCESS",
                                }
                            )
                        else:
                            _LAST_TRACES_BY_HANDLE[h_key] = {
                                "trace_name": span_name,
                                "handle": h_key,
                                "sdk": "langfuse",
                                "sdk_version_mode": _LANGFUSE_SDK_MODE,
                                "langfuse_cloud_enabled": RuntimeGateway.is_langfuse_enabled(),
                                "langfuse_host": settings.LANGFUSE_HOST,
                                "total_latency_ms": elapsed_ms,
                                "total_cost_usd": total_cost,
                                "status": "ERROR" if error_str else "SUCCESS",
                                "spans": collected_spans,
                                "scores": collected_scores,
                            }

        return wrapper

    return decorator


def get_last_candidate_trace(handle: str) -> Optional[Dict[str, Any]]:
    """Retrieve the most recent 4-Span Langfuse trace snapshot recorded for a candidate handle."""
    return _LAST_TRACES_BY_HANDLE.get((handle or "").strip().lstrip("@").lower())
