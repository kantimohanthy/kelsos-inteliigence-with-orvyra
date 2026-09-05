"""
ORVYRA Intelligence Protocol — core data model.

Every producer (ingestion, enrichment, reasoning) and every consumer
(Klesos, CRM, future clients) speaks this object. Keep it stable;
evolve the pipelines underneath it, not the shape of this contract.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import uuid
import datetime


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class ClaimType(str, Enum):
    FACT = "fact"
    INFERENCE = "inference"


class EvidenceSource(BaseModel):
    """Structured evidence provenance object replacing loose strings."""
    source_id: str = Field(default_factory=lambda: new_id("src"))
    url: Optional[str] = None
    source_type: str = "website_scrape"
    retrieval_time: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    excerpt: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ProductContext(BaseModel):
    """Product context supplied in pre-call request for contextual opportunity evaluation."""
    name: str
    description: str
    target_customers: list[str] = Field(default_factory=list)
    value_propositions: list[str] = Field(default_factory=list)


class SourceDocument(BaseModel):
    """Document fetched during crawler ingestion."""
    doc_id: str = Field(default_factory=lambda: new_id("doc"))
    url: str
    title: Optional[str] = None
    content: str
    retrieval_time: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    status: str = "success"
    error: Optional[str] = None




class Claim(BaseModel):
    """A single piece of intelligence, always tagged fact vs inference."""
    claim: str
    type: ClaimType
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[EvidenceSource] = Field(default_factory=list)


class ProspectInput(BaseModel):
    name: str
    company: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    company_url: Optional[str] = None


class CompanyContext(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    business_model: Optional[str] = None
    estimated_size: Optional[str] = None
    recent_signals: list[str] = Field(default_factory=list)


class PersonContext(BaseModel):
    role: Optional[str] = None
    seniority: Optional[str] = None
    responsibilities: list[str] = Field(default_factory=list)
    probable_priorities: list[Claim] = Field(default_factory=list)


class Opportunity(BaseModel):
    primary_problem: Optional[str] = None
    confidence: float = 0.0
    value_hypothesis: Optional[str] = None
    likely_objections: list[str] = Field(default_factory=list)
    recommended_angle: Optional[str] = None
    pursue: bool = True
    reason_if_not_pursue: Optional[str] = None


class ConversationStrategy(BaseModel):
    objective: str
    opening_angle: Optional[str] = None
    discovery_questions: list[str] = Field(default_factory=list)
    proof_points: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)


class IntelligencePacket(BaseModel):
    """The object every downstream application (Klesos included) consumes."""
    schema_version: str = "1.0.0"
    packet_id: str = Field(default_factory=lambda: new_id("pkt"))
    trace_id: str = Field(default_factory=lambda: new_id("trace"))
    prospect_id: str = Field(default_factory=lambda: new_id("prospect"))
    status: str = "generated"
    valid_until: Optional[datetime.datetime] = None
    warnings: list[str] = Field(default_factory=list)
    sources: list[EvidenceSource] = Field(default_factory=list)
    identity: ProspectInput
    company_context: CompanyContext = Field(default_factory=CompanyContext)
    person_context: PersonContext = Field(default_factory=PersonContext)
    facts: list[Claim] = Field(default_factory=list)
    signals: list[str] = Field(default_factory=list)
    opportunity: Opportunity = Field(default_factory=lambda: Opportunity(primary_problem=None))
    conversation_strategy: Optional[ConversationStrategy] = None
    previous_interactions: list[dict] = Field(default_factory=list)
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))



class CallEvent(BaseModel):
    type: str
    detail: str


class PostCallInput(BaseModel):
    conversation_id: str
    prospect_id: str
    transcript: str
    events: list[CallEvent] = Field(default_factory=list)


class NextAction(BaseModel):
    action: str
    channel: Optional[str] = None
    recommended_send_time: Optional[str] = None
    delay_hours: Optional[float] = None


class CallAnalysis(BaseModel):
    conversation_id: str
    prospect_id: str
    outcome: str
    intent_score: float
    signals: list[str] = Field(default_factory=list)
    objections: list[str] = Field(default_factory=list)
    next_best_action: NextAction
    crm_stage: str
    crm_probability: float

