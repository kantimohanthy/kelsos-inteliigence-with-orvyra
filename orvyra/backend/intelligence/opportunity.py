"""
Opportunity Reasoning Module — Deterministic 4-component scoring & prose generation.

Rules:
- Computes four deterministic sub-scores: company_fit, persona_fit, timing_fit, evidence_coverage.
- Overall score = weighted combination.
- pursue = overall >= pursue_threshold() (imported from confidence.py).
- LLM (if configured) generates ONLY the prose explanation from already-scored claims, never setting the numbers.
"""

from __future__ import annotations
from storage.models import Opportunity, CompanyContext, PersonContext, ProductContext, Claim, ClaimType
from .confidence import pursue_threshold
from .llm import complete_json, has_llm


def evaluate_opportunity(
    company: CompanyContext,
    person: PersonContext,
    product: ProductContext,
    claims: list[Claim]
) -> Opportunity:
    # 1. Deterministic Sub-Scoring
    company_fit = _compute_company_fit(company, product, claims)
    persona_fit = _compute_persona_fit(person)
    timing_fit = _compute_timing_fit(claims)
    evidence_coverage = _compute_evidence_coverage(claims)

    # Weighted combination: 35% company fit, 25% persona fit, 20% timing fit, 20% evidence coverage
    overall = (0.35 * company_fit) + (0.25 * persona_fit) + (0.20 * timing_fit) + (0.20 * evidence_coverage)
    overall = round(min(max(overall, 0.0), 1.0), 2)

    threshold = pursue_threshold()
    pursue = overall >= threshold and bool(claims or company.industry or person.role)

    # Counterevidence & Information Gaps
    counterevidence: list[str] = []
    if evidence_coverage < 0.3:
        counterevidence.append("Low evidence coverage — company site provided sparse details")
    if timing_fit < 0.2:
        counterevidence.append("No active expansion or hiring signals observed")

    # 2. Prose Generation (LLM or Deterministic Fallback)
    reason_if_not_pursue: str | None = None
    if not pursue:
        reason_if_not_pursue = (
            f"Overall fit score ({overall:.2f}) is below threshold ({threshold}). "
            f"Key factors: company_fit={company_fit:.2f}, persona_fit={persona_fit:.2f}, "
            f"timing_fit={timing_fit:.2f}, evidence_coverage={evidence_coverage:.2f}. "
            f"Insufficient signal to justify outbound dial."
        )

    if has_llm() and claims:
        prose = _generate_llm_prose(company, person, product, claims, pursue, overall)
        if prose:
            return Opportunity(
                primary_problem=prose.get("primary_problem", f"Opportunity fit score {overall} for {product.name}"),
                confidence=overall,
                value_hypothesis=prose.get("value_hypothesis"),
                likely_objections=prose.get("likely_objections", [
                    "Concern about AI call quality and brand reputation",
                    "Existing CRM integration complexity",
                    "Uncertainty around ROI and timing"
                ]),
                recommended_angle=prose.get("recommended_angle"),
                pursue=pursue,
                reason_if_not_pursue=reason_if_not_pursue if not pursue else None,
            )

    # Fallback prose (Deterministic template)
    fact_claims = [c.claim for c in claims if c.type == ClaimType.FACT]
    primary_problem = (
        f"Hypothesis for {company.name or 'Target Company'}: "
        + ("; ".join(fact_claims[:2]) if fact_claims else f"High potential relevance for {product.name}")
    )
    value_hypothesis = (
        f"{product.name} ({product.description}) can reduce manual SDR overhead "
        f"and accelerate outbound lead qualification."
    )
    recommended_angle = f"Position {product.name} as an AI co-pilot augmenting sales reps."

    return Opportunity(
        primary_problem=primary_problem if pursue else None,
        confidence=overall,
        value_hypothesis=value_hypothesis if pursue else None,
        likely_objections=[
            "Concern about AI call quality",
            "Integration with existing CRM tools",
            "Budget / priority constraints"
        ],
        recommended_angle=recommended_angle if pursue else None,
        pursue=pursue,
        reason_if_not_pursue=reason_if_not_pursue,
    )


def _compute_company_fit(company: CompanyContext, product: ProductContext, claims: list[Claim]) -> float:
    score = 0.4  # baseline
    company_text = f"{company.name or ''} {company.industry or ''} {company.business_model or ''}".lower()
    
    # Check claim text against product target customers
    all_claims_text = " ".join([c.claim for c in claims]).lower()
    
    for target in product.target_customers:
        target_lower = target.lower()
        if target_lower in company_text or target_lower in all_claims_text:
            score += 0.25

    if any(k in all_claims_text for k in ["saas", "software", "b2b", "sales", "outbound", "automation"]):
        score += 0.2

    return min(score, 1.0)


def _compute_persona_fit(person: PersonContext) -> float:
    if not person.role:
        return 0.3
    seniority = (person.seniority or "").lower()
    role_lower = person.role.lower()

    if seniority in ("executive", "manager"):
        if any(k in role_lower for k in ["sales", "revenue", "cro", "ops", "operations", "sdr", "growth"]):
            return 0.95
        return 0.75
    if seniority == "individual contributor":
        return 0.5
    return 0.4


def _compute_timing_fit(claims: list[Claim]) -> float:
    score = 0.2
    for c in claims:
        claim_lower = c.claim.lower()
        if any(k in claim_lower for k in ["hiring", "careers", "expansion", "growth", "funding", "new product"]):
            score += 0.35
    return min(score, 1.0)


def _compute_evidence_coverage(claims: list[Claim]) -> float:
    if not claims:
        return 0.0
    fact_count = sum(1 for c in claims if c.type == ClaimType.FACT)
    total_count = len(claims)
    ratio = fact_count / max(total_count, 1)
    
    # Scale based on volume and fact ratio
    volume_score = min(total_count / 5.0, 1.0)
    return round(0.5 * volume_score + 0.5 * ratio, 2)


def _generate_llm_prose(
    company: CompanyContext,
    person: PersonContext,
    product: ProductContext,
    claims: list[Claim],
    pursue: bool,
    overall_score: float
) -> dict | None:
    claims_formatted = "\n".join([f"- [{c.type.value.upper()}] {c.claim}" for c in claims[:8]])
    
    system_prompt = (
        "You are a strategic B2B sales analyst. Synthesize the provided company and person context "
        "into clear sales opportunity prose. Output JSON with keys:\n"
        "- primary_problem: short statement of the core problem or angle\n"
        "- value_hypothesis: 1-2 sentence explanation of how the product helps\n"
        "- likely_objections: list of 2-3 realistic objections\n"
        "- recommended_angle: strategic positioning angle for the call\n"
    )
    
    user_prompt = (
        f"Product: {product.name} - {product.description}\n"
        f"Target Customers: {product.target_customers}\n"
        f"Company Industry: {company.industry or 'Unknown'}\n"
        f"Person Role: {person.role or 'Unknown'} ({person.seniority or 'Unknown'})\n"
        f"Opportunity Fit Score: {overall_score} (Pursue: {pursue})\n"
        f"Extracted Claims:\n{claims_formatted}"
    )
    
    return complete_json(system=system_prompt, user=user_prompt)
