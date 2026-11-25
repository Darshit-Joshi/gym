import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Bell, CheckCheck, ChevronLeft, ChevronRight } from 'lucide-react';
import { notificationService } from '../services/api';
import type { AppNotification } from '../types';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { EmptyState } from '../components/common/EmptyState';
import { NotificationItem } from '../components/notifications/NotificationItem';

const FILTERS = [
  { key: '', label: 'All' },
  { key: 'ABSENCE_STREAK', label: 'Absence streaks' },
  { key: 'ABSENCE_MONTHLY', label: 'Monthly absences' },
  { key: 'FEE_OVERDUE', label: 'Overdue fees' },
] as const;

export const NotificationsPage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [type, setType] = useState<string>('');

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['notifications', 'page', page, unreadOnly, type],
    queryFn: () => notificationService.getNotifications({ page, page_size: 20, unread_only: unreadOnly, type: type || undefined }),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['notifications'] });
  const markRead = useMutation({ mutationFn: notificationService.markRead, onSuccess: invalidate });
  const markAll = useMutation({ mutationFn: notificationService.markAllRead, onSuccess: invalidate });
  const handleOpen = (n: AppNotification) => {
    if (!n.is_read) markRead.mutate(n.id);
    if (n.link) navigate(n.link);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 pb-2 border-b border-[var(--color-border)]">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-[var(--color-text)] tracking-tight">Notifications</h1>
          <p className="text-sm text-[var(--color-text-secondary)] mt-0.5">
            Absence and overdue fee alerts. Use WhatsApp to follow up with the client in one tap.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            leftIcon={<CheckCheck className="w-4 h-4" />}
            disabled={!data?.unread_count}
            isLoading={markAll.isPending}
            onClick={() => markAll.mutate()}
          >
            Mark all read
          </Button>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center gap-3 justify-between">
        <div className="flex items-center gap-1 overflow-x-auto p-1 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl text-xs font-semibold">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => {
                setType(f.key);
                setPage(1);
              }}
              className={`px-3 py-1.5 rounded-lg whitespace-nowrap cursor-pointer ${
                type === f.key
                  ? 'bg-[var(--color-primary)] text-[var(--color-primary-text)]'
                  : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <label className="inline-flex items-center gap-2 text-sm text-[var(--color-text-secondary)] cursor-pointer">
          <input
            type="checkbox"
            checked={unreadOnly}
            onChange={(e) => {
              setUnreadOnly(e.target.checked);
              setPage(1);
            }}
            className="accent-[var(--color-primary)] w-4 h-4"
          />
          Unread only
        </label>
      </div>

      {isLoading ? (
        <LoadingSpinner message="Loading notifications..." />
      ) : isError || !data ? (
        <EmptyState title="Unable to load notifications" actionLabel="Try again" onAction={() => refetch()} />
      ) : data.items.length === 0 ? (
        <EmptyState
          icon={<Bell className="w-8 h-8" />}
          title="No notifications"
          description={unreadOnly ? 'You have no unread notifications.' : 'Alerts will appear here as they are raised.'}
        />
      ) : (
        <Card className="fx-stagger p-2 divide-y divide-[var(--color-border)]">
          {data.items.map((n) => (
            <NotificationItem key={n.id} notification={n} onOpen={handleOpen} />
          ))}
        </Card>
      )}

      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-between text-sm text-[var(--color-text-secondary)]">
          <span>
            Page {data.page} of {data.total_pages} · {data.total} total
          </span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)} leftIcon={<ChevronLeft className="w-4 h-4" />}>
              Previous
            </Button>
            <Button variant="outline" size="sm" disabled={page >= data.total_pages} onClick={() => setPage((p) => p + 1)} rightIcon={<ChevronRight className="w-4 h-4" />}>
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};
