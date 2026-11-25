"""Add weight to progress photos

Weekly progress photos can record the client's weight on the day.

Revision ID: c8e2a4d6f310
Revises: b3d5e7f9a210
Create Date: 2026-11-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8e2a4d6f310'
down_revision: Union[str, Sequence[str], None] = 'b3d5e7f9a210'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('progress_photos', sa.Column('weight', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('progress_photos', 'weight')
