from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from storage.models import ProspectInput, IntelligencePacket, PostCallInput, CallAnalysis, ProductContext
from storage.memory import memory
from interactions.pre_call import run_pre_call
from interactions.post_call import run_post_call
from api.auth import require_api_key

router = APIRouter(prefix="/v1/intelligence", tags=["intelligence"], dependencies=[Depends(require_api_key)])


class PreCallRequest(BaseModel):
    prospect: ProspectInput
    objective: str
    product: str = "Klesos"
    product_context: ProductContext | None = None
    role_hint: str | None = None


@router.post("/pre-call", response_model=IntelligencePacket)
async def pre_call(req: PreCallRequest) -> IntelligencePacket:
    """Klesos -> Orvyra, before a call. Returns the full IntelligencePacket:
    company/person context, opportunity hypothesis, and conversation strategy."""
    return await run_pre_call(
        prospect=req.prospect,
        objective=req.objective,
        product=req.product,
        product_context=req.product_context,
        role_hint=req.role_hint,
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


@router.get("/prospects/{prospect_id}", response_model=IntelligencePacket)
def get_prospect(prospect_id: str) -> IntelligencePacket:
    """Operator Dashboard -> Orvyra. Get a single prospect intelligence packet by prospect_id."""
    packet = memory.get_packet(prospect_id)
    if not packet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prospect packet '{prospect_id}' not found")
    return packet


@router.get("/prospects/{prospect_id}/history", response_model=list[CallAnalysis])
def get_prospect_history(prospect_id: str) -> list[CallAnalysis]:
    """Operator Dashboard -> Orvyra. Get call history and analyses for a given prospect."""
    return memory.get_history(prospect_id)


@router.get("/calls", response_model=list[CallAnalysis])
def list_calls() -> list[CallAnalysis]:
    """Operator Dashboard -> Orvyra. List all post-call analyses across all prospects."""
    return memory.list_calls()

