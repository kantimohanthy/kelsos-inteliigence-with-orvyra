"""
Conversation Strategy Module — Non-scripted conversation strategy formulation.

Rules:
- Formulates opening angle, discovery questions, proof points, and avoid list.
- Explicitly flags unverified inference details in the avoid list (Klesos must not mention unverified inferences as facts).
- Strategy, never a script.
- If opportunity.pursue is False, returns None.
"""

from __future__ import annotations
from storage.models import ConversationStrategy, Opportunity, Claim, ClaimType


def build_strategy(opportunity: Opportunity, claims: list[Claim], objective: str) -> ConversationStrategy | None:
    if not opportunity.pursue:
        return None

    opening_angle = opportunity.recommended_angle or opportunity.primary_problem or "Position as augmentation to existing team"

    discovery_questions = [
        "How is your team currently handling outbound prospect research and initial lead intake?",
        "What is the biggest bottleneck in your SDR call workflow today?",
        "Have you experimented with AI voice agents or automated call briefing tools?",
        "What tools or CRM systems would any call automation need to integrate with?",
    ]

    proof_points: list[str] = []
    # Collect proof points from fact-based claims
    fact_claims = [c.claim for c in claims if c.type == ClaimType.FACT]
    if fact_claims:
        proof_points.extend(fact_claims[:3])

    # Construct avoid list including explicit warning against stating unverified inferences as facts
    avoid = [
        "Claiming to replace the existing sales team",
        "Reading rigid scripts — maintain dynamic conversation flow",
    ]

    # Collect unverified inference details to avoid claiming them as verified facts
    inference_claims = [c.claim for c in claims if c.type == ClaimType.INFERENCE]
    for inf in inference_claims[:3]:
        avoid.append(f"Stating as absolute fact: '{inf}' (unverified inference)")

    return ConversationStrategy(
        objective=objective,
        opening_angle=opening_angle,
        discovery_questions=discovery_questions[:5],
        proof_points=proof_points,
        avoid=avoid,
    )
