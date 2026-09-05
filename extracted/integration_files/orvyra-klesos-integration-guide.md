# Integration Guide — Plugging ORVYRA into Klesos

**Scope:** exactly how the two ORVYRA endpoints wire into the real
Klesos stack (Next.js `cockpit` + Fastify `worker` + Supabase +
Twilio + Speechmatics + `lobster-trap`), based on the confirmed
dependency inventory. No new services, no new dependencies — this
plugs into what's already there.

---

## 1. Where ORVYRA sits in the topology

```
Apollo.io (lead source)
       │
       ▼
  Supabase (leads table)
       │
       ▼
┌─────────────────┐        pre-call         ┌──────────────┐
│  worker (Fastify)│ ───────────────────────▶│    ORVYRA     │
│  on Vultr         │◀─────────────────────── │  (FastAPI,    │
│                    │      IntelligencePacket │   Railway)    │
│  - Twilio dial     │                          └──────────────┘
│  - lobster-trap     │                                │  ▲
│    (prompt-injection│                                │  │
│    shield)           │                                │  │
│  - Speechmatics       │      post-call (transcript)   │  │
│    transcription      │────────────────────────────────┘  │
│  - @anthropic-ai/sdk   │      CallAnalysis ─────────────────┘
│    (live conversation)  │
└──────────┬───────────────┘
           │
           ▼
     Supabase (call log, updated lead stage)
           │
           ▼
   HubSpot (optional CRM push) / Resend (email follow-up, via cockpit)
```

ORVYRA is a **peer service**, not embedded in either the cockpit or
the worker. It's called over plain HTTPS from the worker, the same
way the worker already calls Twilio, Speechmatics, and HubSpot.

## 2. Auth (done — see `api/auth.py`)

- ORVYRA now requires `Authorization: Bearer <ORVYRA_API_KEY>` on
  both `/v1/intelligence/*` routes. `/health` stays open for
  uptime checks.
- Generate one value: `openssl rand -hex 32`.
- Set it as `ORVYRA_API_KEY` in **two** places:
  - Railway env vars (ORVYRA service)
  - Vultr / worker `.env` (Klesos worker) — same value, new name is fine (`ORVYRA_API_KEY` on both sides keeps it unambiguous)
- Also set `ORVYRA_API_URL` on the worker to ORVYRA's Railway URL.

This is a shared-secret model — fine for one trusted client. The
moment a second execution client (recruitment agent, CRM tool)
starts calling ORVYRA, switch to per-client keys so a compromised
worker key doesn't expose every client.

## 3. The worker-side client

Drop `source/klesos-worker-orvyra-client.ts` into
`worker/src/orvyra/client.ts` in the `deals-machine` repo. It:

- Uses `undici` and `zod` — both already worker dependencies, nothing new to install.
- Validates ORVYRA's response shape against the same contract the Pydantic models define, so a drift between the two services fails loudly in TypeScript instead of silently at runtime.
- **Fails open**: if ORVYRA is down or times out, `preCall()` returns `null` and the worker proceeds without a packet rather than blocking the dial. A broken intelligence layer should degrade Klesos to "calling cold," never stop it from calling.

## 4. Exact call sites

### 4.1 Before the Twilio dial

Wherever the worker currently pulls a lead from Supabase and hands
it to Twilio to place the call — call `preCall()` first:

```ts
import { preCall } from "./orvyra/client";

const packet = await preCall(
  { name: lead.name, company: lead.company, email: lead.email,
    linkedin_url: lead.linkedin_url, company_url: lead.company_url },
  "Book a product demo",
  lead.title // role_hint
);

if (packet && !packet.opportunity.pursue) {
  await supabase.from("leads").update({
    status: "skipped_low_relevance",
    orvyra_reason: packet.opportunity.reason_if_not_pursue,
  }).eq("id", lead.id);
  return; // don't dial
}

// stash prospect_id for the post-call step later
await supabase.from("leads").update({ orvyra_prospect_id: packet?.prospect_id ?? null }).eq("id", lead.id);
```

