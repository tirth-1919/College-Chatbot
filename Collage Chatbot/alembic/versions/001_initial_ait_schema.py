"""Initial production schema for AIT AI Assistant

Revision ID: 001_initial_ait_schema
Revises: 
Create Date: 2026-08-27 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_ait_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Schema creation will bind to Base metadata or execute DDL
    pass

def downgrade() -> None:
    pass
