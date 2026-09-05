"""
LLM provider abstraction.

One function, `complete_json`, used everywhere reasoning needs a
model call. If ANTHROPIC_API_KEY is set, it calls Claude and expects
strict JSON back. If not set, callers fall back to their own
heuristic logic — the pipeline must never crash for lack of a key.
"""

from __future__ import annotations
import os
import json


def has_llm() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def complete_json(system: str, user: str, model: str = "claude-sonnet-4-6") -> dict | None:
    """Returns parsed JSON dict, or None if no key configured / call failed.
    Callers MUST have a heuristic fallback for the None case."""
    if not has_llm():
        return None

    try:
        import anthropic  # imported lazily so the app runs without the package installed

        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=model,
            max_tokens=1024,
            system=system + "\nRespond with ONLY valid JSON. No markdown fences, no preamble.",
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(block.text for block in resp.content if block.type == "text")
        text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(text)
    except Exception:  # noqa: BLE001 — reasoning must degrade gracefully, never 500
        return None
