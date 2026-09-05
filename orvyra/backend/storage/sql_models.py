from __future__ import annotations
import datetime
from sqlalchemy import (
    Column, String, Text, Float, Boolean, DateTime, ForeignKey, Integer, Index
)
from sqlalchemy.orm import relationship
from storage.db import Base, DATABASE_URL

try:
    from pgvector.sqlalchemy import Vector
    VectorType = Vector(1536) if not DATABASE_URL.startswith("sqlite") else Text
except Exception:
    VectorType = Text


class ClientModel(Base):
    __tablename__ = "clients"

    client_id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))


class ProspectModel(Base):
    __tablename__ = "prospects"

    prospect_id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True, index=True)
    linkedin_url = Column(String(512), nullable=True, index=True)
    company_url = Column(String(512), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))

    identities = relationship("IdentityModel", back_populates="prospect", cascade="all, delete-orphan")
    packets = relationship("IntelligencePacketModel", back_populates="prospect", cascade="all, delete-orphan")
    runs = relationship("EnrichmentRunModel", back_populates="prospect", cascade="all, delete-orphan")


class CompanyModel(Base):
    __tablename__ = "companies"

    company_id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    company_url = Column(String(512), nullable=True, index=True)
    industry = Column(String(255), nullable=True)
    business_model = Column(String(100), nullable=True)
    estimated_size = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))


class IdentityModel(Base):
    __tablename__ = "identities"

    identity_id = Column(String(64), primary_key=True)
    prospect_id = Column(String(64), ForeignKey("prospects.prospect_id", ondelete="CASCADE"), nullable=False, index=True)
    key_type = Column(String(50), nullable=False)  # e.g. email, linkedin_url, domain, name_company
    key_value = Column(String(512), nullable=False, index=True)
    company_name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))

    prospect = relationship("ProspectModel", back_populates="identities")


class SourceDocumentModel(Base):
    __tablename__ = "source_documents"

    doc_id = Column(String(64), primary_key=True)
    url = Column(String(512), nullable=False, index=True)
    retrieved_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))
    content_hash = Column(String(64), nullable=True)
    clean_text = Column(Text, nullable=True)
    title = Column(String(512), nullable=True)
    trust_level = Column(Float, default=1.0)
    status = Column(String(50), default="success")
    error = Column(Text, nullable=True)
    embedding = Column(VectorType, nullable=True)


class ClaimModel(Base):
    __tablename__ = "claims"

    claim_id = Column(String(64), primary_key=True)
    prospect_id = Column(String(64), ForeignKey("prospects.prospect_id", ondelete="CASCADE"), nullable=True, index=True)
    subject_id = Column(String(64), nullable=True)
    predicate = Column(String(255), nullable=True)
    value = Column(Text, nullable=True)
    claim_text = Column(Text, nullable=False)
    claim_type = Column(String(50), nullable=False)  # fact or inference
    confidence = Column(Float, default=0.8)
    embedding = Column(VectorType, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))

    evidence = relationship("ClaimEvidenceModel", back_populates="claim", cascade="all, delete-orphan")


class ClaimEvidenceModel(Base):
    __tablename__ = "claim_evidence"

    evidence_id = Column(String(64), primary_key=True)
    claim_id = Column(String(64), ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    source_document_id = Column(String(64), ForeignKey("source_documents.doc_id", ondelete="SET NULL"), nullable=True)
    url = Column(String(512), nullable=True)
    source_type = Column(String(50), default="website_scrape")
    excerpt = Column(Text, nullable=True)
    confidence = Column(Float, default=1.0)

    claim = relationship("ClaimModel", back_populates="evidence")


class EnrichmentRunModel(Base):
    __tablename__ = "enrichment_runs"

    run_id = Column(String(64), primary_key=True)
    prospect_id = Column(String(64), ForeignKey("prospects.prospect_id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String(64), nullable=True, index=True)
    started_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default="pending")  # pending, enriching, ready, partial, failed, needs_review
    error = Column(Text, nullable=True)

    prospect = relationship("ProspectModel", back_populates="runs")


class IntelligencePacketModel(Base):
    __tablename__ = "intelligence_packets"

    packet_id = Column(String(64), primary_key=True)
    prospect_id = Column(String(64), ForeignKey("prospects.prospect_id", ondelete="CASCADE"), nullable=False, index=True)
    schema_version = Column(String(20), default="1.0.0")
    status = Column(String(50), default="ready")
    valid_until = Column(DateTime(timezone=True), nullable=True)
    packet_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))

    prospect = relationship("ProspectModel", back_populates="packets")


