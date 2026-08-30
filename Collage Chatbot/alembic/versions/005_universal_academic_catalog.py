"Add versioned academic catalog metadata without replacing existing subjects."""
from alembic import op
import sqlalchemy as sa
revision = "005_universal_academic_catalog"
down_revision = "004_admin_knowledge_lifecycle"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "academic_branches" not in tables:
        op.create_table("academic_branches", sa.Column("id", sa.String(), primary_key=True), sa.Column("course_id", sa.String(), sa.ForeignKey("courses.id"), nullable=False), sa.Column("name", sa.String(150), nullable=False), sa.Column("code", sa.String(50)), sa.Column("is_active", sa.Boolean(), server_default="1"), sa.UniqueConstraint("course_id", "name", name="uq_academic_branch_course_name"))
    if "academic_schemes" not in tables:
        op.create_table("academic_schemes", sa.Column("id", sa.String(), primary_key=True), sa.Column("course_id", sa.String(), sa.ForeignKey("courses.id"), nullable=False), sa.Column("branch_id", sa.String(), sa.ForeignKey("academic_branches.id")), sa.Column("academic_year", sa.String(20), nullable=False), sa.Column("scheme_version", sa.String(80), nullable=False), sa.Column("effective_from", sa.Date()), sa.Column("effective_to", sa.Date()), sa.Column("verification_status", sa.String(30), server_default="DRAFT"), sa.Column("source_url", sa.String(500)), sa.Column("is_active", sa.Boolean(), server_default="1"), sa.UniqueConstraint("course_id", "branch_id", "academic_year", "scheme_version", name="uq_academic_scheme_version"))
    if "curriculum_sources" not in tables:
        op.create_table("curriculum_sources", sa.Column("id", sa.String(), primary_key=True), sa.Column("title", sa.String(255), nullable=False), sa.Column("source_url", sa.String(500), nullable=False), sa.Column("source_type", sa.String(50), nullable=False), sa.Column("verification_status", sa.String(30), server_default="PENDING"), sa.Column("verified_by", sa.String(100)), sa.Column("verified_at", sa.DateTime()), sa.Column("created_at", sa.DateTime()))
    columns = {c["name"] for c in inspector.get_columns("subjects")}
    additions = [("branch_id", sa.String(), "academic_branches.id"), ("scheme_id", sa.String(), "academic_schemes.id"), ("category", sa.String(80), None), ("delivery_mode", sa.String(30), None), ("verification_status", sa.String(30), None), ("source_id", sa.String(), "curriculum_sources.id"), ("effective_from", sa.Date(), None), ("effective_to", sa.Date(), None)]
    for name, typ, fk in additions:
        if name not in columns:
            op.add_column("subjects", sa.Column(name, typ, nullable=True))
            if fk: op.create_foreign_key(None, "subjects", fk.split(".")[0], [name], ["id"])
    if "subject_topics" not in tables:
        op.create_table("subject_topics", sa.Column("id", sa.String(), primary_key=True), sa.Column("subject_id", sa.String(), sa.ForeignKey("subjects.id"), nullable=False), sa.Column("topic", sa.String(255), nullable=False), sa.Column("sequence", sa.Integer(), server_default="0"), sa.Column("verification_status", sa.String(30), server_default="VERIFIED"))

def downgrade():
    op.drop_table("subject_topics")
    for name in ("effective_to", "effective_from", "source_id", "verification_status", "delivery_mode", "category", "scheme_id", "branch_id"): op.drop_column("subjects", name)
    op.drop_table("curriculum_sources")
    op.drop_table("academic_schemes")
    op.drop_table("academic_branches")
