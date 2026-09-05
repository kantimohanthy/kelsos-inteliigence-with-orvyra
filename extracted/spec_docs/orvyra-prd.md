# PRD — ORVYRA Intelligence Layer (Klesos Reference Implementation)

**Status:** Draft v0.1 — MVP scope, locked for build
**Owner:** Ujju
**Contributors:** Kyle (Klesos)
**Last updated:** 2026-09-04

---

## 1. Problem

Klesos runs outbound sales conversations as an AI voice agent. Today
it calls "cold" — no structured understanding of who the prospect is,
what their company does, or what happened in prior contact. That
produces generic conversations, wasted calls on poor-fit prospects,
and no compounding memory across calls.

ORVYRA is being generalized from a single space-economy intelligence
product into a **contextual intelligence and reasoning layer** that
any execution client can call. Klesos is the first execution client
and the forcing function for the MVP.

## 2. Goal

Give Klesos, before every call, a structured, honest picture of the
prospect and a conversation strategy (never a script) — and after
every call, an analysis that updates a durable memory of that
prospect so the next contact isn't a cold start.

**Success metric:** calls briefed by ORVYRA convert to
`interested_follow_up` / booked-meeting at a measurably higher rate
than unbriefed calls, measured over the first 100 Klesos calls post-
integration.

## 3. Non-goals (MVP)

- ORVYRA does not write or speak the call script — Klesos owns
  real-time execution.
- No live mid-call assist yet (real-time endpoint is phase 2).
- No scraping of personal/social data beyond what's explicitly
  provided or publicly available on the company's own site —
  consent-aware by design, not "scrape everything."
- No multi-tenant auth/billing — single-team internal tool for now.

## 4. Users

| User | Need |
|---|---|
| Klesos (system) | Structured pre-call packet + post-call analysis via API |
| Kyle / Klesos operators | Visibility into why ORVYRA recommended (or didn't recommend) pursuing a prospect |
| Ujju / ORVYRA operators | A growing intelligence graph that gets more valuable per prospect over time |

## 5. System stages — the full loop (8 stages)

This is the complete pipeline, end to end, one prospect at a time.
Stages 1–3 and 7–8 are built and live in the MVP scaffold; 4–6 are
partially built (heuristic fallback) or explicitly deferred — marked below.

| # | Stage | What happens | Status |
|---|---|---|---|
| 1 | **Identity resolution** | Klesos sends a minimal prospect object (name, company, email, LinkedIn, company URL). ORVYRA resolves who this actually is and disambiguates same-name collisions. | **Built** (trusts input keys; cross-source dedup not yet built) |
| 2 | **Company intelligence** | Pull industry, size, business model, and recent signals (hiring, funding, expansion) for the prospect's company. | **Built — heuristic only.** Keyword-matches the company's own site text. Real firmographics/hiring/news provider not yet wired in. |
| 3 | **Person intelligence** | Build a commercially-relevant profile of the person: role, seniority, responsibilities, probable priorities — every priority tagged `fact` or `inference` with a confidence score, never presented as certain. | **Built** |
| 4 | **Opportunity reasoning** | Reason about why this person might (or might not) care about the product, likely objections, and a recommended angle. Must be willing to output `pursue: false`. | **Built** — heuristic fallback live; real LLM reasoning (Claude) wired in and ready, just needs `ANTHROPIC_API_KEY` set |
| 5 | **Conversation strategy** | Package angle + discovery questions + things to avoid. Explicitly *not* a script — Klesos decides real-time delivery. | **Built** |
| 6 | **Real-time mid-call intelligence** | During the call, Klesos can query ORVYRA for context on something the prospect just said (e.g. "we already use Salesforce") and get a live recommendation. | **Deferred — not MVP.** Needs its own low-latency endpoint; build only after stages 1–5 and 7–8 are proven on real calls. |
| 7 | **Post-call analysis** | Klesos sends the transcript + events. ORVYRA classifies outcome, intent score, objections, signals, and recommends the next best action. | **Built** |
| 8 | **Memory / follow-up intelligence** | The call analysis and packet are written into ORVYRA's memory against that prospect. The *next* pre-call for the same person is no longer a cold start — prior objections, requests, and outcomes are already loaded in. | **Built** — in-process store for MVP; Postgres + pgvector is the planned upgrade, same interface |

**Read as a loop:** stages 1→5 run before a call, 6 runs during a
call (deferred), 7→8 run after — and stage 8 feeds straight back
into stage 1 the next time this same prospect comes up.

## 6. Core requirements

### 6.1 Pre-call intelligence
- Given `{name, company, email, linkedin_url, company_url, objective, product}`, return an `IntelligencePacket`:
  - Resolved identity
  - Company context (industry, signals — sourced, not invented)
  - Person context (role, seniority)
  - Opportunity hypothesis, explicitly tagged `fact` vs `inference`, with a confidence score
  - A `pursue: true/false` recommendation with a stated reason — ORVYRA must be able to say "don't call this one"
  - Conversation strategy: opening angle, discovery questions, things to avoid — never a full script

### 6.2 Post-call intelligence
- Given `{conversation_id, prospect_id, transcript, events}`, return:
  - Outcome classification, intent score, objections, signals
  - Next best action (channel + timing)
  - CRM stage/probability
  - Written to ORVYRA's memory against that prospect

### 6.3 Memory
- Every packet and call analysis persists against a `prospect_id`.
- The *next* pre-call for a known prospect includes prior interaction
  history — no repeated cold-start questions.

### 6.4 Honesty constraint (hard requirement, not a nice-to-have)
- Every claim in a packet is tagged `fact` or `inference` with
  evidence and a confidence score. ORVYRA never presents an inference
  as a fact, and never fabricates evidence to support a
  recommendation to pursue.

## 7. Out of scope for this repo

The existing ORVYRA space-economy frontend (cinematic Earth, entity
dossiers, knowledge graph) is a **separate, frozen product surface**
and is not touched by this work. This PRD covers the intelligence
API layer and its own operator dashboard only.

## 8. Milestones

1. **API contract + two endpoints live** (pre-call, post-call) — done in MVP scaffold.
2. **Klesos wired to call both endpoints** in its outbound flow.
3. **Real enrichment sources** replace the keyword-heuristic fallback (firmographics, hiring signals, news).
4. **Operator dashboard** (see design doc) for reviewing packets, overriding pursue/no-pursue, and watching call outcomes roll in.
5. **Real-time mid-call endpoint** — stretch goal, not MVP.

## 9. Open questions

- Which firmographics/news/hiring-signal provider to license for real company enrichment (cost vs. coverage tradeoff — not decided yet).
- Whether Klesos calls ORVYRA synchronously (blocking dial) or ORVYRA pre-warms packets for a queued call list.
- CRM system of record: none chosen yet — `ingestion/crm.py` currently reads only ORVYRA's own memory.
