import React from 'react';
import { Button } from './Button';

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  actionIcon?: React.ReactNode;
  /** Renders without the surrounding panel, for use inside a card. */
  bare?: boolean;
  tone?: 'default' | 'error';
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  actionLabel,
  onAction,
  actionIcon,
  bare = false,
  tone = 'default',
}) => (
  <div className={`flex flex-col items-center justify-center text-center py-12 px-6 ${bare ? '' : 'panel border-dashed'}`}>
    {icon && (
      <div
        className={`mb-4 w-14 h-14 rounded-2xl flex items-center justify-center border ${
          tone === 'error'
            ? 'bg-rose-500/10 border-rose-500/25 text-rose-500 dark:text-rose-400'
            : 'bg-[var(--color-accent-soft)] border-[rgba(var(--color-primary-rgb),0.25)] text-[var(--color-accent-ink)]'
        }`}
      >
        {icon}
      </div>
    )}
    <h3 className="text-base font-semibold text-[var(--color-text)]">{title}</h3>
    {description && <p className="text-sm text-[var(--color-text-secondary)] max-w-sm mt-1.5">{description}</p>}
    {actionLabel && onAction && (
      <div className="mt-5">
        <Button onClick={onAction} leftIcon={actionIcon} variant={tone === 'error' ? 'secondary' : 'primary'} size="sm">
          {actionLabel}
        </Button>
      </div>
    )}
  </div>
);
