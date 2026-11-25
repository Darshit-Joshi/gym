"""Make sets and reps optional on session exercises

The exercise log now just records which exercises a client did on a day,
so sets and reps are no longer required.

Revision ID: b3d5e7f9a210
Revises: f2b7c9d41a10
Create Date: 2026-11-21 23:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3d5e7f9a210'
down_revision: Union[str, Sequence[str], None] = 'f2b7c9d41a10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('workout_session_exercises') as batch_op:
        batch_op.alter_column('sets_completed', existing_type=sa.Integer(), nullable=True)
        batch_op.alter_column('reps', existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("UPDATE workout_session_exercises SET sets_completed = 3 WHERE sets_completed IS NULL")
    op.execute("UPDATE workout_session_exercises SET reps = 10 WHERE reps IS NULL")
    with op.batch_alter_table('workout_session_exercises') as batch_op:
        batch_op.alter_column('sets_completed', existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column('reps', existing_type=sa.Integer(), nullable=False)
