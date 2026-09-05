"""
Person Intelligence Module — Person context & priority inference.

Rules:
- Uses explicit role_hint and company context only (no LinkedIn scraping).
- Reuses _infer_seniority() from enrichment.py.
- Every inferred priority MUST be a Claim with type: ClaimType.INFERENCE.
"""

from __future__ import annotations
from storage.models import PersonContext, CompanyContext, Claim, ClaimType, EvidenceSource
from .enrichment import _infer_seniority


def infer_person_context(
    role_hint: str | None,
    company: CompanyContext,
    prior_interactions: list[dict] | None = None
) -> PersonContext:
    seniority = _infer_seniority(role_hint)
    responsibilities: list[str] = []
    probable_priorities: list[Claim] = []

    if role_hint:
        role_lower = role_hint.lower()
        
        if "sales" in role_lower or "revenue" in role_lower or "cro" in role_lower:
            responsibilities.extend(["Driving quota performance", "Improving call conversion rates", "Pipeline execution"])
            probable_priorities.append(
                Claim(
                    claim="Maximizing SDR outbound efficiency and demo booking rates",
                    type=ClaimType.INFERENCE,
                    confidence=0.75,
                    evidence=[
                        EvidenceSource(
                            source_type="inference_rule",
                            excerpt=f"Inferred from role title '{role_hint}'",
                            confidence=0.75,
                        )
                    ],
                )
            )
        elif "ops" in role_lower or "operations" in role_lower:
            responsibilities.extend(["Workflow optimization", "Tool stack integration", "Scaling sales operations"])
            probable_priorities.append(
                Claim(
                    claim="Eliminating manual rep data entry and optimizing tooling workflows",
                    type=ClaimType.INFERENCE,
                    confidence=0.70,
                    evidence=[
                        EvidenceSource(
                            source_type="inference_rule",
                            excerpt=f"Inferred from role title '{role_hint}'",
                            confidence=0.70,
                        )
                    ],
                )
            )
        elif "founder" in role_lower or "ceo" in role_lower or "executive" in (seniority or "").lower():
            responsibilities.extend(["Strategic growth", "Resource allocation", "Accelerating revenue generation"])
            probable_priorities.append(
                Claim(
                    claim="Accelerating customer acquisition while controlling SDR headcount costs",
                    type=ClaimType.INFERENCE,
                    confidence=0.80,
                    evidence=[
                        EvidenceSource(
                            source_type="inference_rule",
                            excerpt=f"Inferred from executive role '{role_hint}'",
                            confidence=0.80,
                        )
                    ],
                )
            )
        else:
            responsibilities.append(f"Managing functions related to {role_hint}")
            probable_priorities.append(
                Claim(
                    claim=f"Evaluating tools that improve efficiency in {role_hint} workflows",
                    type=ClaimType.INFERENCE,
                    confidence=0.50,
                    evidence=[
                        EvidenceSource(
                            source_type="inference_rule",
                            excerpt=f"Inferred from role hint '{role_hint}'",
                            confidence=0.50,
                        )
                    ],
                )
            )
    else:
        probable_priorities.append(
            Claim(
                claim="General commercial interest in automating outbound sales workflows",
                type=ClaimType.INFERENCE,
                confidence=0.40,
                evidence=[
                    EvidenceSource(
                        source_type="inference_rule",
                        excerpt="Fallback priority — no explicit role hint provided",
                        confidence=0.40,
                    )
                ],
            )
        )

    # Incorporate company signals if available
    if company.industry:
        probable_priorities.append(
            Claim(
                claim=f"Navigating competitive landscape within {company.industry}",
                type=ClaimType.INFERENCE,
                confidence=0.60,
                evidence=[
                    EvidenceSource(
                        source_type="inference_rule",
                        excerpt=f"Inferred from company industry '{company.industry}'",
                        confidence=0.60,
                    )
                ],
            )
        )

    return PersonContext(
        role=role_hint,
        seniority=seniority,
        responsibilities=responsibilities,
        probable_priorities=probable_priorities,
    )