class ConversationModel(Base):
    __tablename__ = "conversations"

    conversation_id = Column(String(64), primary_key=True)
    prospect_id = Column(String(64), ForeignKey("prospects.prospect_id", ondelete="CASCADE"), nullable=False, index=True)
    packet_id = Column(String(64), ForeignKey("intelligence_packets.packet_id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))

    events = relationship("CallEventModel", back_populates="conversation", cascade="all, delete-orphan")
    analyses = relationship("CallAnalysisModel", back_populates="conversation", cascade="all, delete-orphan")


class CallEventModel(Base):
    __tablename__ = "call_events"

    event_id = Column(String(64), primary_key=True)
    conversation_id = Column(String(64), ForeignKey("conversations.conversation_id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(100), nullable=False)
    detail = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))

    conversation = relationship("ConversationModel", back_populates="events")


class CallAnalysisModel(Base):
    __tablename__ = "call_analyses"

    analysis_id = Column(String(64), primary_key=True)
    conversation_id = Column(String(64), ForeignKey("conversations.conversation_id", ondelete="CASCADE"), nullable=False, index=True)
    prospect_id = Column(String(64), ForeignKey("prospects.prospect_id", ondelete="CASCADE"), nullable=False, index=True)
    outcome_summary = Column(Text, nullable=True)
    analysis_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))

    conversation = relationship("ConversationModel", back_populates="analyses")
    objections = relationship("ObjectionModel", back_populates="analysis", cascade="all, delete-orphan")
    next_actions = relationship("NextActionModel", back_populates="analysis", cascade="all, delete-orphan")


class ObjectionModel(Base):
    __tablename__ = "objections"

    objection_id = Column(String(64), primary_key=True)
    analysis_id = Column(String(64), ForeignKey("call_analyses.analysis_id", ondelete="CASCADE"), nullable=False, index=True)
    objection_text = Column(Text, nullable=False)
    embedding = Column(VectorType, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))

    analysis = relationship("CallAnalysisModel", back_populates="objections")


class NextActionModel(Base):
    __tablename__ = "next_actions"

    action_id = Column(String(64), primary_key=True)
    analysis_id = Column(String(64), ForeignKey("call_analyses.analysis_id", ondelete="CASCADE"), nullable=False, index=True)
    action_text = Column(Text, nullable=False)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))

    analysis = relationship("CallAnalysisModel", back_populates="next_actions")


class OperatorOverrideModel(Base):
    __tablename__ = "operator_overrides"

    override_id = Column(String(64), primary_key=True)
    prospect_id = Column(String(64), ForeignKey("prospects.prospect_id", ondelete="CASCADE"), nullable=False, index=True)
    packet_id = Column(String(64), ForeignKey("intelligence_packets.packet_id", ondelete="SET NULL"), nullable=True)
    override_pursue = Column(Boolean, nullable=False)
    reason = Column(Text, nullable=True)
    operator_id = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    audit_id = Column(String(64), primary_key=True)
    entity_type = Column(String(100), nullable=False)  # prospect, packet, override, etc.
    entity_id = Column(String(64), nullable=False, index=True)
    action = Column(String(50), nullable=False)        # create, update, override, delete
    payload_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))
