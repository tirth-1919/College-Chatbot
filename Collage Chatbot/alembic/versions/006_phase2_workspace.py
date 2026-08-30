"Phase 2 projects, secure shares, canvases, and attachment project scope."""
from alembic import op
import sqlalchemy as sa
revision = "006_phase2_workspace"
down_revision = "005_universal_academic_catalog"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "projects" not in tables:
        op.create_table("projects", sa.Column("id", sa.String(), primary_key=True), sa.Column("owner_id", sa.String(), sa.ForeignKey("users.id"), nullable=False), sa.Column("name", sa.String(160), nullable=False), sa.Column("description", sa.String(1000)), sa.Column("instructions", sa.Text()), sa.Column("is_archived", sa.Boolean(), server_default="0"), sa.Column("created_at", sa.DateTime()), sa.Column("updated_at", sa.DateTime()))
        op.create_index("ix_projects_owner_id", "projects", ["owner_id"])
    if "conversation_shares" not in tables:
        op.create_table("conversation_shares", sa.Column("id", sa.String(), primary_key=True), sa.Column("conversation_id", sa.String(), sa.ForeignKey("conversations.id"), nullable=False), sa.Column("created_by", sa.String(), sa.ForeignKey("users.id"), nullable=False), sa.Column("share_token_hash", sa.String(64), nullable=False, unique=True), sa.Column("created_at", sa.DateTime()), sa.Column("expires_at", sa.DateTime()), sa.Column("revoked_at", sa.DateTime()))
        op.create_index("ix_conversation_shares_share_token_hash", "conversation_shares", ["share_token_hash"])
    if "canvases" not in tables:
        op.create_table("canvases", sa.Column("id", sa.String(), primary_key=True), sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=False), sa.Column("owner_id", sa.String(), sa.ForeignKey("users.id"), nullable=False), sa.Column("title", sa.String(255), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("content_type", sa.String(30), nullable=False), sa.Column("revision", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime()), sa.Column("updated_at", sa.DateTime()))
    if "canvas_versions" not in tables:
        op.create_table("canvas_versions", sa.Column("id", sa.String(), primary_key=True), sa.Column("canvas_id", sa.String(), sa.ForeignKey("canvases.id"), nullable=False), sa.Column("version", sa.Integer(), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime()))
    if "conversations" in tables and "project_id" not in {c["name"] for c in inspector.get_columns("conversations")}:
        op.add_column("conversations", sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id")))
    if "attachments" in tables and "project_id" not in {c["name"] for c in inspector.get_columns("attachments")}:
        op.add_column("attachments", sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id")))

def downgrade():
    pass
