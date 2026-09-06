"""
Intelligence Memory — Durable Postgres/SQLAlchemy backed intelligence memory graph.
Maintains exact same interface signatures as MVP in-memory dict.
"""

from __future__ import annotations
import json
import datetime
from typing import Optional
from sqlalchemy import select, delete, desc
from storage.db import SessionLocal, engine, Base
from storage.sql_models import (
    ProspectModel, IntelligencePacketModel, IdentityModel,
    CallAnalysisModel, ConversationModel, CallEventModel,
    AuditLogModel, ClaimModel, SourceDocumentModel, ClaimEvidenceModel,
    CompanyModel, OperatorOverrideModel
)
from storage.models import IntelligencePacket, CallAnalysis, new_id


class IntelligenceMemory:
    def __init__(self) -> None:
        # Ensure database tables exist (safeguard for test/dev initialization)
        Base.metadata.create_all(bind=engine)

    def save_packet(self, packet: IntelligencePacket) -> None:
        db = SessionLocal()
        try:
            # 1. Upsert Prospect record
            prospect_name = packet.identity.get_effective_name() if hasattr(packet.identity, "get_effective_name") else (packet.identity.name or packet.identity.company or "Unknown Prospect")
            prospect = db.query(ProspectModel).filter_by(prospect_id=packet.prospect_id).first()
            if not prospect:
                prospect = ProspectModel(
                    prospect_id=packet.prospect_id,
                    name=prospect_name,
                    email=packet.identity.email,
                    linkedin_url=packet.identity.linkedin_url,
                    company_url=packet.identity.company_url,
                    created_at=packet.created_at,
                )
                db.add(prospect)
            else:
                prospect.name = prospect_name
                prospect.email = packet.identity.email or prospect.email
                prospect.linkedin_url = packet.identity.linkedin_url or prospect.linkedin_url
                prospect.company_url = packet.identity.company_url or prospect.company_url

            # 2. Upsert Company record if company context exists
            if packet.company_context and packet.company_context.name:
                comp_name = packet.company_context.name[:250]
                company = db.query(CompanyModel).filter_by(name=comp_name).first()
                if not company:
                    company = CompanyModel(
                        company_id=new_id("comp"),
                        name=comp_name,
                        company_url=packet.identity.company_url[:500] if packet.identity.company_url else None,
                        industry=packet.company_context.industry,
                        business_model=packet.company_context.business_model[:100] if packet.company_context.business_model else None,
                        estimated_size=packet.company_context.estimated_size[:100] if packet.company_context.estimated_size else None,
                    )
                    db.add(company)

            # 3. Add Identity resolution keys
            if packet.identity.email:
                key_val = packet.identity.email.lower().strip()
                id_rec = db.query(IdentityModel).filter_by(key_value=key_val).first()
                if not id_rec:
                    db.add(
                        IdentityModel(
                            identity_id=new_id("id"),
                            prospect_id=packet.prospect_id,
                            key_type="email",
                            key_value=key_val,
                            company_name=packet.identity.company,
                        )
                    )
                else:
                    id_rec.prospect_id = packet.prospect_id
                    if packet.identity.company:
                        id_rec.company_name = packet.identity.company
            if packet.identity.linkedin_url:
                key_val = packet.identity.linkedin_url.lower().strip()
                id_rec = db.query(IdentityModel).filter_by(key_value=key_val).first()
                if not id_rec:
                    db.add(
                        IdentityModel(
                            identity_id=new_id("id"),
                            prospect_id=packet.prospect_id,
                            key_type="linkedin_url",
                            key_value=key_val,
                            company_name=packet.identity.company,
                        )
                    )
                else:
                    id_rec.prospect_id = packet.prospect_id
                    if packet.identity.company:
                        id_rec.company_name = packet.identity.company
            if packet.identity.name and packet.identity.company:
                key_val = f"{packet.identity.name.lower().strip()}|{packet.identity.company.lower().strip()}"
                id_rec = db.query(IdentityModel).filter_by(key_value=key_val).first()
                if not id_rec:
                    db.add(
                        IdentityModel(
                            identity_id=new_id("id"),
                            prospect_id=packet.prospect_id,
                            key_type="name_company",
                            key_value=key_val,
                            company_name=packet.identity.company,
                        )
                    )
                else:
                    id_rec.prospect_id = packet.prospect_id
                    if packet.identity.company:
                        id_rec.company_name = packet.identity.company

            # 4. Save versioned Intelligence Packet record
            packet_json_str = json.dumps(packet.model_dump(mode="json"))
            pkt_model = IntelligencePacketModel(
                packet_id=packet.packet_id,
                prospect_id=packet.prospect_id,
                schema_version=packet.schema_version,
                status=packet.status,
                valid_until=packet.valid_until,
                packet_json=packet_json_str,
                created_at=packet.created_at,
            )
            db.merge(pkt_model)

            # 5. Save Claims and Sources
            for claim in packet.facts:
                claim_rec = ClaimModel(
                    claim_id=new_id("clm"),
                    prospect_id=packet.prospect_id,
                    claim_text=claim.claim,
                    claim_type=str(claim.type),
                    confidence=claim.confidence,
                )
                db.add(claim_rec)
                db.flush()

                for ev in claim.evidence:
                    db.add(
                        ClaimEvidenceModel(
                            evidence_id=new_id("ev"),
                            claim_id=claim_rec.claim_id,
                            url=ev.url,
                            source_type=ev.source_type,
                            excerpt=ev.excerpt,
                            confidence=ev.confidence,
                        )
                    )

            # 6. Audit Log
            db.add(
                AuditLogModel(
                    audit_id=new_id("audit"),
                    entity_type="intelligence_packet",
                    entity_id=packet.packet_id,
                    action="save_packet",
                    payload_json=json.dumps({"prospect_id": packet.prospect_id, "status": packet.status}),
                )
            )

            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_packet(self, prospect_id: str) -> Optional[IntelligencePacket]:
        db = SessionLocal()
        try:
            pkt_rec = (
                db.query(IntelligencePacketModel)
                .filter_by(prospect_id=prospect_id)
                .order_by(desc(IntelligencePacketModel.created_at))
                .first()
            )
            if not pkt_rec:
                return None
            data = json.loads(pkt_rec.packet_json)
            return IntelligencePacket.model_validate(data)
        finally:
            db.close()

    def find_by_identity(self, email: str | None, linkedin_url: str | None) -> Optional[IntelligencePacket]:
        db = SessionLocal()
        try:
            prospect_id: str | None = None

            if email:
                key_val = email.lower().strip()
                id_rec = db.query(IdentityModel).filter_by(key_value=key_val).first()
                if id_rec:
                    prospect_id = id_rec.prospect_id

            if not prospect_id and linkedin_url:
                key_val = linkedin_url.lower().strip()
                id_rec = db.query(IdentityModel).filter_by(key_value=key_val).first()
                if id_rec:
                    prospect_id = id_rec.prospect_id

            if prospect_id:
                return self.get_packet(prospect_id)

            return None
        finally:
            db.close()

    def record_call(self, analysis: CallAnalysis) -> None:
        db = SessionLocal()
        try:
            analysis_json_str = json.dumps(analysis.model_dump(mode="json"))

            # Ensure Conversation record exists
            conv = db.query(ConversationModel).filter_by(conversation_id=analysis.conversation_id).first()
            if not conv:
                conv = ConversationModel(
                    conversation_id=analysis.conversation_id,
                    prospect_id=analysis.prospect_id,
                )
                db.add(conv)

            # Save CallAnalysisModel
            outcome_text = getattr(analysis, "outcome_summary", getattr(analysis, "outcome", None))
            analysis_model = CallAnalysisModel(
                analysis_id=new_id("ana"),
                conversation_id=analysis.conversation_id,
                prospect_id=analysis.prospect_id,
                outcome_summary=outcome_text,
                analysis_json=analysis_json_str,
                created_at=getattr(analysis, "created_at", datetime.datetime.now(datetime.timezone.utc)),
            )
            db.add(analysis_model)

            # Save Audit Log
            db.add(
                AuditLogModel(
                    audit_id=new_id("audit"),
                    entity_type="call_analysis",
                    entity_id=analysis.conversation_id,
                    action="record_call",
                    payload_json=json.dumps({"prospect_id": analysis.prospect_id}),
                )
            )

            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_history(self, prospect_id: str) -> list[CallAnalysis]:
        db = SessionLocal()
        try:
            recs = (
                db.query(CallAnalysisModel)
                .filter_by(prospect_id=prospect_id)
                .order_by(CallAnalysisModel.created_at)
                .all()
            )
            return [CallAnalysis.model_validate(json.loads(r.analysis_json)) for r in recs]
        finally:
            db.close()

    def list_packets(self) -> list[IntelligencePacket]:
        db = SessionLocal()
        try:
            recs = (
                db.query(IntelligencePacketModel)
                .order_by(desc(IntelligencePacketModel.created_at))
                .all()
            )
            seen_prospects: set[str] = set()
            packets: list[IntelligencePacket] = []
            for r in recs:
                if r.prospect_id not in seen_prospects:
                    seen_prospects.add(r.prospect_id)
                    packets.append(IntelligencePacket.model_validate(json.loads(r.packet_json)))
            return packets
        finally:
            db.close()

    def list_calls(self) -> list[CallAnalysis]:
        db = SessionLocal()
        try:
            recs = (
                db.query(CallAnalysisModel)
                .order_by(desc(CallAnalysisModel.created_at))
                .all()
            )
            return [CallAnalysis.model_validate(json.loads(r.analysis_json)) for r in recs]
        finally:
            db.close()

    def save_override(self, prospect_id: str, pursue: bool, reason: str, operator_id: str | None = None) -> dict:
        db = SessionLocal()
        try:
            prospect = db.query(ProspectModel).filter_by(prospect_id=prospect_id).first()
            if not prospect:
                pkt = (
                    db.query(IntelligencePacketModel)
                    .filter_by(prospect_id=prospect_id)
                    .order_by(desc(IntelligencePacketModel.created_at))
                    .first()
                )
                if not pkt:
                    raise ValueError(f"Prospect '{prospect_id}' not found")
                pkt_data = json.loads(pkt.packet_json)
                ident = pkt_data.get("identity", {})
                prospect = ProspectModel(
                    prospect_id=prospect_id,
                    name=ident.get("name") or ident.get("company") or "Unknown Prospect",
                    email=ident.get("email"),
                    linkedin_url=ident.get("linkedin_url"),
                    company_url=ident.get("company_url"),
                )
                db.add(prospect)
                db.flush()

            pkt_rec = (
                db.query(IntelligencePacketModel)
                .filter_by(prospect_id=prospect_id)
                .order_by(desc(IntelligencePacketModel.created_at))
                .first()
            )
            packet_id = pkt_rec.packet_id if pkt_rec else None

            override_id = new_id("ovr")
            ovr_model = OperatorOverrideModel(
                override_id=override_id,
                prospect_id=prospect_id,
                packet_id=packet_id,
                override_pursue=pursue,
                reason=reason,
                operator_id=operator_id or "operator",
            )
            db.add(ovr_model)

            db.add(
                AuditLogModel(
                    audit_id=new_id("audit"),
                    entity_type="operator_override",
                    entity_id=override_id,
                    action="override_decision",
                    payload_json=json.dumps({"prospect_id": prospect_id, "pursue": pursue, "reason": reason}),
                )
            )

            db.commit()
            return {
                "override_id": override_id,
                "prospect_id": prospect_id,
                "packet_id": packet_id,
                "pursue": pursue,
                "reason": reason,
                "operator_id": operator_id or "operator",
                "created_at": ovr_model.created_at.isoformat() if ovr_model.created_at else None,
            }
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_override(self, prospect_id: str) -> dict | None:
        db = SessionLocal()
        try:
            ovr = (
                db.query(OperatorOverrideModel)
                .filter_by(prospect_id=prospect_id)
                .order_by(desc(OperatorOverrideModel.created_at))
                .first()
            )
            if not ovr:
                return None
            return {
                "override_id": ovr.override_id,
                "prospect_id": ovr.prospect_id,
                "packet_id": ovr.packet_id,
                "pursue": ovr.override_pursue,
                "reason": ovr.reason,
                "operator_id": ovr.operator_id,
                "created_at": ovr.created_at.isoformat() if ovr.created_at else None,
            }
        finally:
            db.close()

    def clear(self) -> None:
        db = SessionLocal()
        try:
            for table in reversed(Base.metadata.sorted_tables):
                db.execute(delete(table))
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


memory = IntelligenceMemory()
