"""Drop single trainer constraint

Revision d4e821b9a789 limited the trainers table to one row via a unique
`singleton_guard` column. Trainers now register independently, so a second
trainer's insert failed on that constraint (and was reported as a duplicate email).

Revision ID: a9c4e1f7b2d8
Revises: e7a1c2d3f4b5
Create Date: 2026-11-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9c4e1f7b2d8'
down_revision: Union[str, Sequence[str], None] = 'e7a1c2d3f4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('uq_trainers_singleton_guard', 'trainers', type_='unique')
    op.drop_column('trainers', 'singleton_guard')


def downgrade() -> None:
    # Fails if more than one trainer exists, which is the point of the constraint.
    op.add_column(
        'trainers',
        sa.Column('singleton_guard', sa.Integer(), nullable=False, server_default='1'),
    )
    op.create_unique_constraint('uq_trainers_singleton_guard', 'trainers', ['singleton_guard'])
