"""Add single trainer constraint and demo flag

Revision ID: d4e821b9a789
Revises: c1f938a9d123
Create Date: 2026-10-09 21:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e821b9a789'
down_revision: Union[str, Sequence[str], None] = 'c1f938a9d123'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add singleton_guard column with default 1
    op.add_column(
        'trainers',
        sa.Column('singleton_guard', sa.Integer(), nullable=False, server_default='1'),
    )

    # 2. Add is_demo column with default false
    op.add_column(
        'trainers',
        sa.Column('is_demo', sa.Boolean(), nullable=False, server_default='false'),
    )

    # 3. Create unique constraint on singleton_guard to physically restrict trainers table to at most 1 row
    op.create_unique_constraint('uq_trainers_singleton_guard', 'trainers', ['singleton_guard'])

    # 4. Mark existing demo trainer if present
    op.execute(
        sa.text(
            "UPDATE trainers SET is_demo = true WHERE id IN (SELECT t.id FROM trainers t JOIN users u ON t.user_id = u.id WHERE u.email = 'trainer@example.com')"
        )
    )


def downgrade() -> None:
    op.drop_constraint('uq_trainers_singleton_guard', 'trainers', type_='unique')
    op.drop_column('trainers', 'is_demo')
    op.drop_column('trainers', 'singleton_guard')
