import React from 'react';
import { AlertTriangle, BellRing, HardDrive, IndianRupee, MessageCircle, UserX } from 'lucide-react';
import type { AppNotification } from '../../types';
import { formatRelativeTime } from '../../utils/format';

const ICONS: Record<string, React.ElementType> = {
  ABSENCE_STREAK: UserX,
  ABSENCE_MONTHLY: UserX,
  FEE_DUE_SOON: IndianRupee,
  FEE_OVERDUE: AlertTriangle,
  STORAGE_LOW: HardDrive,
};

const SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: 'bg-rose-500/15 text-rose-600 dark:text-rose-400',
  WARNING: 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
  INFO: 'bg-sky-500/15 text-sky-600 dark:text-sky-400',
};

interface Props {
  notification: AppNotification;
  onOpen: (n: AppNotification) => void;
  compact?: boolean;
}

export const NotificationItem: React.FC<Props> = ({ notification: n, onOpen, compact = false }) => {
  const Icon = ICONS[n.type] ?? BellRing;
  return (
    <div
      className={`flex gap-3 ${compact ? 'p-3' : 'p-4'} rounded-lg transition-colors ${
        n.is_read ? '' : 'bg-[var(--color-primary)]/5'
      } hover:bg-[var(--color-hover)]`}
    >
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${SEVERITY_STYLES[n.severity] ?? SEVERITY_STYLES.INFO}`}>
        <Icon className="w-4 h-4" />
      </div>
      <button type="button" onClick={() => onOpen(n)} className="flex-1 min-w-0 text-left cursor-pointer">
        <div className="flex items-start justify-between gap-2">
          <p className={`text-sm ${n.is_read ? 'font-medium' : 'font-bold'} text-[var(--color-text)] ${compact ? 'line-clamp-1' : ''}`}>
            {n.title}
          </p>
          {!n.is_read && <span className="mt-1.5 w-2 h-2 rounded-full bg-[var(--color-primary)] shrink-0" aria-label="Unread" />}
        </div>
        <p className={`text-xs text-[var(--color-text-secondary)] mt-0.5 ${compact ? 'line-clamp-2' : ''}`}>{n.message}</p>
        <p className="text-[11px] text-[var(--color-text-muted)] mt-1">{formatRelativeTime(n.created_at)}</p>
      </button>
      {n.whatsapp_link && (
        <a
          href={n.whatsapp_link}
          target="_blank"
          rel="noopener noreferrer"
          title="Send a WhatsApp message to the client"
          className="self-center shrink-0 inline-flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-semibold text-emerald-700 dark:text-emerald-300 bg-emerald-500/10 border border-emerald-500/30 hover:bg-emerald-500/20"
        >
          <MessageCircle className="w-3.5 h-3.5" />
          {!compact && <span>WhatsApp</span>}
        </a>
      )}
    </div>
  );
};
