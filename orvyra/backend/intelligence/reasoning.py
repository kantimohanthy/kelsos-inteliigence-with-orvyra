"""
Reasoning stage.

Turns structured context into: an opportunity hypothesis (why would
this person care, or why not), a conversation strategy (angles and
questions, never a script), and post-call analysis (what happened,
what to do next).

Design rule carried over from the spec: Orvyra reasons and advises,
Klesos executes in real time. This module never outputs a script —
only strategy. And it must be willing to output pursue=False.
"""

from __future__ import annotations
from storage.models import (
    Opportunity, ConversationStrategy, Claim, ClaimType,
    CompanyContext, PersonContext, CallAnalysis, NextAction, PostCallInput,
)
from .llm import complete_json, has_llm
from .confidence import score_from_signal_count, pursue_threshold


PRODUCT_CONTEXT = "Klesos: an AI voice agent that runs outbound sales conversations."


def build_opportunity(company: CompanyContext, person: PersonContext, product: str) -> Opportunity:
    if has_llm():
        result = complete_json(
            system=(
                "You are a B2B sales intelligence analyst. Given company and "
                "person context, hypothesize why this person might care about "
                "the given product, and why they might not. Be honest — if the "
                "fit looks weak, say so and recommend not pursuing. Output JSON "
                "with keys: primary_problem, confidence (0-1), value_hypothesis, "
                "likely_objections (list), recommended_angle, pursue (bool), "
                "reason_if_not_pursue."
            ),
            user=(
                f"Product: {product}\n"
                f"Company: industry={company.industry}, size={company.estimated_size}, "
                f"signals={company.recent_signals}\n"
                f"Person: role={person.role}, seniority={person.seniority}"
            ),
        )
        if result:
            return Opportunity(**result)

    # Heuristic fallback — no LLM key configured.
    # Only count signals that actually describe the prospect, not
    # meta-notes about enrichment failing/being unavailable.
    real_signals = [
        s for s in company.recent_signals
        if s not in (
            "No company URL provided — enrichment limited to prospect input",
            "Company site unreachable at enrichment time",
        )
    ]
    confidence = score_from_signal_count(len(real_signals))
    pursue = confidence >= pursue_threshold() and bool(person.role) and bool(real_signals)

    if not pursue:
        return Opportunity(
            primary_problem=None,
            confidence=confidence,
            pursue=False,
            reason_if_not_pursue="Insufficient signal to justify a confident hypothesis — "
                                  "not enough company/role context resolved yet.",
        )

    return Opportunity(
        primary_problem=f"Hypothesis based on: {'; '.join(real_signals[:2])}",
        confidence=confidence,
        value_hypothesis=f"{product} could reduce manual effort in whatever this role owns.",
        likely_objections=["Concern about call/response quality", "Integration with existing tools", "Trust/compliance concerns"],
        recommended_angle="Position as augmentation, not replacement.",
        pursue=True,
    )


def build_conversation_strategy(opportunity: Opportunity, objective: str) -> ConversationStrategy | None:
    if not opportunity.pursue:
        return None
    return ConversationStrategy(
        objective=objective,
        opening_angle=opportunity.primary_problem,
        discovery_questions=[
            "How are you currently handling this today?",
            "What's the biggest bottleneck in that process?",
            "Have you experimented with automating any part of it?",
        ],
        proof_points=[],
        avoid=["Claiming to replace the team", "Referencing unverified personal details"],
    )


def analyze_call(payload: PostCallInput) -> CallAnalysis:
    if has_llm():
        result = complete_json(
            system=(
                "You analyze a sales call transcript. Output JSON with keys: "
                "outcome (one of: interested_follow_up, not_interested, needs_more_info, "
                "booked_meeting). If the prospect asks for pricing, demo, or details, or says 'sounds good', "
                "classify outcome as 'interested_follow_up'. "
                "intent_score (0-1), signals (list of short strings), "
                "objections (list), next_action_channel (email/call/none), "
                "next_action_description, delay_hours (number), crm_stage, crm_probability (0-1)."
            ),
            user=f"Transcript:\n{payload.transcript}\n\nEvents: {[e.model_dump() for e in payload.events]}",
        )
        if result:
            return CallAnalysis(
                conversation_id=payload.conversation_id,
                prospect_id=payload.prospect_id,
                outcome=result.get("outcome", "needs_more_info"),
                intent_score=result.get("intent_score", 0.5),
                signals=result.get("signals", []),
                objections=result.get("objections", []),
                next_best_action=NextAction(
                    action=result.get("next_action_description", "follow_up"),
                    channel=result.get("next_action_channel"),
                    delay_hours=result.get("delay_hours"),
                ),
                crm_stage=result.get("crm_stage", "qualified"),
                crm_probability=result.get("crm_probability", 0.5),
            )

    # Heuristic fallback — crude keyword scan, clearly not a substitute for real NLP.
    text = payload.transcript.lower()
    positive_markers = ["interested", "pricing", "demo", "sounds good", "let's talk", "send me"]
    negative_markers = ["not interested", "no thanks", "remove me", "stop calling"]

    intent_score = 0.5
    outcome = "needs_more_info"
    if any(m in text for m in negative_markers):
        outcome, intent_score = "not_interested", 0.1
    elif any(m in text for m in positive_markers):
        outcome, intent_score = "interested_follow_up", 0.7

    return CallAnalysis(
        conversation_id=payload.conversation_id,
        prospect_id=payload.prospect_id,
        outcome=outcome,
        intent_score=intent_score,
        signals=[m for m in positive_markers if m in text],
        objections=[],
        next_best_action=NextAction(
            action="send_follow_up_email" if outcome != "not_interested" else "mark_do_not_contact",
            channel="email" if outcome != "not_interested" else None,
            delay_hours=14 if outcome != "not_interested" else None,
        ),
        crm_stage="qualified" if outcome == "interested_follow_up" else "unqualified" if outcome == "not_interested" else "in_progress",
        crm_probability=intent_score,
    )
