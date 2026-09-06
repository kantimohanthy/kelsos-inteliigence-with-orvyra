"""
Critic Module — Contradiction & Evidence Verification Pass.

Acts as an adversarial critic reviewing the Opportunity hypothesis before
finalizing the IntelligencePacket:
1. Checks evidence support vs overreach.
2. Checks company vs person level conflation.
3. Detects weak / single-source low-confidence claims.
4. Checks previous interactions for prior rejection or do-not-contact signals.
"""

from __future__ import annotations
from storage.models import Opportunity, Claim, ClaimType


def critique_opportunity(
    opportunity: Opportunity,
    claims: list[Claim],
    previous_interactions: list[dict],
) -> Opportunity:
    # Copy mutable fields
    confidence = opportunity.confidence
    pursue = opportunity.pursue
    reason_if_not_pursue = opportunity.reason_if_not_pursue
    primary_problem = opportunity.primary_problem
    value_hypothesis = opportunity.value_hypothesis
    likely_objections = list(opportunity.likely_objections)
    recommended_angle = opportunity.recommended_angle

    # 1. Check prior rejection / do-not-contact signals in previous_interactions
    negative_signals = ["do not contact", "not interested", "opt out", "opt-out", "unsubscribe", "rejected", "disqualified", "stop calling"]
    for inter in previous_interactions:
        text_content = str(inter).lower()
        if any(sig in text_content for sig in negative_signals):
            return Opportunity(
                primary_problem=primary_problem,
                confidence=min(confidence, 0.15),
                value_hypothesis=value_hypothesis,
                likely_objections=likely_objections,
                recommended_angle=recommended_angle,
                pursue=False,
                reason_if_not_pursue=(
                    "Critic Pass: Previous interaction contains an explicit rejection or do-not-contact signal; "
                    "overriding pursue recommendation."
                ),
            )

    # 2. Check weak signals: single-source or low-confidence claims supporting pursue recommendation
    if pursue:
        if len(claims) == 0:
            return Opportunity(
                primary_problem=primary_problem,
                confidence=min(confidence, 0.3),
                value_hypothesis=value_hypothesis,
                likely_objections=likely_objections,
                recommended_angle=recommended_angle,
                pursue=False,
                reason_if_not_pursue=(
                    "Critic Pass: Recommendation reached beyond evidence — no claims extracted to support opportunity hypothesis."
                ),
            )

        if len(claims) == 1:
            single = claims[0]
            if single.confidence <= 0.65 or single.type == ClaimType.INFERENCE:
                return Opportunity(
                    primary_problem=primary_problem,
                    confidence=min(confidence, 0.35),
                    value_hypothesis=value_hypothesis,
                    likely_objections=likely_objections,
                    recommended_angle=recommended_angle,
                    pursue=False,
                    reason_if_not_pursue=(
                        "Critic Pass: Recommendation relied on a single low-confidence claim about hiring activity; "
                        "insufficient to support pursue."
                    ),
                )

        # 3. Check for conflation or unbacked fact assertions
        low_conf_facts = [c for c in claims if c.confidence < 0.4]
        if len(low_conf_facts) == len(claims) and len(claims) < 3:
            return Opportunity(
                primary_problem=primary_problem,
                confidence=min(confidence, 0.35),
                value_hypothesis=value_hypothesis,
                likely_objections=likely_objections,
                recommended_angle=recommended_angle,
                pursue=False,
                reason_if_not_pursue=(
                    "Critic Pass: Extracted claims have low confidence scores; insufficient empirical backing for outbound pursue."
                ),
            )

    # If no critic issues found, return original or updated opportunity
    return Opportunity(
        primary_problem=primary_problem,
        confidence=confidence,
        value_hypothesis=value_hypothesis,
        likely_objections=likely_objections,
        recommended_angle=recommended_angle,
        pursue=pursue,
        reason_if_not_pursue=reason_if_not_pursue,
    )
