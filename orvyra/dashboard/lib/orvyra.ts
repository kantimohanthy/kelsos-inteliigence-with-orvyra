const ORVYRA_API_URL = process.env.ORVYRA_API_URL ?? "http://127.0.0.1:8009";
const ORVYRA_API_KEY = process.env.ORVYRA_API_KEY ?? "";

export interface EvidenceSource {
  source_id: string;
  url: string | null;
  source_type: string;
  retrieval_time: string;
  excerpt: string | null;
  confidence: number;
}

export interface ProductContext {
  name: string;
  description: string;
  target_customers?: string[];
  value_propositions?: string[];
}

export interface Claim {

  claim: string;
  type: "fact" | "inference";
  confidence: number;
  evidence: EvidenceSource[];
}

export interface IntelligencePacket {
  schema_version: string;
  packet_id: string;
  trace_id: string;
  prospect_id: string;
  status: string;
  valid_until: string | null;
  warnings: string[];
  sources: EvidenceSource[];
  identity: {
    name: string;
    company: string | null;
    email: string | null;
    linkedin_url: string | null;
    company_url: string | null;
  };
  company_context: {
    name: string | null;
    industry: string | null;
    business_model: string | null;
    estimated_size: string | null;
    recent_signals: string[];
  };
  person_context: {
    role: string | null;
    seniority: string | null;
    responsibilities: string[];
    probable_priorities: Claim[];
  };
  facts: Claim[];
  signals: string[];
  opportunity: {
    primary_problem: string | null;
    confidence: number;
    value_hypothesis: string | null;
    likely_objections: string[];
    recommended_angle: string | null;
    pursue: boolean;
    reason_if_not_pursue: string | null;
  };
  conversation_strategy: {
    objective: string;
    opening_angle: string | null;
    discovery_questions: string[];
    proof_points: string[];
    avoid: string[];
  } | null;
  previous_interactions: Record<string, unknown>[];
  created_at: string;
}

export interface CallAnalysis {
  conversation_id: string;
  prospect_id: string;
  outcome: string;
  intent_score: number;
  signals: string[];
  objections: string[];
  next_best_action: {
    action: string;
    channel: string | null;
    recommended_send_time: string | null;
    delay_hours: number | null;
  };
  crm_stage: string;
  crm_probability: number;
}

async function orvyraGet<T>(path: string): Promise<T> {
  const res = await fetch(`${ORVYRA_API_URL}${path}`, {
    headers: { Authorization: `Bearer ${ORVYRA_API_KEY}` },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`ORVYRA ${path} returned ${res.status}`);
  }
  return res.json();
}

export const orvyra = {
  listProspects: () => orvyraGet<IntelligencePacket[]>("/v1/intelligence/prospects"),
  getProspect: (id: string) => orvyraGet<IntelligencePacket>(`/v1/intelligence/prospects/${id}`),
  getProspectHistory: (id: string) => orvyraGet<CallAnalysis[]>(`/v1/intelligence/prospects/${id}/history`),
  listCalls: () => orvyraGet<CallAnalysis[]>("/v1/intelligence/calls"),
};
