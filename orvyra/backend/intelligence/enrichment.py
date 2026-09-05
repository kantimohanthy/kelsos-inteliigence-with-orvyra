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


from urllib.parse import urlparse
from storage.db import SessionLocal
from storage.sql_models import IdentityModel


def resolve_identity(prospect: ProspectInput) -> dict:
    """
    Stage A — identity resolution.

    Queries IdentityModel across email, linkedin_url, domains, name+company.
    Returns 'needs_review' status if conflicting signals are submitted.
    """
    keys = []
    if prospect.email:
        keys.append(("email", prospect.email.lower().strip()))
    if prospect.linkedin_url:
        keys.append(("linkedin_url", prospect.linkedin_url.lower().strip()))
    if prospect.company_url:
        domain = urlparse(prospect.company_url).netloc or prospect.company_url
        if domain.startswith("www."):
            domain = domain[4:]
        if domain:
            keys.append(("domain", domain.lower().strip()))
    if prospect.name and prospect.company:
        keys.append(("name_company", f"{prospect.name.lower().strip()}|{prospect.company.lower().strip()}"))

    key_vals = [k[1] for k in keys]

    if not key_vals:
        return {
            "name": prospect.name,
            "status": "unresolved",
            "needs_review": False,
            "resolved": False,
            "disambiguation_keys": [],
            "conflicts": [],
        }

    db = SessionLocal()
    try:
        recs = db.query(IdentityModel).filter(IdentityModel.key_value.in_(key_vals)).all()

        prospect_ids = set()
        conflicts = []

        for r in recs:
            prospect_ids.add(r.prospect_id)
            if prospect.company and r.company_name:
                c1 = prospect.company.lower().strip()
                c2 = r.company_name.lower().strip()
                if c1 != c2 and c1 not in c2 and c2 not in c1:
                    conflicts.append(f"Company mismatch on key '{r.key_value}': '{prospect.company}' vs stored '{r.company_name}'")

        if len(prospect_ids) > 1:
            conflicts.append(f"Multiple prospects matched for input keys: {list(prospect_ids)}")

        needs_review = len(conflicts) > 0
        status = "needs_review" if needs_review else ("resolved" if recs else "new")

        return {
            "name": prospect.name,
            "status": status,
            "needs_review": needs_review,
            "resolved": not needs_review and len(recs) > 0,
            "prospect_id": list(prospect_ids)[0] if len(prospect_ids) == 1 else None,
            "disambiguation_keys": key_vals,
            "conflicts": conflicts,
        }
    finally:
        db.close()


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
