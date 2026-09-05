"""
Enrichment stage.

Identity resolution + structuring of company/person context from
raw ingestion output. This is deliberately conservative: it never
invents a fact. Anything not directly observed becomes a Claim with
type=inference and an honest confidence score, handled downstream
in reasoning.py.
"""

from __future__ import annotations
from storage.models import ProspectInput, CompanyContext, PersonContext, Claim, ClaimType


def resolve_identity(prospect: ProspectInput) -> dict:
    """
    Stage A — identity resolution.

    MVP: trusts the input as given (name + email/linkedin as the
    disambiguating keys). Real version: cross-check name+company
    against multiple sources before merging, to avoid conflating
    two different people with the same name.
    """
    return {
        "name": prospect.name,
        "disambiguation_keys": [k for k in [prospect.email, prospect.linkedin_url] if k],
        "resolved": bool(prospect.email or prospect.linkedin_url),
    }


def build_person_context(prospect: ProspectInput, role_hint: str | None = None) -> PersonContext:
    """
    MVP: role/seniority come from explicit input for now (no LinkedIn
    scraping — that requires an authorized data source or user-provided
    context, per the consent-aware design). probable_priorities are
    left empty here; reasoning.py fills them in as tagged inferences.
    """
    return PersonContext(
        role=role_hint,
        seniority=_infer_seniority(role_hint),
        responsibilities=[],
        probable_priorities=[],
    )


def _infer_seniority(role: str | None) -> str | None:
    if not role:
        return None
    lowered = role.lower()
    if any(t in lowered for t in ["vp", "chief", "cxo", "head of", "director", "founder", "ceo", "cto", "cfo"]):
        return "Executive"
    if "manager" in lowered or "lead" in lowered:
        return "Manager"
    return "Individual Contributor"


def build_company_context(company_data: dict) -> CompanyContext:
    return CompanyContext(
        name=company_data.get("name"),
        industry=company_data.get("industry"),
        business_model=company_data.get("business_model"),
        estimated_size=company_data.get("estimated_size"),
        recent_signals=company_data.get("recent_signals", []),
    )
