"""add fees, payments, notifications and trainer settings

Revision ID: f2b7c9d41a10
Revises: 6ee69ebc70d0
Create Date: 2026-11-21 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f2b7c9d41a10'
down_revision: Union[str, Sequence[str], None] = '6ee69ebc70d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timestamps():
    return [
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        'membership_plans',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('trainer_id', sa.Integer(), sa.ForeignKey('trainers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
        sa.Column('duration_months', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        *_timestamps(),
        sa.UniqueConstraint('trainer_id', 'name', name='uq_membership_plan_trainer_name'),
        sa.CheckConstraint('price > 0', name='ck_membership_plan_price_positive'),
        sa.CheckConstraint('duration_months BETWEEN 1 AND 24', name='ck_membership_plan_duration'),
    )
    op.create_index('ix_membership_plans_id', 'membership_plans', ['id'])
    op.create_index('ix_membership_plans_trainer_id', 'membership_plans', ['trainer_id'])

    op.add_column('clients', sa.Column('membership_plan_id', sa.Integer(), nullable=True))
    op.add_column('clients', sa.Column('fee_amount', sa.Numeric(10, 2), nullable=True))
    op.add_column('clients', sa.Column('billing_start_date', sa.Date(), nullable=True))
    op.create_foreign_key(
        'fk_clients_membership_plan_id', 'clients', 'membership_plans',
        ['membership_plan_id'], ['id'], ondelete='SET NULL',
    )
    op.create_index('ix_clients_membership_plan_id', 'clients', ['membership_plan_id'])

    op.create_table(
        'fee_records',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('trainer_id', sa.Integer(), sa.ForeignKey('trainers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plan_id', sa.Integer(), sa.ForeignKey('membership_plans.id', ondelete='SET NULL'), nullable=True),
        sa.Column('plan_name', sa.String(length=100), nullable=True),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('amount_due', sa.Numeric(10, 2), nullable=False),
        sa.Column('amount_paid', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('is_waived', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('notes', sa.Text(), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint('client_id', 'period_start', name='uq_fee_client_period_start'),
        sa.CheckConstraint('amount_due > 0', name='ck_fee_amount_due_positive'),
        sa.CheckConstraint('amount_paid >= 0', name='ck_fee_amount_paid_non_negative'),
        sa.CheckConstraint('period_end >= period_start', name='ck_fee_period_order'),
    )
    op.create_index('ix_fee_records_id', 'fee_records', ['id'])
    op.create_index('ix_fee_records_client_id', 'fee_records', ['client_id'])
    op.create_index('ix_fee_records_trainer_id', 'fee_records', ['trainer_id'])
    op.create_index('ix_fee_records_due_date', 'fee_records', ['due_date'])

    op.create_table(
        'fee_payments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('fee_id', sa.Integer(), sa.ForeignKey('fee_records.id', ondelete='CASCADE'), nullable=False),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('trainer_id', sa.Integer(), sa.ForeignKey('trainers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('paid_on', sa.Date(), nullable=False),
        sa.Column('method', sa.String(length=20), nullable=False, server_default='CASH'),
        sa.Column('reference', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('recorded_by_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('amount > 0', name='ck_fee_payment_amount_positive'),
    )
    op.create_index('ix_fee_payments_id', 'fee_payments', ['id'])
    op.create_index('ix_fee_payments_fee_id', 'fee_payments', ['fee_id'])
    op.create_index('ix_fee_payments_client_id', 'fee_payments', ['client_id'])
    op.create_index('ix_fee_payments_trainer_id', 'fee_payments', ['trainer_id'])
    op.create_index('ix_fee_payments_paid_on', 'fee_payments', ['paid_on'])

    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('trainer_id', sa.Integer(), sa.ForeignKey('trainers.id', ondelete='CASCADE'), nullable=True),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=True),
        sa.Column('fee_id', sa.Integer(), sa.ForeignKey('fee_records.id', ondelete='CASCADE'), nullable=True),
        sa.Column('type', sa.String(length=30), nullable=False),
        sa.Column('severity', sa.String(length=10), nullable=False, server_default='INFO'),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('client_message', sa.Text(), nullable=True),
        sa.Column('dedupe_key', sa.String(length=150), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('email_status', sa.String(length=10), nullable=True),
        sa.Column('email_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('email_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('user_id', 'dedupe_key', name='uq_notification_user_dedupe'),
    )
    op.create_index('ix_notifications_id', 'notifications', ['id'])
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('ix_notifications_trainer_id', 'notifications', ['trainer_id'])
    op.create_index('ix_notifications_client_id', 'notifications', ['client_id'])
    op.create_index('ix_notifications_type', 'notifications', ['type'])
    op.create_index('ix_notifications_is_read', 'notifications', ['is_read'])
    op.create_index('ix_notifications_email_status', 'notifications', ['email_status'])
    op.create_index('ix_notifications_created_at', 'notifications', ['created_at'])

    op.create_table(
        'trainer_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('trainer_id', sa.Integer(), sa.ForeignKey('trainers.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='INR'),
        sa.Column('fee_grace_days', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('fee_reminder_days', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('absence_streak_threshold', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('absence_monthly_threshold', sa.Integer(), nullable=False, server_default='6'),
        sa.Column('email_clients', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('email_trainer', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        *_timestamps(),
    )
    op.create_index('ix_trainer_settings_id', 'trainer_settings', ['id'])


def downgrade() -> None:
    op.drop_table('trainer_settings')
    op.drop_table('notifications')
    op.drop_table('fee_payments')
    op.drop_table('fee_records')
    op.drop_index('ix_clients_membership_plan_id', table_name='clients')
    op.drop_constraint('fk_clients_membership_plan_id', 'clients', type_='foreignkey')
    op.drop_column('clients', 'billing_start_date')
    op.drop_column('clients', 'fee_amount')
    op.drop_column('clients', 'membership_plan_id')
    op.drop_table('membership_plans')
