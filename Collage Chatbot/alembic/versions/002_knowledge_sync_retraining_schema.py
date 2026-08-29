"""Knowledge sync, pending updates, and intent retraining schema

Revision ID: 002_knowledge_sync_retraining_schema
Revises: 001_initial_ait_schema
Create Date: 2026-08-29 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_knowledge_sync_retraining_schema'
down_revision: Union[str, None] = '001_initial_ait_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Schema creation binds to Base metadata
    pass

def downgrade() -> None:
    pass
