"""add last_modified_by_user_id to attendance

Revision ID: 6ee69ebc70d0
Revises: a7886564e14b
Create Date: 2026-10-11 20:34:24.847962

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6ee69ebc70d0'
down_revision: Union[str, Sequence[str], None] = 'a7886564e14b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('attendance_records', sa.Column('last_modified_by_user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_attendance_records_last_modified_by_user_id',
        'attendance_records',
        'users',
        ['last_modified_by_user_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_attendance_records_last_modified_by_user_id', 'attendance_records', type_='foreignkey')
    op.drop_column('attendance_records', 'last_modified_by_user_id')
