/**
 * ORVYRA client — drop this into the Klesos worker at
 * worker/src/orvyra/client.ts
 *
 * Uses `undici` and `zod`, both already in worker/package.json —
 * no new dependencies required.
 *
 * Env vars required (add to worker/.env and Vultr deployment config):
 *   ORVYRA_API_URL   e.g. https://orvyra-production.up.railway.app
 *   ORVYRA_API_KEY   the same value set as ORVYRA_API_KEY on the ORVYRA
 *                    service (Railway env vars) — generate with
 *                    `openssl rand -hex 32`, set it in both places
 */

import { request } from "undici";
import { z } from "zod";

const ORVYRA_API_URL = process.env.ORVYRA_API_URL!;
const ORVYRA_API_KEY = process.env.ORVYRA_API_KEY!;

if (!ORVYRA_API_URL || !ORVYRA_API_KEY) {
  throw new Error("ORVYRA_API_URL and ORVYRA_API_KEY must be set");
}

// ---- Schemas mirroring the Pydantic models in storage/models.py ----
// Keep these two files in sync manually for now; if the contract
// starts drifting, generate this from ORVYRA's OpenAPI schema instead
// (FastAPI serves it at /openapi.json for free).

const EvidenceSourceSchema = z.object({
  source_id: z.string(),
  url: z.string().nullable(),
  source_type: z.string(),
  retrieval_time: z.string(),
  excerpt: z.string().nullable(),
  confidence: z.number(),
});

export const ProductContextSchema = z.object({
  name: z.string(),
  description: z.string(),
  target_customers: z.array(z.string()).optional(),
  value_propositions: z.array(z.string()).optional(),
});
export type ProductContext = z.infer<typeof ProductContextSchema>;

const ClaimSchema = z.object({
  claim: z.string(),
  type: z.enum(["fact", "inference"]),
  confidence: z.number(),
  evidence: z.array(EvidenceSourceSchema),
});

const OpportunitySchema = z.object({
  primary_problem: z.string().nullable(),
  confidence: z.number(),
  value_hypothesis: z.string().nullable(),
  likely_objections: z.array(z.string()),
  recommended_angle: z.string().nullable(),
  pursue: z.boolean(),
  reason_if_not_pursue: z.string().nullable(),
});

const ConversationStrategySchema = z.object({
  objective: z.string(),
  opening_angle: z.string().nullable(),
  discovery_questions: z.array(z.string()),
  proof_points: z.array(z.string()),
  avoid: z.array(z.string()),
}).nullable();

export const IntelligencePacketSchema = z.object({
  schema_version: z.string(),
  packet_id: z.string(),
  trace_id: z.string(),
  prospect_id: z.string(),
  status: z.string(),
  valid_until: z.string().nullable(),
  warnings: z.array(z.string()),
  sources: z.array(EvidenceSourceSchema),
  identity: z.object({
    name: z.string(),
    company: z.string().nullable(),
    email: z.string().nullable(),
    linkedin_url: z.string().nullable(),
    company_url: z.string().nullable(),
  }),
  company_context: z.object({
    name: z.string().nullable(),
    industry: z.string().nullable(),
    business_model: z.string().nullable(),
    estimated_size: z.string().nullable(),
    recent_signals: z.array(z.string()),
  }),
  person_context: z.object({
    role: z.string().nullable(),
    seniority: z.string().nullable(),
    responsibilities: z.array(z.string()),
    probable_priorities: z.array(ClaimSchema),
  }),
  facts: z.array(ClaimSchema),
  signals: z.array(z.string()),
  opportunity: OpportunitySchema,
  conversation_strategy: ConversationStrategySchema,
  previous_interactions: z.array(z.record(z.unknown())),
  created_at: z.string(),
});
export type IntelligencePacket = z.infer<typeof IntelligencePacketSchema>;

export const CallAnalysisSchema = z.object({
  conversation_id: z.string(),
  prospect_id: z.string(),
  outcome: z.string(),
  intent_score: z.number(),
  signals: z.array(z.string()),
  objections: z.array(z.string()),
  next_best_action: z.object({
    action: z.string(),
    channel: z.string().nullable(),
    recommended_send_time: z.string().nullable(),
    delay_hours: z.number().nullable(),
  }),
  crm_stage: z.string(),
  crm_probability: z.number(),
});
export type CallAnalysis = z.infer<typeof CallAnalysisSchema>;

// ---- Client ----

interface ProspectInput {
  name: string;
  company?: string;
  email?: string;
  linkedin_url?: string;
  company_url?: string;
}

