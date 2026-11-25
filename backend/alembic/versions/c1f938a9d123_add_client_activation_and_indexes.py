"""Add client activation and indexes

Revision ID: c1f938a9d123
Revises: e36d340bdb80
Create Date: 2026-10-09 18:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1f938a9d123'
down_revision: Union[str, Sequence[str], None] = 'e36d340bdb80'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add activation columns to users
    op.add_column('users', sa.Column('activation_token', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('activation_expires', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_users_activation_token'), 'users', ['activation_token'], unique=False)

    # Add index on clients fitness_goal for fast filtering
    op.create_index(op.f('ix_clients_fitness_goal'), 'clients', ['fitness_goal'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_clients_fitness_goal'), table_name='clients')
    op.drop_index(op.f('ix_users_activation_token'), table_name='users')
    op.drop_column('users', 'activation_expires')
    op.drop_column('users', 'activation_token')
