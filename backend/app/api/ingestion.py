from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.runtime_gateway import RuntimeGateway
from backend.app.core.security import get_current_user
from backend.app.schemas.candidate import (
    CandidateCreate,
    SeedIngestRequest,
    CsvPreflightRequest,
    CsvPreflightResponse,
    CsvIngestRequest,
    IngestionAuditReport,
    LiveXLookupResponse,
)
from backend.app.services.ingestion import (
    XApiLookupError,
    ingest_seed_pack,
    preflight_csv_check,
    parse_csv_content,
    ingest_candidate_batch,
    lookup_x_handle,
)
from backend.app.services.queue_worker import process_pending_jobs

router = APIRouter(
    prefix="/ingestion",
    tags=["Ingestion"],
    dependencies=[Depends(get_current_user)],
)

SAMPLE_CSV_TEMPLATE = """handle,name,location,bio,recent_tweets,can_dm,segment
@minh_quant,Minh Nguyen,"Hanoi, Vietnam","Founder @TensorEdgeVN. Ultra-fast C++/CUDA/ARM LLM inference engine.","[2026-11-08] Just open-sourced our AWQ-W4A8 speculative decoding kernel for L40S GPUs.",true,SEG-02: LLM Inference & AI Infra
@dr_somchai_ai,Dr. Somchai Charoen,"Bangkok, Thailand","CEO @SiamAgriBot | Autonomous ROS2 laser-weeding rovers.","[2026-11-07] Field trial results: 3 autonomous rovers ran 140 hours continuously in 38C mud conditions.",true,SEG-01: SEA Embodied AI & Robotics
"""

LIVE_X_HEADER_TEMPLATE = "handle,segment\n"
LIVE_MANUAL_HEADER_TEMPLATE = "handle,name,location,bio,recent_tweets,can_dm,segment\n"


@router.post("/seed", response_model=IngestionAuditReport)
def load_seed_pack(
    background_tasks: BackgroundTasks,
    payload: SeedIngestRequest = SeedIngestRequest(),
    db: Session = Depends(get_db),
) -> IngestionAuditReport:
    """1-Click Seed Pack ingestion for Tab 1 (20 SEA AI/Robotics profiles)."""
    try:
        report = ingest_seed_pack(db, default_segment=payload.segment)
        background_tasks.add_task(process_pending_jobs, db, "AI_EVALUATE")
        return IngestionAuditReport(**report)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/preflight",
    response_model=CsvPreflightResponse,
    response_model_exclude_unset=True,
)
def check_csv_preflight(
    payload: CsvPreflightRequest,
    db: Session = Depends(get_db),
) -> CsvPreflightResponse:
    """Pre-flight validation, $0 dedup preview & optional 1-call X profile preview for Tab 2."""
    try:
        result = preflight_csv_check(
            payload.csv_content,
            verify_with_x_api=payload.verify_with_x_api,
            fetch_x_preview=payload.fetch_x_preview,
            db=db,
        )
        return CsvPreflightResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except XApiLookupError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/csv", response_model=IngestionAuditReport)
def upload_csv_batch(
    payload: CsvIngestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> IngestionAuditReport:
    """Parse and ingest a custom CSV batch for Tab 2."""
    try:
        parsed_rows = parse_csv_content(
            payload.csv_content,
            verify_with_x_api=payload.verify_with_x_api,
        )
        report = ingest_candidate_batch(
            db,
            parsed_rows,
            source_label="CSV_X_SYNC" if payload.verify_with_x_api else "CSV_UPLOAD",
            default_segment=payload.default_segment,
            skip_ledger_collisions=payload.skip_ledger_collisions,
            verify_with_x_api=payload.verify_with_x_api,
        )
        if payload.queue_ai_enabled:
            background_tasks.add_task(process_pending_jobs, db, "AI_EVALUATE")
        return IngestionAuditReport(**report)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except XApiLookupError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/x-lookup", response_model=LiveXLookupResponse)
def lookup_handle_on_x(
    handle: str = Query(..., description="X handle or profile URL"),
    db: Session = Depends(get_db),
) -> LiveXLookupResponse:
    """Lookup X profile via configured X API v2 base URL (real X or local simulator)."""
    try:
        result = lookup_x_handle(db, handle)
        return LiveXLookupResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except XApiLookupError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/single", response_model=IngestionAuditReport)
def ingest_single_profile(
    payload: CandidateCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> IngestionAuditReport:
    """Ingest a single looked-up X profile into the AI evaluation queue (Tab 3)."""
    record = payload.model_dump()
    report = ingest_candidate_batch(
        db,
        [record],
        source_label="LIVE_X_LOOKUP",
        default_segment=payload.segment,
    )
    background_tasks.add_task(process_pending_jobs, db, "AI_EVALUATE")
    return IngestionAuditReport(**report)


@router.get("/template", response_class=PlainTextResponse)
def download_csv_template(
    verify_with_x_api: Optional[bool] = Query(
        default=None,
        description="Optional override for Live Production header-only template columns.",
    ),
) -> PlainTextResponse:
    """
    Return an environment-appropriate CSV template:
    - LIVE_PRODUCTION: header-only blank CSV (no mock handles, protects X API credits).
    - OFFLINE_MOCK / HYBRID_AUTO: sample simulator CSV rows for instant testing.
    """
    if RuntimeGateway.get_active_profile() == "LIVE_PRODUCTION":
        use_handle_only = True if verify_with_x_api is None else verify_with_x_api
        content = LIVE_X_HEADER_TEMPLATE if use_handle_only else LIVE_MANUAL_HEADER_TEMPLATE
        filename = (
            "genai_fund_live_x_template.csv"
            if use_handle_only
            else "genai_fund_live_manual_template.csv"
        )
    else:
        content = SAMPLE_CSV_TEMPLATE
        filename = "genai_fund_sample_candidates_mock.csv"

    return PlainTextResponse(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