async function orvyraPost<T>(path: string, body: unknown, schema: z.ZodType<T>, timeoutMs = 8000): Promise<T> {
  const { statusCode, body: resBody } = await request(`${ORVYRA_API_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${ORVYRA_API_KEY}`,
    },
    body: JSON.stringify(body),
    headersTimeout: timeoutMs,
    bodyTimeout: timeoutMs,
  });

  const json = await resBody.json();

  if (statusCode >= 400) {
    throw new Error(`ORVYRA ${path} returned ${statusCode}: ${JSON.stringify(json)}`);
  }
  return schema.parse(json);
}

/** Call before dialing. Returns null (and logs) on failure — a
 * broken ORVYRA call must never block Klesos from placing the call;
 * fail open to "call cold" rather than fail closed. */
export async function preCall(
  prospect: ProspectInput,
  objective: string,
  roleHint?: string,
  productContext?: ProductContext
): Promise<IntelligencePacket | null> {
  try {
    return await orvyraPost(
      "/v1/intelligence/pre-call",
      { prospect, objective, product: "Klesos", product_context: productContext, role_hint: roleHint },
      IntelligencePacketSchema
    );
  } catch (err) {
    console.error("[orvyra] pre-call failed, proceeding without a packet:", err);
    return null;
  }
}


/** Call after the transcript is finalized. Non-blocking is fine here too —
 * queue a retry if you want post-call analysis to be reliable, since a
 * missed post-call means the memory never gets the outcome. */
export async function postCall(
  conversationId: string,
  prospectId: string,
  transcript: string,
  events: { type: string; detail: string }[] = []
): Promise<CallAnalysis | null> {
  try {
    return await orvyraPost(
      "/v1/intelligence/post-call",
      { conversation_id: conversationId, prospect_id: prospectId, transcript, events },
      CallAnalysisSchema
    );
  } catch (err) {
    console.error("[orvyra] post-call failed:", err);
    return null;
  }
}

export const JobStatusSchema = z.object({
  job_id: z.string(),
  prospect_id: z.string(),
  status: z.enum(["pending", "enriching", "ready", "partial", "failed", "needs_review"]),
  error: z.string().nullable(),
});
export type JobStatus = z.infer<typeof JobStatusSchema>;

/** Pre-warm intelligence packets asynchronously for a batch of leads. */
export async function enrichLeads(
  leads: Array<{ prospect: ProspectInput; objective: string; roleHint?: string; productContext?: ProductContext }>
): Promise<JobStatus[] | null> {
  try {
    const body = leads.map((l) => ({
      prospect: l.prospect,
      objective: l.objective,
      product: "Klesos",
      product_context: l.productContext,
      role_hint: l.roleHint,
    }));
    return await orvyraPost("/v1/prospects/enrich", body, z.array(JobStatusSchema));
  } catch (err) {
    console.error("[orvyra] enrichLeads failed:", err);
    return null;
  }
}

/** Check status of a background enrichment job. */
export async function getEnrichmentJobStatus(jobId: string): Promise<JobStatus | null> {
  try {
    const { statusCode, body: resBody } = await request(`${ORVYRA_API_URL}/v1/enrichment-jobs/${jobId}`, {
      method: "GET",
      headers: { Authorization: `Bearer ${ORVYRA_API_KEY}` },
    });
    const json = await resBody.json();
    if (statusCode >= 400) {
      throw new Error(`ORVYRA GET /v1/enrichment-jobs/${jobId} returned ${statusCode}`);
    }
    return JobStatusSchema.parse(json);
  } catch (err) {
    console.error("[orvyra] getEnrichmentJobStatus failed:", err);
    return null;
  }
}

export const DecisionOverrideSchema = z.object({
  override_id: z.string(),
  prospect_id: z.string(),
  packet_id: z.string().nullable(),
  pursue: z.boolean(),
  reason: z.string(),
  operator_id: z.string(),
  created_at: z.string().nullable(),
});
export type DecisionOverride = z.infer<typeof DecisionOverrideSchema>;

/** Override an automated pursue decision for a prospect. Fail-open pattern. */
export async function overrideDecision(
  prospectId: string,
  pursue: boolean,
  reason: string
): Promise<DecisionOverride | null> {
  try {
    const { statusCode, body: resBody } = await request(`${ORVYRA_API_URL}/v1/intelligence/prospects/${prospectId}/decision`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${ORVYRA_API_KEY}`,
      },
      body: JSON.stringify({ pursue, reason }),
    });
    const json = await resBody.json();
    if (statusCode >= 400) {
      throw new Error(`ORVYRA PATCH /v1/intelligence/prospects/${prospectId}/decision returned ${statusCode}`);
    }
    return DecisionOverrideSchema.parse(json);
  } catch (err) {
    console.error("[orvyra] overrideDecision failed:", err);
    return null;
  }
}


