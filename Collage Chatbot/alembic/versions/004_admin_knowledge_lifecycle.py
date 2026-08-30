""
from alembic import op
import sqlalchemy as sa
revision = "004_admin_knowledge_lifecycle"
down_revision = "003_enhance_user_authentication"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "knowledge_versions" not in inspector.get_table_names():
        op.create_table("knowledge_versions",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False), sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False), sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("change_reason", sa.String(500)), sa.Column("created_by", sa.String()), sa.Column("created_at", sa.DateTime()))
        op.create_index("ix_knowledge_versions_source_id", "knowledge_versions", ["source_id"])
        op.create_index("ix_knowledge_versions_content_hash", "knowledge_versions", ["content_hash"])
    op.create_table("knowledge_gap_events",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("normalized_question", sa.String(1000), nullable=False),
        sa.Column("occurrence_count", sa.Integer(), nullable=False, server_default="1"), sa.Column("first_seen_at", sa.DateTime()),
        sa.Column("last_seen_at", sa.DateTime()), sa.Column("status", sa.String(30), nullable=False, server_default="OPEN"),
        sa.Column("resolved_by", sa.String()), sa.Column("resolved_at", sa.DateTime()))
    op.create_index("ix_knowledge_gap_events_normalized_question", "knowledge_gap_events", ["normalized_question"])
    op.create_table("admin_sessions",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False), sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime()), sa.Column("created_at", sa.DateTime()))
    op.create_index("ix_admin_sessions_user_id", "admin_sessions", ["user_id"])
    op.create_index("ix_admin_sessions_token_hash", "admin_sessions", ["token_hash"], unique=True)

def downgrade():
    op.drop_index("ix_admin_sessions_token_hash", table_name="admin_sessions"); op.drop_index("ix_admin_sessions_user_id", table_name="admin_sessions"); op.drop_table("admin_sessions")
    op.drop_index("ix_knowledge_gap_events_normalized_question", table_name="knowledge_gap_events"); op.drop_table("knowledge_gap_events")
    op.drop_index("ix_knowledge_versions_content_hash", table_name="knowledge_versions"); op.drop_index("ix_knowledge_versions_source_id", table_name="knowledge_versions"); op.drop_table("knowledge_versions")


