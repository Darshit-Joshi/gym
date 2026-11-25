import React from 'react';
import { Badge } from '../common/Badge';

const STATUS_STYLES: Record<string, { label: string; variant: 'success' | 'warning' | 'danger' | 'info' | 'neutral' }> = {
  PAID: { label: 'Paid', variant: 'success' },
  PARTIAL: { label: 'Partially paid', variant: 'warning' },
  PENDING: { label: 'Due', variant: 'warning' },
  UPCOMING: { label: 'Upcoming', variant: 'info' },
  OVERDUE: { label: 'Overdue', variant: 'danger' },
  WAIVED: { label: 'Waived', variant: 'neutral' },
  NO_DUE: { label: 'No due', variant: 'neutral' },
  NO_PLAN: { label: 'No plan', variant: 'neutral' },
};

export const FeeStatusBadge: React.FC<{ status: string; size?: 'sm' | 'md' }> = ({ status, size = 'sm' }) => {
  const style = STATUS_STYLES[status] ?? { label: status, variant: 'neutral' as const };
  return (
    <Badge variant={style.variant} size={size} dot>
      {style.label}
    </Badge>
  );
};

const STANDING: Record<string, { label: string; variant: 'success' | 'warning' | 'danger' | 'neutral' }> = {
  OVERDUE: { label: 'Overdue', variant: 'danger' },
  DUE: { label: 'Fee due', variant: 'warning' },
  CLEAR: { label: 'Paid up', variant: 'success' },
  NO_PLAN: { label: 'No plan', variant: 'neutral' },
};

/** A client's overall fee standing, from the client list. */
export const PaymentStandingBadge: React.FC<{ status?: string }> = ({ status }) => {
  const s = STANDING[status ?? 'NO_PLAN'] ?? STANDING.NO_PLAN;
  return (
    <Badge variant={s.variant} size="sm" dot>
      {s.label}
    </Badge>
  );
};
