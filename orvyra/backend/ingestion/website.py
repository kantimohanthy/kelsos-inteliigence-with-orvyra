"""
Website ingestion.

MVP: fetches the company URL if reachable and extracts obvious
signals (title, meta description, simple keyword heuristics).
Swap in Playwright only when a target requires JS rendering —
httpx + BeautifulSoup covers most marketing sites.

Every value returned here should be traceable to source_fixture
or live so `intelligence/confidence.py` can score it correctly.
"""

from __future__ import annotations
import httpx
from bs4 import BeautifulSoup


async def fetch_company_site(company_url: str | None) -> dict:
    if not company_url:
        return {"source": "none", "title": None, "description": None, "text_sample": None}

    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            resp = await client.get(company_url)
            resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001 — ingestion must never crash the pipeline
        return {"source": "fetch_failed", "error": str(exc), "title": None, "description": None, "text_sample": None}

    soup = BeautifulSoup(resp.text, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    meta = soup.find("meta", attrs={"name": "description"})
    description = meta.get("content", "").strip() if meta else None
    text_sample = " ".join(soup.get_text(separator=" ", strip=True).split())[:2000]

    return {
        "source": "live",
        "title": title,
        "description": description,
        "text_sample": text_sample,
    }