Add one column to the Supabase `leads` table: `orvyra_prospect_id
text`. That's the join key between Supabase and ORVYRA's own
memory — Supabase stays the system of record for lead status,
ORVYRA stays the system of record for accumulated intelligence.

### 4.2 Feeding the strategy into the live conversation

Klesos's real-time conversation is driven by `@anthropic-ai/sdk` in
the worker (with `openai` Whisper as a fallback for transcription,
not conversation). `packet.conversation_strategy` — opening angle,
discovery questions, things to avoid — becomes part of the **system
prompt** for that Claude call, not literal text to read aloud:

```ts
const systemPrompt = buildKlesosSystemPrompt({
  ...existingContext,
  opportunityContext: packet?.opportunity.pursue
    ? {
        angle: packet.conversation_strategy?.opening_angle,
        discoveryQuestions: packet.conversation_strategy?.discovery_questions,
        avoid: packet.conversation_strategy?.avoid,
        objections: packet.opportunity.likely_objections,
      }
    : undefined,
});
```

This is also the natural point for `lobster-trap` to stay exactly
where it already is — it should validate/sanitize whatever comes
back from ORVYRA the same way it does anything else that ends up in
the live prompt, since ORVYRA's `company_context.recent_signals` and
similar free-text fields are themselves influenced by scraped web
content.

### 4.3 After the call — post-call analysis

Once Speechmatics finalizes the transcript (or Whisper fallback
completes):

```ts
import { postCall } from "./orvyra/client";

const analysis = await postCall(
  callSid, // conversation_id
  lead.orvyra_prospect_id,
  finalTranscript,
  events // dial/hangup/DTMF events if you're already collecting them
);

if (analysis) {
  await supabase.from("leads").update({
    status: analysis.outcome,
    crm_stage: analysis.crm_stage,
    crm_probability: analysis.crm_probability,
  }).eq("id", lead.id);

  if (analysis.next_best_action.channel === "email") {
    // hand off to cockpit's existing Resend integration, or trigger
    // it directly from the worker if that's already wired
  }
  if (hubspotEnabled) {
    await pushToHubSpot(lead, analysis); // existing optional HubSpot push
  }
}
```

## 5. Data mapping (Apollo.io → ORVYRA `ProspectInput`)

| Apollo.io / Supabase `leads` field | ORVYRA `ProspectInput` field |
|---|---|
| `name` / `full_name` | `name` |
| `organization.name` | `company` |
| `email` | `email` |
| `linkedin_url` | `linkedin_url` |
| `organization.website_url` | `company_url` |
| `title` | `role_hint` (separate param, not part of the packet identity) |

## 6. Deployment checklist

- [ ] ORVYRA deployed on Railway with `ANTHROPIC_API_KEY` and `ORVYRA_API_KEY` set (Postgres + Redis add-ons per the locked tech stack, once storage moves off in-process dict)
- [ ] `ORVYRA_API_URL` + `ORVYRA_API_KEY` added to worker's Vultr env
- [ ] `orvyra_prospect_id` and any status columns added to Supabase `leads` table
- [ ] `worker/src/orvyra/client.ts` added, imported at the pre-dial and post-transcript call sites
- [ ] Confirm `lobster-trap` runs on anything from `packet.company_context` / `packet.opportunity` before it reaches the live prompt
- [ ] Smoke test: one real lead through the full loop — pre-call → dial → transcript → post-call → Supabase updated → (optional) HubSpot updated

## 7. What's intentionally not wired yet

Real-time mid-call queries (ORVYRA stage 6 in the PRD) — the worker
already has a live Twilio Media Stream and an LLM in the loop, so
that endpoint is buildable next, but get stages 1–5 and 7–8 proven
on real calls first.
