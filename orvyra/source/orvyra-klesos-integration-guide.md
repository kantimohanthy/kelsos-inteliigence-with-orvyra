# Integration Guide — Plugging ORVYRA into Klesos

**Scope:** exactly how the ORVYRA endpoints wire into the real
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

- ORVYRA requires `Authorization: Bearer <ORVYRA_API_KEY>` on
  `/v1/intelligence/*` routes. `/health` stays open for uptime checks.
- Generate one value: `openssl rand -hex 32`.
- Set it as `ORVYRA_API_KEY` in **two** places:
  - Railway env vars (ORVYRA service)
  - Vultr / worker `.env` (Klesos worker) — same value, new name is fine (`ORVYRA_API_KEY` on both sides keeps it unambiguous)
- Also set `ORVYRA_API_URL` on the worker to ORVYRA's Railway URL.

## 3. The worker-side client

Drop `source/klesos-worker-orvyra-client.ts` into
`worker/src/orvyra/client.ts` in the `deals-machine` repo. It:

- Uses `undici` and `zod` — both already worker dependencies, nothing new to install.
- Validates ORVYRA's response shape against the same contract the Pydantic models define.
- **Fails open**: if ORVYRA is down or times out, `preCall()` returns `null` and the worker proceeds without a packet rather than blocking the dial.

## 4. Exact call sites

### 4.1 Before the Twilio dial

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

await supabase.from("leads").update({ orvyra_prospect_id: packet?.prospect_id ?? null }).eq("id", lead.id);
```

### 4.2 Feeding the strategy into the live conversation

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

### 4.3 After the call — post-call analysis

```ts
import { postCall } from "./orvyra/client";

const analysis = await postCall(
  callSid,
  lead.orvyra_prospect_id,
  finalTranscript,
  events
);
```

## 5. Data mapping (Apollo.io → ORVYRA `ProspectInput`)

| Apollo.io / Supabase `leads` field | ORVYRA `ProspectInput` field |
|---|---|
| `name` / `full_name` | `name` |
| `organization.name` | `company` |
| `email` | `email` |
| `linkedin_url` | `linkedin_url` |
| `organization.website_url` | `company_url` |
| `title` | `role_hint` |

## 8. Batch Async Pre-Warming & Manual Decision Overrides

Kyle's worker can utilize three additional client functions exported from `client.ts`:

### 8.1 `enrichLeads(leads)`
Pre-warms intelligence packets asynchronously in background jobs for a batch of leads before scheduled calling blocks.
```ts
import { enrichLeads } from "./orvyra/client";

const jobs = await enrichLeads(newLeads.map(l => ({
  prospect: { name: l.name, company: l.company, company_url: l.website },
  objective: "Pre-warm lead batch"
})));
```

### 8.2 `getEnrichmentJobStatus(jobId)`
Polls or checks background enrichment status for a pre-warming job.
```ts
import { getEnrichmentJobStatus } from "./orvyra/client";

const status = await getEnrichmentJobStatus(jobId);
if (status?.status === "ready") {
  // Lead intelligence is ready
}
```

### 8.3 `overrideDecision(prospectId, pursue, reason)`
Records an operator's manual decision override for a prospect in ORVYRA's durable storage (`operator_overrides` table).
```ts
import { overrideDecision } from "./orvyra/client";

await overrideDecision("prospect_123", true, "Operator manually verified company fit with CEO");
```

## 6. Deployment checklist

- [ ] ORVYRA deployed on Railway with `ANTHROPIC_API_KEY` and `ORVYRA_API_KEY` set
- [ ] `ORVYRA_API_URL` + `ORVYRA_API_KEY` added to worker's Vultr env
- [ ] `orvyra_prospect_id` and any status columns added to Supabase `leads` table
- [ ] `worker/src/orvyra/client.ts` added, imported at pre-dial, post-transcript, and pre-warming call sites
- [ ] Smoke test: pre-call → dial → transcript → post-call → Supabase updated
