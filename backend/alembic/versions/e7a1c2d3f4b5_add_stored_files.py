"""Add stored_files table for photos kept in the database

With STORAGE_BACKEND=database, profile and progress photos are stored here instead of on disk.

Revision ID: e7a1c2d3f4b5
Revises: c8e2a4d6f310
Create Date: 2026-11-25 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7a1c2d3f4b5'
down_revision: Union[str, Sequence[str], None] = 'c8e2a4d6f310'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'stored_files',
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('content_type', sa.String(length=50), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('data', sa.LargeBinary(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('key'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('stored_files')
