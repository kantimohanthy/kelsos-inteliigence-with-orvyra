"""
Intelligence Pipeline Module — Master orchestrator for pre-call intelligence generation.

Orchestrates:
1. Identity resolution
2. Safe multi-page crawling
3. Atomic claim extraction with provenance
4. Company profile assembly
5. Person context & priority inference
6. Deterministic opportunity evaluation
7. Non-scripted conversation strategy formulation
8. IntelligencePacket assembly & schema validation
"""

from __future__ import annotations
import datetime
from storage.models import (
    IntelligencePacket, ProspectInput, ProductContext, CompanyContext,
    PersonContext, Claim, ClaimType, EvidenceSource, SourceDocument, new_id
)
from ingestion.crawler import crawl_company
from intelligence.enrichment import resolve_identity
from intelligence.extraction import extract_atomic_claims
from intelligence.person import infer_person_context
from intelligence.opportunity import evaluate_opportunity
from intelligence.critic import critique_opportunity
from intelligence.strategy import build_strategy

DEFAULT_PRODUCT_CONTEXT = ProductContext(
    name="Klesos",
    description="AI voice agent that conducts outbound sales conversations",
    target_customers=["Sales Teams", "B2B SaaS", "Outbound SDRs", "Revenue Leaders", "Sales Ops"],
    value_propositions=[
        "Automate outbound phone sales conversations",
        "Qualify prospects and book meetings automatically",
        "Compound prospect memory across calls"
    ]
)


def build_company_profile(
    claims: list[Claim],
    company_name: str | None,
    documents: list[SourceDocument]
) -> CompanyContext:
    industry: str | None = None
    recent_signals: list[str] = []

    # 1. First pass: look for real FACT claims describing industry/domain (excluding title tags)
    for c in claims:
        if c.type == ClaimType.FACT and not c.claim.startswith("Company identity title"):
            claim_lower = c.claim.lower()
            if any(kw in claim_lower for kw in ["industry", "financial infrastructure", "payments", "fintech", "saas", "software", "healthcare", "logistics", "e-commerce", "platform"]):
                industry = c.claim
                break

    # 2. Second pass: fallback to any non-title claim with industry keywords if no fact claim matched
    if not industry:
        for c in claims:
            if not c.claim.startswith("Company identity title"):
                claim_lower = c.claim.lower()
                if any(kw in claim_lower for kw in ["saas", "software", "fintech", "payments", "financial infrastructure", "healthcare", "logistics", "ai", "technology"]):
                    industry = c.claim
                    break

    for c in claims:
        claim_lower = c.claim.lower()
        if any(kw in claim_lower for kw in ["hiring", "expansion", "growth", "funding", "careers", "signal", "agentic"]):
            if not c.claim.startswith("Company identity title"):
                recent_signals.append(c.claim)

    successful_docs = [d for d in documents if d.status == "success"]
    if successful_docs:
        recent_signals.insert(0, f"Successfully crawled {len(successful_docs)} pages from company website")
    elif documents:
        err_msg = documents[0].error or "Company site unreachable at crawl time"
        recent_signals.append(f"Company site crawl issue: {err_msg}")
    else:
        recent_signals.append("No company URL provided — enrichment limited to prospect input")

    return CompanyContext(
        name=company_name,
        industry=industry or "B2B Software & Services",
        business_model="B2B",
        estimated_size=None,
        recent_signals=recent_signals[:5],
    )


async def build_intelligence_pipeline(
    prospect: ProspectInput,
    objective: str,
    product_name: str = "Klesos",
    product_context: ProductContext | None = None,
    role_hint: str | None = None,
    prior_interactions: list[dict] | None = None,
    prospect_id_override: str | None = None,
) -> IntelligencePacket:
    if not prospect.name or not prospect.name.strip():
        prospect.name = prospect.get_effective_name()

    # 1. Identity Resolution
    identity = resolve_identity(prospect)

    # 2. Multi-page Crawling
    documents = await crawl_company(prospect.company_url, max_pages=10)

    # 3. Claims Extraction
    claims = await extract_atomic_claims(documents)

    # 4. Company Profile Assembly
    company = build_company_profile(claims, prospect.company, documents)

    # 5. Person Context Inference
    person = infer_person_context(role_hint, company, prior_interactions or [])

    # 6. Product Context Setup
    active_product = product_context or DEFAULT_PRODUCT_CONTEXT
    if product_name and not product_context:
        active_product.name = product_name

    # 7. Opportunity Reasoning & Adversarial Critic Pass
    raw_opportunity = evaluate_opportunity(company, person, active_product, claims)
    opportunity = critique_opportunity(raw_opportunity, claims, prior_interactions or [])

    # 8. Conversation Strategy Formulation
    strategy = build_strategy(opportunity, claims, objective)

    # 9. Evidence Sources & Warnings Aggregation
    sources: list[EvidenceSource] = []
    warnings: list[str] = []

    if not prospect.company_url:
        warnings.append("No company URL provided — enrichment limited to prospect input")

    for doc in documents:

        if doc.status == "success":
            sources.append(
                EvidenceSource(
                    source_id=doc.doc_id,
                    url=doc.url,
                    source_type="website_scrape",
                    excerpt=f"Crawled page title: {doc.title or 'Untitled'}",
                    confidence=0.9,
                )
            )
        else:
            warnings.append(f"Page fetch notice for {doc.url}: {doc.error or doc.status}")

    sources.append(
        EvidenceSource(
            url=prospect.linkedin_url,
            source_type="prospect_input",
            excerpt=f"Prospect: {prospect.name}, Role Hint: {role_hint or 'Unspecified'}",
            confidence=1.0,
        )
    )

    if identity.get("needs_review") or identity.get("status") == "needs_review":
        status = "needs_review"
        for conf in identity.get("conflicts", []):
            warnings.append(f"Identity conflict: {conf}")
    elif not opportunity.pursue:
        status = "needs_review"
    elif any(d.status != "success" for d in documents) or not prospect.company_url:
        status = "partial"
    else:
        status = "ready"
    now = datetime.datetime.now(datetime.timezone.utc)
    valid_until = now + datetime.timedelta(days=7)

    return IntelligencePacket(
        **({"prospect_id": prospect_id_override} if prospect_id_override else {}),
        schema_version="1.0.0",
        status=status,
        valid_until=valid_until,
        warnings=warnings,
        sources=sources,
        identity=prospect,
        company_context=company,
        person_context=person,
        facts=claims,
        signals=company.recent_signals,
        opportunity=opportunity,
        conversation_strategy=strategy,
        previous_interactions=prior_interactions or [],
        created_at=now,
    )

