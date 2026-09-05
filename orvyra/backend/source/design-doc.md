# Design Doc — ORVYRA Operator Dashboard

**Status:** Draft v0.1
**Scope:** The internal dashboard operators use to review pre-call
packets, pursue/no-pursue calls, and watch post-call outcomes. Does
**not** touch the existing ORVYRA marketing/query frontend, which
stays frozen per prior direction.

---

## 1. Reference

**Dribbble:** [B2B Enterprise Dashboard UI/UX Design — Dark Mode, by Denovers](https://dribbble.com/shots/15255974-B2B-Enterprise-Dashboard-UI-UX-Design-Dark-Mode)

Picked over the other dark-mode sales-dashboard shots in the same
search because it's built for dense B2B operational data (multiple
metric panels, tabular pipeline data, status pills) rather than a
consumer-style analytics chart wall — closer to what an ORVYRA
operator actually needs to scan: packets, confidence scores, and
pursue/no-pursue calls at a glance.

**What we're taking from it (principles, not a clone):**
- Dark canvas with a small number of high-contrast data panels rather than one dense grid
- Left-rail navigation, content organized into scannable cards, not walls of table rows
- Status communicated with color-coded pills/badges (pursue vs. no-pursue, outcome states) rather than icons alone
- Generous spacing between data groups so confidence/evidence annotations don't feel cramped next to the primary numbers

**What we're deliberately not copying:** exact color values, iconography, or chart styles — those come from ORVYRA's existing, already-locked design system (below), not from the reference.

## 2. Design system (carried over from ORVYRA brand, not re-decided here)

| Token | Value |
|---|---|
| Background | Near-black / deep space navy |
| Primary text | High-contrast white |
| Accent | Electric cyan/teal — used sparingly, for pursue/positive states and active nav only |
| Typography | Inter / Space Grotesk for UI text; IBM Plex Mono for metadata, IDs, confidence scores, timestamps |
| Data honesty | Every value on screen must be visibly tagged LIVE / SOURCE_FIXTURE / SYNTHETIC — no exceptions, matching the ORVYRA-wide provenance rule |

## 3. Key screens (MVP)

1. **Prospect queue** — list of `IntelligencePacket`s awaiting a call, each row showing name, company, opportunity confidence, and a pursue/no-pursue pill. Filter by pursue status.
2. **Packet detail** — full breakdown of one packet: company context, person context, opportunity hypothesis with fact/inference tags and evidence, conversation strategy (angles + discovery questions, explicitly labeled "not a script").
3. **Call outcomes** — post-call analyses as they land: outcome, intent score, objections, next best action. Same card language as the packet detail so operators recognize the pattern.
4. **Prospect memory view** — timeline of every packet + call analysis for one prospect, so an operator can see how the relationship evolved call over call.

## 4. Interaction principles

- No screen ever presents an inference as settled fact — the fact/inference tag from the API is always visible, not just in a tooltip.
- The `pursue: false` state is a first-class, non-apologetic UI state — a clearly labeled "Recommended: don't pursue" card with the stated reason, not a greyed-out or hidden row.
- Confidence scores render as a number + a short bar, in IBM Plex Mono — consistent with how ORVYRA already displays confidence elsewhere.

## 5. Explicitly deferred

Real-time mid-call view, and any operator-facing chart/analytics wall beyond the four screens above — build those once the two batch endpoints have real call volume behind them, not before.
