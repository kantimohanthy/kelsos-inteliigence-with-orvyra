"""initial_schema

Revision ID: a81f46d371de
Revises: 
Create Date: 2026-09-05 17:23:06.461862

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a81f46d371de'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table('audit_logs',
    sa.Column('audit_id', sa.String(length=64), nullable=False),
    sa.Column('entity_type', sa.String(length=100), nullable=False),
    sa.Column('entity_id', sa.String(length=64), nullable=False),
    sa.Column('action', sa.String(length=50), nullable=False),
    sa.Column('payload_json', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('audit_id')
    )
    op.create_index(op.f('ix_audit_logs_entity_id'), 'audit_logs', ['entity_id'], unique=False)
    op.create_table('clients',
    sa.Column('client_id', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('client_id')
    )
    op.create_table('companies',
    sa.Column('company_id', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('company_url', sa.String(length=512), nullable=True),
    sa.Column('industry', sa.String(length=255), nullable=True),
    sa.Column('business_model', sa.String(length=100), nullable=True),
    sa.Column('estimated_size', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('company_id')
    )
    op.create_index(op.f('ix_companies_company_url'), 'companies', ['company_url'], unique=False)
    op.create_table('prospects',
    sa.Column('prospect_id', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('linkedin_url', sa.String(length=512), nullable=True),
    sa.Column('company_url', sa.String(length=512), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('prospect_id')
    )
    op.create_index(op.f('ix_prospects_company_url'), 'prospects', ['company_url'], unique=False)
    op.create_index(op.f('ix_prospects_email'), 'prospects', ['email'], unique=False)
    op.create_index(op.f('ix_prospects_linkedin_url'), 'prospects', ['linkedin_url'], unique=False)
    op.create_table('source_documents',
    sa.Column('doc_id', sa.String(length=64), nullable=False),
    sa.Column('url', sa.String(length=512), nullable=False),
    sa.Column('retrieved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('content_hash', sa.String(length=64), nullable=True),
    sa.Column('clean_text', sa.Text(), nullable=True),
    sa.Column('title', sa.String(length=512), nullable=True),
    sa.Column('trust_level', sa.Float(), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=True),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('embedding', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('doc_id')
    )
    op.create_index(op.f('ix_source_documents_url'), 'source_documents', ['url'], unique=False)
    op.create_table('claims',
    sa.Column('claim_id', sa.String(length=64), nullable=False),
    sa.Column('prospect_id', sa.String(length=64), nullable=True),
    sa.Column('subject_id', sa.String(length=64), nullable=True),
    sa.Column('predicate', sa.String(length=255), nullable=True),
    sa.Column('value', sa.Text(), nullable=True),
    sa.Column('claim_text', sa.Text(), nullable=False),
    sa.Column('claim_type', sa.String(length=50), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=True),
    sa.Column('embedding', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['prospect_id'], ['prospects.prospect_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('claim_id')
    )
    op.create_index(op.f('ix_claims_prospect_id'), 'claims', ['prospect_id'], unique=False)
    op.create_table('enrichment_runs',
    sa.Column('run_id', sa.String(length=64), nullable=False),
    sa.Column('prospect_id', sa.String(length=64), nullable=False),
    sa.Column('job_id', sa.String(length=64), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=True),
    sa.Column('error', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['prospect_id'], ['prospects.prospect_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('run_id')
    )
    op.create_index(op.f('ix_enrichment_runs_job_id'), 'enrichment_runs', ['job_id'], unique=False)
    op.create_index(op.f('ix_enrichment_runs_prospect_id'), 'enrichment_runs', ['prospect_id'], unique=False)
    op.create_table('identities',
    sa.Column('identity_id', sa.String(length=64), nullable=False),
    sa.Column('prospect_id', sa.String(length=64), nullable=False),
    sa.Column('key_type', sa.String(length=50), nullable=False),
    sa.Column('key_value', sa.String(length=512), nullable=False),
    sa.Column('company_name', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['prospect_id'], ['prospects.prospect_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('identity_id')
    )
    op.create_index(op.f('ix_identities_key_value'), 'identities', ['key_value'], unique=False)
    op.create_index(op.f('ix_identities_prospect_id'), 'identities', ['prospect_id'], unique=False)
    op.create_table('intelligence_packets',
    sa.Column('packet_id', sa.String(length=64), nullable=False),
    sa.Column('prospect_id', sa.String(length=64), nullable=False),
    sa.Column('schema_version', sa.String(length=20), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=True),
    sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('packet_json', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['prospect_id'], ['prospects.prospect_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('packet_id')
    )
    op.create_index(op.f('ix_intelligence_packets_prospect_id'), 'intelligence_packets', ['prospect_id'], unique=False)
    op.create_table('claim_evidence',
    sa.Column('evidence_id', sa.String(length=64), nullable=False),
    sa.Column('claim_id', sa.String(length=64), nullable=False),
    sa.Column('source_document_id', sa.String(length=64), nullable=True),
    sa.Column('url', sa.String(length=512), nullable=True),
    sa.Column('source_type', sa.String(length=50), nullable=True),
    sa.Column('excerpt', sa.Text(), nullable=True),
    sa.Column('confidence', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['claim_id'], ['claims.claim_id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['source_document_id'], ['source_documents.doc_id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('evidence_id')
    )
    op.create_index(op.f('ix_claim_evidence_claim_id'), 'claim_evidence', ['claim_id'], unique=False)
    op.create_table('conversations',
    sa.Column('conversation_id', sa.String(length=64), nullable=False),
    sa.Column('prospect_id', sa.String(length=64), nullable=False),
    sa.Column('packet_id', sa.String(length=64), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['packet_id'], ['intelligence_packets.packet_id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['prospect_id'], ['prospects.prospect_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('conversation_id')
    )
    op.create_index(op.f('ix_conversations_packet_id'), 'conversations', ['packet_id'], unique=False)
    op.create_index(op.f('ix_conversations_prospect_id'), 'conversations', ['prospect_id'], unique=False)
    op.create_table('operator_overrides',
    sa.Column('override_id', sa.String(length=64), nullable=False),
    sa.Column('prospect_id', sa.String(length=64), nullable=False),
    sa.Column('packet_id', sa.String(length=64), nullable=True),
    sa.Column('override_pursue', sa.Boolean(), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('operator_id', sa.String(length=64), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['packet_id'], ['intelligence_packets.packet_id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['prospect_id'], ['prospects.prospect_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('override_id')
    )
    op.create_index(op.f('ix_operator_overrides_prospect_id'), 'operator_overrides', ['prospect_id'], unique=False)
    op.create_table('call_analyses',
    sa.Column('analysis_id', sa.String(length=64), nullable=False),
    sa.Column('conversation_id', sa.String(length=64), nullable=False),
    sa.Column('prospect_id', sa.String(length=64), nullable=False),
    sa.Column('outcome_summary', sa.Text(), nullable=True),
    sa.Column('analysis_json', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.conversation_id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['prospect_id'], ['prospects.prospect_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('analysis_id')
    )
    op.create_index(op.f('ix_call_analyses_conversation_id'), 'call_analyses', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_call_analyses_prospect_id'), 'call_analyses', ['prospect_id'], unique=False)
    op.create_table('call_events',
    sa.Column('event_id', sa.String(length=64), nullable=False),
    sa.Column('conversation_id', sa.String(length=64), nullable=False),
    sa.Column('type', sa.String(length=100), nullable=False),
    sa.Column('detail', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.conversation_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('event_id')
    )
    op.create_index(op.f('ix_call_events_conversation_id'), 'call_events', ['conversation_id'], unique=False)
    op.create_table('next_actions',
    sa.Column('action_id', sa.String(length=64), nullable=False),
    sa.Column('analysis_id', sa.String(length=64), nullable=False),
    sa.Column('action_text', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['analysis_id'], ['call_analyses.analysis_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('action_id')
    )
    op.create_index(op.f('ix_next_actions_analysis_id'), 'next_actions', ['analysis_id'], unique=False)
    op.create_table('objections',
    sa.Column('objection_id', sa.String(length=64), nullable=False),
    sa.Column('analysis_id', sa.String(length=64), nullable=False),
    sa.Column('objection_text', sa.Text(), nullable=False),
    sa.Column('embedding', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['analysis_id'], ['call_analyses.analysis_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('objection_id')
    )
    op.create_index(op.f('ix_objections_analysis_id'), 'objections', ['analysis_id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_objections_analysis_id'), table_name='objections')
    op.drop_table('objections')
    op.drop_index(op.f('ix_next_actions_analysis_id'), table_name='next_actions')
    op.drop_table('next_actions')
    op.drop_index(op.f('ix_call_events_conversation_id'), table_name='call_events')
    op.drop_table('call_events')
    op.drop_index(op.f('ix_call_analyses_prospect_id'), table_name='call_analyses')
    op.drop_index(op.f('ix_call_analyses_conversation_id'), table_name='call_analyses')
    op.drop_table('call_analyses')
    op.drop_index(op.f('ix_operator_overrides_prospect_id'), table_name='operator_overrides')
    op.drop_table('operator_overrides')
    op.drop_index(op.f('ix_conversations_prospect_id'), table_name='conversations')
    op.drop_index(op.f('ix_conversations_packet_id'), table_name='conversations')
    op.drop_table('conversations')
    op.drop_index(op.f('ix_claim_evidence_claim_id'), table_name='claim_evidence')
    op.drop_table('claim_evidence')
    op.drop_index(op.f('ix_intelligence_packets_prospect_id'), table_name='intelligence_packets')
    op.drop_table('intelligence_packets')
    op.drop_index(op.f('ix_identities_prospect_id'), table_name='identities')
    op.drop_index(op.f('ix_identities_key_value'), table_name='identities')
    op.drop_table('identities')
    op.drop_index(op.f('ix_enrichment_runs_prospect_id'), table_name='enrichment_runs')
    op.drop_index(op.f('ix_enrichment_runs_job_id'), table_name='enrichment_runs')
    op.drop_table('enrichment_runs')
    op.drop_index(op.f('ix_claims_prospect_id'), table_name='claims')
    op.drop_table('claims')
    op.drop_index(op.f('ix_source_documents_url'), table_name='source_documents')
    op.drop_table('source_documents')
    op.drop_index(op.f('ix_prospects_linkedin_url'), table_name='prospects')
    op.drop_index(op.f('ix_prospects_email'), table_name='prospects')
    op.drop_index(op.f('ix_prospects_company_url'), table_name='prospects')
    op.drop_table('prospects')
    op.drop_index(op.f('ix_companies_company_url'), table_name='companies')
    op.drop_table('companies')
    op.drop_table('clients')
    op.drop_index(op.f('ix_audit_logs_entity_id'), table_name='audit_logs')
    op.drop_table('audit_logs')
    # ### end Alembic commands ###
