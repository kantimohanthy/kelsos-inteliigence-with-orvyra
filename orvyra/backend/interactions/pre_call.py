from __future__ import annotations
import datetime
from storage.models import IntelligencePacket, ProspectInput, ProductContext
from storage.memory import memory
from ingestion.crm import get_prior_interactions
from intelligence.pipeline import build_intelligence_pipeline


async def run_pre_call(
    prospect: ProspectInput,
    objective: str,
    product: str = "Klesos",
    product_context: ProductContext | None = None,
    role_hint: str | None = None,
    force_refresh: bool = False,
    prospect_id_override: str | None = None,
) -> IntelligencePacket:
    now = datetime.datetime.now(datetime.timezone.utc)
    existing = memory.find_by_identity(prospect.email, prospect.linkedin_url)

    if existing and not force_refresh:
        is_fresh = existing.valid_until is None or existing.valid_until > now
        if is_fresh:
            return existing

    prospect_id = prospect_id_override or (existing.prospect_id if existing else None)
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



