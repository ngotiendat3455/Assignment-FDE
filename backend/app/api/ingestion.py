from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
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


@router.post("/preflight", response_model=CsvPreflightResponse)
def check_csv_preflight(payload: CsvPreflightRequest) -> CsvPreflightResponse:
    """Pre-flight validation & 5-row preview for Tab 2 CSV Upload."""
    result = preflight_csv_check(payload.csv_content)
    return CsvPreflightResponse(**result)


@router.post("/csv", response_model=IngestionAuditReport)
def upload_csv_batch(
    payload: CsvIngestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> IngestionAuditReport:
    """Parse and ingest a custom CSV batch for Tab 2."""
    try:
        parsed_rows = parse_csv_content(payload.csv_content)
        report = ingest_candidate_batch(
            db,
            parsed_rows,
            source_label="CSV_UPLOAD",
            default_segment=payload.default_segment,
            skip_ledger_collisions=payload.skip_ledger_collisions,
        )
        if payload.queue_ai_enabled:
            background_tasks.add_task(process_pending_jobs, db, "AI_EVALUATE")
        return IngestionAuditReport(**report)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
def download_csv_template() -> str:
    """Return a clean CSV template for associates."""
    return SAMPLE_CSV_TEMPLATE

