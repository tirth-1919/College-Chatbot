"""Phase 3: Background Jobs, Memory, Deep Research, Data Analysis, AI Quality Metrics

Revision ID: 007_phase3
Revises: 006_phase2_workspace
Create Date: 2026-08-30

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '007_phase3'
down_revision = '006_phase2_workspace'
branch_labels = None
depends_on = None


def upgrade():
    # Add missing Phase 2 tables first
    op.create_table(
        'projects',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('owner_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=160), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_projects_owner_id'), 'projects', ['owner_id'], unique=False)
    
    op.create_table(
        'conversation_shares',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('conversation_id', sa.String(), nullable=False),
        sa.Column('created_by', sa.String(), nullable=False),
        sa.Column('share_token_hash', sa.String(length=64), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conversation_shares_conversation_id'), 'conversation_shares', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_conversation_shares_share_token_hash'), 'conversation_shares', ['share_token_hash'], unique=True)
    
    op.create_table(
        'canvases',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('owner_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False, server_default='Untitled Canvas'),
        sa.Column('content', sa.Text(), nullable=False, server_default=''),
        sa.Column('content_type', sa.String(length=30), nullable=False, server_default='markdown'),
        sa.Column('revision', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_canvases_project_id'), 'canvases', ['project_id'], unique=False)
    op.create_index(op.f('ix_canvases_owner_id'), 'canvases', ['owner_id'], unique=False)
    
    op.create_table(
        'canvas_versions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('canvas_id', sa.String(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['canvas_id'], ['canvases.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_canvas_versions_canvas_id'), 'canvas_versions', ['canvas_id'], unique=False)
    
    op.create_table(
        'attachments',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('conversation_id', sa.String(), nullable=True),
        sa.Column('project_id', sa.String(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_type', sa.String(length=120), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.Column('source_hash', sa.String(length=64), nullable=False),
        sa.Column('processing_status', sa.String(length=20), nullable=False, server_default='PROCESSING'),
        sa.Column('extraction_status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('index_status', sa.String(length=20), nullable=False, server_default='NOT_INDEXED'),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_attachments_conversation_id'), 'attachments', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_attachments_project_id'), 'attachments', ['project_id'], unique=False)
    op.create_index(op.f('ix_attachments_user_id'), 'attachments', ['user_id'], unique=False)
    op.create_index(op.f('ix_attachments_source_hash'), 'attachments', ['source_hash'], unique=False)
    
    # Add missing columns to conversations table
    with op.batch_alter_table('conversations') as batch_op:
        batch_op.add_column(sa.Column('project_id', sa.String(), nullable=True))
        batch_op.create_index('ix_conversations_project_id', ['project_id'])
    
    # Add missing columns to existing attachments table (if it exists without project_id)
    try:
        with op.batch_alter_table('attachments') as batch_op:
            batch_op.add_column(sa.Column('project_id', sa.String(), nullable=True), existing_type=sa.String())
            batch_op.create_index('ix_attachments_project_id', ['project_id'], existing_type=sa.String())
    except:
        pass  # Column may already exist
    
    # Background Jobs table
    op.create_table(
        'background_jobs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('job_type', sa.String(length=50), nullable=False),
        sa.Column('owner_id', sa.String(), nullable=False),
        sa.Column('owner_role', sa.String(length=50), nullable=False, server_default='STUDENT'),
        sa.Column('parameters', sa.JSON(), nullable=True, server_default='{}'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='QUEUED'),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_step', sa.String(length=255), nullable=True),
        sa.Column('queued_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('estimated_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_category', sa.String(length=50), nullable=True),
        sa.Column('cancellation_requested', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('cancellation_requested_at', sa.DateTime(), nullable=True),
        sa.Column('memory_used_mb', sa.Float(), nullable=True),
        sa.Column('cpu_time_seconds', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_background_jobs_owner_id'), 'background_jobs', ['owner_id'], unique=False)
    
    # User Memory table
    op.create_table(
        'user_memories',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('preferred_language', sa.String(length=10), nullable=False, server_default='en'),
        sa.Column('preferred_answer_style', sa.String(length=50), nullable=False, server_default='balanced'),
        sa.Column('study_preferences', sa.JSON(), nullable=True, server_default='{}'),
        sa.Column('recurring_patterns', sa.JSON(), nullable=True, server_default='[]'),
        sa.Column('memory_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_accessed_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('access_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_user_memories_user_id'), 'user_memories', ['user_id'], unique=True)
    
    # Deep Research Sources table
    op.create_table(
        'deep_research_sources',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('job_id', sa.String(), nullable=False),
        sa.Column('source_url', sa.String(length=500), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('authority_score', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('freshness_score', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('relevance_score', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('overall_quality', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('extracted_facts', sa.JSON(), nullable=True, server_default='[]'),
        sa.Column('citation_text', sa.Text(), nullable=True),
        sa.Column('is_duplicate', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('duplicate_of_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['job_id'], ['background_jobs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_deep_research_sources_job_id'), 'deep_research_sources', ['job_id'], unique=False)
    
    # Deep Research Reports table
    op.create_table(
        'deep_research_reports',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('job_id', sa.String(), nullable=False),
        sa.Column('research_question', sa.Text(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('detailed_report', sa.Text(), nullable=False),
        sa.Column('key_findings', sa.JSON(), nullable=True, server_default='[]'),
        sa.Column('total_sources', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('authoritative_sources', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('source_conflicts', sa.JSON(), nullable=True, server_default='[]'),
        sa.Column('citations_validated', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('citation_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('limitations', sa.Text(), nullable=True),
        sa.Column('confidence_level', sa.String(length=30), nullable=False, server_default='MEDIUM'),
        sa.Column('uncertainty_explained', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('suggested_followups', sa.JSON(), nullable=True, server_default='[]'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['job_id'], ['background_jobs.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id')
    )
    op.create_index(op.f('ix_deep_research_reports_job_id'), 'deep_research_reports', ['job_id'], unique=True)
    
    # Data Analysis Jobs table
    op.create_table(
        'data_analysis_jobs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('job_id', sa.String(), nullable=False),
        sa.Column('file_id', sa.String(), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=False),
        sa.Column('row_count', sa.Integer(), nullable=True),
        sa.Column('column_count', sa.Integer(), nullable=True),
        sa.Column('schema_detected', sa.JSON(), nullable=True),
        sa.Column('statistics', sa.JSON(), nullable=True),
        sa.Column('operations_performed', sa.JSON(), nullable=True, server_default='[]'),
        sa.Column('charts_generated', sa.JSON(), nullable=True, server_default='[]'),
        sa.Column('chart_urls', sa.JSON(), nullable=True, server_default='[]'),
        sa.Column('missing_values', sa.JSON(), nullable=True),
        sa.Column('data_quality_score', sa.Float(), nullable=True),
        sa.Column('result_csv_path', sa.String(length=500), nullable=True),
        sa.Column('result_xlsx_path', sa.String(length=500), nullable=True),
        sa.Column('result_pdf_path', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['file_id'], ['attachments.id'], ),
        sa.ForeignKeyConstraint(['job_id'], ['background_jobs.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id')
    )
    op.create_index(op.f('ix_data_analysis_jobs_job_id'), 'data_analysis_jobs', ['job_id'], unique=True)
    
    # AI Quality Metrics table
    op.create_table(
        'ai_quality_metrics',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('request_id', sa.String(length=100), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('conversation_id', sa.String(), nullable=True),
        sa.Column('intent', sa.String(length=50), nullable=True),
        sa.Column('selected_source', sa.String(length=50), nullable=True),
        sa.Column('provider', sa.String(length=50), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('answer_success', sa.Boolean(), nullable=True),
        sa.Column('tool_failure', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('retrieval_failure', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('user_feedback', sa.String(length=20), nullable=True),
        sa.Column('feedback_reason', sa.Text(), nullable=True),
        sa.Column('knowledge_gap_detected', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('gap_topic', sa.String(length=255), nullable=True),
        sa.Column('error_category', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_quality_metrics_request_id'), 'ai_quality_metrics', ['request_id'], unique=False)
    
    # Evaluation Dataset table
    op.create_table(
        'evaluation_dataset',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('question_type', sa.String(length=50), nullable=False),
        sa.Column('intent', sa.String(length=50), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=False, server_default='en'),
        sa.Column('course', sa.String(length=50), nullable=True),
        sa.Column('semester', sa.Integer(), nullable=True),
        sa.Column('subject', sa.String(length=100), nullable=True),
        sa.Column('expected_source', sa.String(length=50), nullable=False),
        sa.Column('expected_intent', sa.String(length=50), nullable=False),
        sa.Column('key_entities', sa.JSON(), nullable=True, server_default='{}'),
        sa.Column('expected_answer_contains', sa.JSON(), nullable=True, server_default='[]'),
        sa.Column('forbidden_phrases', sa.JSON(), nullable=True, server_default='[]'),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('difficulty', sa.String(length=30), nullable=False, server_default='MEDIUM'),
        sa.Column('priority', sa.String(length=30), nullable=False, server_default='NORMAL'),
        sa.Column('last_tested_at', sa.DateTime(), nullable=True),
        sa.Column('last_result', sa.String(length=30), nullable=True),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    # Drop Phase 3 tables first
    op.drop_index(op.f('ix_evaluation_dataset_updated_at'), table_name='evaluation_dataset')
    op.drop_index(op.f('ix_evaluation_dataset_created_at'), table_name='evaluation_dataset')
    op.drop_table('evaluation_dataset')
    
    op.drop_index(op.f('ix_ai_quality_metrics_request_id'), table_name='ai_quality_metrics')
    op.drop_table('ai_quality_metrics')
    
    op.drop_index(op.f('ix_data_analysis_jobs_job_id'), table_name='data_analysis_jobs')
    op.drop_table('data_analysis_jobs')
    
    op.drop_index(op.f('ix_deep_research_reports_job_id'), table_name='deep_research_reports')
    op.drop_table('deep_research_reports')
    
    op.drop_index(op.f('ix_deep_research_sources_job_id'), table_name='deep_research_sources')
    op.drop_table('deep_research_sources')
    
    op.drop_index(op.f('ix_user_memories_user_id'), table_name='user_memories')
    op.drop_table('user_memories')
    
    op.drop_index(op.f('ix_background_jobs_owner_id'), table_name='background_jobs')
    op.drop_table('background_jobs')
    
    # Drop Phase 2 tables
    op.drop_index(op.f('ix_attachments_source_hash'), table_name='attachments')
    op.drop_index(op.f('ix_attachments_user_id'), table_name='attachments')
    op.drop_index(op.f('ix_attachments_project_id'), table_name='attachments')
    op.drop_index(op.f('ix_attachments_conversation_id'), table_name='attachments')
    op.drop_table('attachments')
    
    op.drop_index(op.f('ix_canvas_versions_canvas_id'), table_name='canvas_versions')
    op.drop_table('canvas_versions')
    
    op.drop_index(op.f('ix_canvases_owner_id'), table_name='canvases')
    op.drop_index(op.f('ix_canvases_project_id'), table_name='canvases')
    op.drop_table('canvases')
    
    op.drop_index(op.f('ix_conversation_shares_share_token_hash'), table_name='conversation_shares')
    op.drop_index(op.f('ix_conversation_shares_conversation_id'), table_name='conversation_shares')
    op.drop_table('conversation_shares')
    
    op.drop_index(op.f('ix_projects_owner_id'), table_name='projects')
    op.drop_table('projects')