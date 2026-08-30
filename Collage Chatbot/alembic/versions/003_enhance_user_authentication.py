"""Enhance user authentication with Google OAuth and password reset

Revision ID: 003_enhance_user_authentication
Revises: 002_knowledge_sync_retraining_schema
Create Date: 2026-08-29 22:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '003_enhance_user_authentication'
down_revision = '002_knowledge_sync_retraining_schema'
branch_labels = None
depends_on = None


def upgrade():
    # For SQLite, we need to recreate the table to make hashed_password nullable and add new columns
    # This is a limitation of SQLite's ALTER TABLE support
    op.execute("ALTER TABLE users RENAME TO users_old")
    
    # Create new users table with nullable hashed_password and new columns
    op.execute("""
        CREATE TABLE users (
            id VARCHAR PRIMARY KEY,
            email VARCHAR(150) NOT NULL UNIQUE,
            hashed_password VARCHAR(255),
            full_name VARCHAR(150) NOT NULL,
            enrollment_number VARCHAR(50) UNIQUE,
            google_id VARCHAR(255) UNIQUE,
            profile_image_url VARCHAR(500),
            is_active BOOLEAN DEFAULT 1,
            is_verified BOOLEAN DEFAULT 0,
            department_id VARCHAR,
            course_id VARCHAR,
            current_semester INTEGER,
            created_at DATETIME,
            updated_at DATETIME,
            last_login_at DATETIME,
            FOREIGN KEY(department_id) REFERENCES departments(id),
            FOREIGN KEY(course_id) REFERENCES courses(id)
        )
    """)
    
    # Copy data from old table
    op.execute("""
        INSERT INTO users (id, email, hashed_password, full_name, enrollment_number, 
                         is_active, department_id, course_id, current_semester, 
                         created_at, updated_at, google_id, profile_image_url, 
                         is_verified, last_login_at)
        SELECT id, email, hashed_password, full_name, enrollment_number,
               is_active, department_id, course_id, current_semester,
               created_at, updated_at, NULL, NULL, 0, NULL
        FROM users_old
    """)
    
    # Drop old table
    op.execute("DROP TABLE users_old")
    
    # Recreate indexes
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_enrollment_number', 'users', ['enrollment_number'], unique=True)
    op.create_index('ix_users_google_id', 'users', ['google_id'], unique=True)
    
    # Create password_reset_tokens table
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('token', sa.String(255), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token')
    )
    op.create_index('ix_password_reset_tokens_token', 'password_reset_tokens', ['token'], unique=True)


def downgrade():
    # Drop password_reset_tokens table
    op.drop_index('ix_password_reset_tokens_token', table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')
    
    # Drop google_id index
    op.drop_index('ix_users_google_id', table_name='users')
    
    # Recreate users table without new columns and with non-nullable hashed_password
    op.execute("ALTER TABLE users RENAME TO users_new")
    
    op.execute("""
        CREATE TABLE users (
            id VARCHAR PRIMARY KEY,
            email VARCHAR(150) NOT NULL UNIQUE,
            hashed_password VARCHAR(255) NOT NULL,
            full_name VARCHAR(150) NOT NULL,
            enrollment_number VARCHAR(50) UNIQUE,
            is_active BOOLEAN DEFAULT 1,
            department_id VARCHAR,
            course_id VARCHAR,
            current_semester INTEGER,
            created_at DATETIME,
            updated_at DATETIME,
            FOREIGN KEY(department_id) REFERENCES departments(id),
            FOREIGN KEY(course_id) REFERENCES courses(id)
        )
    """)
    
    # Copy data (excluding new columns)
    op.execute("""
        INSERT INTO users (id, email, hashed_password, full_name, enrollment_number,
                         is_active, department_id, course_id, current_semester,
                         created_at, updated_at)
        SELECT id, email, hashed_password, full_name, enrollment_number,
               is_active, department_id, course_id, current_semester,
               created_at, updated_at
        FROM users_new
    """)
    
    # Drop new table
    op.execute("DROP TABLE users_new")
    
    # Recreate indexes
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_enrollment_number', 'users', ['enrollment_number'], unique=True)
