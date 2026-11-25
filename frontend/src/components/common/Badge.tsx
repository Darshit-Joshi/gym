import React from 'react';

export type BadgeVariant = 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'lime';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
  /** Leading status dot. */
  dot?: boolean;
  className?: string;
}

const STYLES: Record<BadgeVariant, { box: string; dot: string }> = {
  lime: {
    box: 'bg-[var(--color-accent-soft)] text-[var(--color-accent-ink)] border-[rgba(var(--color-primary-rgb),0.3)]',
    dot: 'bg-[var(--color-primary)]',
  },
  success: {
    box: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/25',
    dot: 'bg-emerald-500 dark:bg-emerald-400',
  },
  warning: {
    box: 'bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/25',
    dot: 'bg-amber-500 dark:bg-amber-400',
  },
  danger: {
    box: 'bg-rose-500/10 text-rose-700 dark:text-rose-300 border-rose-500/25',
    dot: 'bg-rose-500 dark:bg-rose-400',
  },
  info: {
    box: 'bg-sky-500/10 text-sky-700 dark:text-sky-300 border-sky-500/25',
    dot: 'bg-sky-500 dark:bg-sky-400',
  },
  neutral: {
    box: 'bg-[var(--color-surface-elevated)] text-[var(--color-text-secondary)] border-[var(--color-border)]',
    dot: 'bg-[var(--color-text-muted)]',
  },
};

export const Badge: React.FC<BadgeProps> = ({ children, variant = 'neutral', size = 'md', dot = false, className = '' }) => {
  const s = STYLES[variant];
  return (
    <span
      className={`inline-flex items-center gap-1.5 font-semibold rounded-full border whitespace-nowrap ${s.box} ${
        size === 'sm' ? 'text-[11px] px-2 py-0.5' : 'text-xs px-2.5 py-1'
      } ${className}`}
    >
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} aria-hidden="true" />}
      {children}
    </span>
  );
};

const CLIENT_STATUS: Record<string, BadgeVariant> = {
  Active: 'lime',
  'Pending Activation': 'lime',
  Inactive: 'warning',
  Archived: 'neutral',
};

/** Membership status of a client: Active, Inactive or Archived. */
export const ClientStatusBadge: React.FC<{ status: string; size?: 'sm' | 'md' }> = ({ status, size = 'sm' }) => (
  <Badge variant={CLIENT_STATUS[status] ?? 'neutral'} size={size} dot>
    {status === 'Pending Activation' ? 'Active' : status}
  </Badge>
);
