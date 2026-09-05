"""
CRM / prior-interaction ingestion.

MVP: reads from Orvyra's own intelligence memory (past packets and
call analyses for this prospect). Real version: also pull from an
actual CRM (HubSpot/Salesforce/Pipedrive) via its API, authorized
per-user, and merge with this same shape.
"""

from __future__ import annotations
from storage.memory import memory


def get_prior_interactions(prospect_id: str) -> list[dict]:
    history = memory.get_history(prospect_id)
    return [
        {
            "conversation_id": h.conversation_id,
            "outcome": h.outcome,
            "intent_score": h.intent_score,
            "objections": h.objections,
        }
        for h in history
    ]
