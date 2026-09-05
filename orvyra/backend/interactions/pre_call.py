from __future__ import annotations
from storage.models import IntelligencePacket, ProspectInput, ProductContext
from storage.memory import memory
from ingestion.crm import get_prior_interactions
from intelligence.pipeline import build_intelligence_pipeline


async def run_pre_call(
    prospect: ProspectInput,
    objective: str,
    product: str,
    product_context: ProductContext | None = None,
    role_hint: str | None = None
) -> IntelligencePacket:
    existing = memory.find_by_identity(prospect.email, prospect.linkedin_url)
    prospect_id = existing.prospect_id if existing else None
    prior_interactions = get_prior_interactions(prospect_id) if prospect_id else []

    packet = await build_intelligence_pipeline(
        prospect=prospect,
        objective=objective,
        product_name=product,
        product_context=product_context,
        role_hint=role_hint,
        prior_interactions=prior_interactions,
        prospect_id_override=prospect_id,
    )

    memory.save_packet(packet)
    return packet


