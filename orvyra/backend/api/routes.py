from __future__ import annotations
import datetime
import logging
import traceback
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel

from storage.models import ProspectInput, IntelligencePacket, PostCallInput, CallAnalysis, ProductContext, new_id
from storage.memory import memory
from storage.jobs import jobs
from interactions.pre_call import run_pre_call
from interactions.post_call import run_post_call
from api.auth import require_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/intelligence", tags=["intelligence"], dependencies=[Depends(require_api_key)])
root_router = APIRouter(prefix="/v1", tags=["enrichment"], dependencies=[Depends(require_api_key)])


class PreCallRequest(BaseModel):
    prospect: ProspectInput
    objective: str
    product: str = "Klesos"
    product_context: ProductContext | None = None
    role_hint: str | None = None


class JobStatusResponse(BaseModel):
    job_id: str
    prospect_id: str
    status: str
    error: str | None = None


async def _run_enrichment_job(job_id: str, req: PreCallRequest, prospect_id_override: str | None = None) -> None:
    jobs.update_status(job_id, "enriching")
    try:
        packet = await run_pre_call(
            prospect=req.prospect,
            objective=req.objective,
            product=req.product,
            product_context=req.product_context,
            role_hint=req.role_hint,
            force_refresh=True,
        )
        if prospect_id_override and packet.prospect_id != prospect_id_override:
            packet.prospect_id = prospect_id_override
            memory.save_packet(packet)

        facts_count = len(packet.facts)
        has_industry = bool(packet.company_context and packet.company_context.industry)
        
        job_status = packet.status
        jobs.update_status(job_id, job_status)
    except Exception as e:
        logger.error(f"Background enrichment job '{job_id}' failed: {e}\n{traceback.format_exc()}")
        jobs.update_status(job_id, "failed", error=str(e))


@router.post("/pre-call", response_model=IntelligencePacket)
async def pre_call(req: PreCallRequest) -> IntelligencePacket:
    """Klesos -> Orvyra, before a call. Returns the full IntelligencePacket:
    company/person context, opportunity hypothesis, and conversation strategy."""
    try:
        return await run_pre_call(
            prospect=req.prospect,
            objective=req.objective,
            product=req.product,
            product_context=req.product_context,
            role_hint=req.role_hint,
        )
    except Exception as e:
        logger.error(f"Error generating pre-call packet: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate intelligence packet: {str(e)}"
        )



@root_router.post("/prospects/enrich", response_model=list[JobStatusResponse])
@router.post("/prospects/enrich", response_model=list[JobStatusResponse])
async def enrich_prospects(leads: list[PreCallRequest], background_tasks: BackgroundTasks) -> list[JobStatusResponse]:
    """Pre-warm intelligence packets asynchronously for a batch of leads."""
    now = datetime.datetime.now(datetime.timezone.utc)
    responses: list[JobStatusResponse] = []

    for lead in leads:
        existing = memory.find_by_identity(lead.prospect.email, lead.prospect.linkedin_url)
        if existing:
            is_fresh = existing.valid_until is None or existing.valid_until > now
            if is_fresh:
                existing_job = jobs.find_by_prospect(existing.prospect_id)
                job_status = existing_job.status if existing_job else ("ready" if existing.opportunity.pursue else "partial")
                job_id = existing_job.job_id if existing_job else new_id("job")
                if not existing_job:
                    jobs.create(prospect_id=existing.prospect_id, job_id=job_id, status=job_status)
                responses.append(
                    JobStatusResponse(
                        job_id=job_id,
                        prospect_id=existing.prospect_id,
                        status=job_status,
                        error=existing_job.error if existing_job else None,
                    )
                )
                continue


        prospect_id = existing.prospect_id if existing else new_id("prospect")
        job = jobs.create(prospect_id=prospect_id, status="pending")
        background_tasks.add_task(_run_enrichment_job, job.job_id, lead, prospect_id)
        responses.append(
            JobStatusResponse(
                job_id=job.job_id,
                prospect_id=prospect_id,
                status="pending",
                error=None,
            )
        )

    return responses


