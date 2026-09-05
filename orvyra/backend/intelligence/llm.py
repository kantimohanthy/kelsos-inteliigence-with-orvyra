from __future__ import annotations
import os
import json
from pathlib import Path
from dotenv import load_dotenv

backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(backend_dir / ".env")
load_dotenv(backend_dir.parent / ".env")
load_dotenv()


import logging

logger = logging.getLogger(__name__)


def has_llm() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def complete_json(system: str, user: str, model: str = "claude-sonnet-5") -> dict | None:
    """Returns parsed JSON dict, or None if no key configured / call failed.
    Callers MUST have a heuristic fallback for the None case."""
    if not has_llm():
        return None

    try:
        import anthropic  # imported lazily so the app runs without the package installed

        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=model,
            max_tokens=8192,
            system=system + "\nRespond with ONLY valid JSON. No markdown fences, no preamble.",
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(getattr(block, "text", "") for block in resp.content if getattr(block, "type", None) == "text").strip()
        if "```" in text:
            for part in text.split("```"):
                part_clean = part.removeprefix("json").strip()
                if part_clean.startswith("{") or part_clean.startswith("["):
                    text = part_clean
                    break
        return json.loads(text)
    except Exception as exc:  # noqa: BLE001 — reasoning must degrade gracefully, never 500
        logger.warning(f"LLM call to model '{model}' failed ({type(exc).__name__}: {exc}); falling back to heuristics")
        return None

