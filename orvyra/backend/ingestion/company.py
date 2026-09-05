"""
Company intelligence ingestion.

MVP: heuristic extraction from the scraped site text (industry
keywords, size hints) plus a clearly-labeled SYNTHETIC fallback so
the pipeline is demoable before real data providers are wired in.

Real version: plug in a firmographics API (Clearbit/Crunchbase-style),
a job-postings source for hiring signals, and a news/funding feed.
Keep every field's provenance (LIVE / SOURCE_FIXTURE / SYNTHETIC)
attached — never let a synthetic value look like a fact downstream.
"""

from __future__ import annotations

_INDUSTRY_KEYWORDS = {
    "saas": "B2B SaaS",
    "software": "Software",
    "fintech": "Fintech",
    "healthcare": "Healthcare",
    "logistics": "Logistics",
    "manufacturing": "Manufacturing",
    "sales": "Sales Tech",
    "marketing": "MarTech",
    "ai": "AI / ML",
}


def infer_industry(text_sample: str | None) -> str | None:
    if not text_sample:
        return None
    lowered = text_sample.lower()
    for keyword, label in _INDUSTRY_KEYWORDS.items():
        if keyword in lowered:
            return label
    return None


def build_company_context(prospect_company: str | None, site_data: dict) -> dict:
    industry = infer_industry(site_data.get("text_sample"))
    recent_signals: list[str] = []

    if site_data.get("source") == "live":
        recent_signals.append("Company website reachable; description parsed for context")
    elif site_data.get("source") == "fetch_failed":
        recent_signals.append("Company site unreachable at enrichment time")
    else:
        recent_signals.append("No company URL provided — enrichment limited to prospect input")

    return {
        "name": prospect_company,
        "industry": industry,
        "business_model": None,  # TODO: wire firmographics provider
        "estimated_size": None,  # TODO: wire firmographics provider
        "recent_signals": recent_signals,
        "provenance": "live" if site_data.get("source") == "live" else "unavailable",
    }