@root_router.get("/enrichment-jobs/{job_id}", response_model=JobStatusResponse)
@router.get("/enrichment-jobs/{job_id}", response_model=JobStatusResponse)
def get_enrichment_job(job_id: str) -> JobStatusResponse:
    """Check current status of a background enrichment job."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Enrichment job '{job_id}' not found")
    return JobStatusResponse(
        job_id=job.job_id,
        prospect_id=job.prospect_id,
        status=job.status,
        error=job.error,
    )


@router.post("/prospects/{prospect_id}/refresh", response_model=JobStatusResponse)
async def refresh_prospect(prospect_id: str, background_tasks: BackgroundTasks) -> JobStatusResponse:
    """Force re-enrichment of a prospect ignoring valid_until freshness."""
    packet = memory.get_packet(prospect_id)
    if not packet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prospect '{prospect_id}' not found")

    lead = PreCallRequest(
        prospect=packet.identity,
        objective="Refreshed pre-call intelligence",
    )
    job = jobs.create(prospect_id=prospect_id, status="pending")
    background_tasks.add_task(_run_enrichment_job, job.job_id, lead, prospect_id)
    return JobStatusResponse(
        job_id=job.job_id,
        prospect_id=prospect_id,
        status="pending",
        error=None,
    )


@router.post("/post-call", response_model=CallAnalysis)
def post_call(payload: PostCallInput) -> CallAnalysis:
    """Klesos -> Orvyra, after a call. Returns analysis + next best action,
    and updates the prospect's intelligence memory for the next call."""
    return run_post_call(payload)


@router.get("/prospects", response_model=list[IntelligencePacket])
def list_prospects() -> list[IntelligencePacket]:
    """Operator Dashboard -> Orvyra. List all prospect intelligence packets, newest first."""
    return memory.list_packets()


class DecisionOverrideRequest(BaseModel):
    pursue: bool
    reason: str


class DecisionOverrideResponse(BaseModel):
    override_id: str
    prospect_id: str
    packet_id: str | None = None
    pursue: bool
    reason: str
    operator_id: str
    created_at: str | None = None


@router.get("/prospects/{prospect_id}", response_model=IntelligencePacket)
def get_prospect(prospect_id: str) -> IntelligencePacket:
    """Operator Dashboard -> Orvyra. Get a single prospect intelligence packet by prospect_id."""
    packet = memory.get_packet(prospect_id)
    if not packet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prospect packet '{prospect_id}' not found")
    return packet


@root_router.patch("/prospects/{prospect_id}/decision", response_model=DecisionOverrideResponse)
@router.patch("/prospects/{prospect_id}/decision", response_model=DecisionOverrideResponse)
def override_decision(prospect_id: str, req: DecisionOverrideRequest) -> DecisionOverrideResponse:
    """Operator Dashboard / Klesos -> Orvyra. Override automated pursue decision,
    persisting record in operator_overrides without mutating original packet recommendation."""
    try:
        data = memory.save_override(prospect_id=prospect_id, pursue=req.pursue, reason=req.reason)
        return DecisionOverrideResponse(**data)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error(f"Error saving decision override for '{prospect_id}': {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@root_router.get("/prospects/{prospect_id}/override", response_model=DecisionOverrideResponse | None)
@router.get("/prospects/{prospect_id}/override", response_model=DecisionOverrideResponse | None)
def get_prospect_override(prospect_id: str) -> DecisionOverrideResponse | None:
    data = memory.get_override(prospect_id)
    if not data:
        return None
    return DecisionOverrideResponse(**data)


@router.get("/prospects/{prospect_id}/history", response_model=list[CallAnalysis])
def get_prospect_history(prospect_id: str) -> list[CallAnalysis]:
    """Operator Dashboard -> Orvyra. Get call history and analyses for a given prospect."""
    return memory.get_history(prospect_id)


@router.get("/calls", response_model=list[CallAnalysis])
def list_calls() -> list[CallAnalysis]:
    """Operator Dashboard -> Orvyra. List all post-call analyses across all prospects."""
    return memory.list_calls()


