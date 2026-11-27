import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Bell, CheckCheck } from 'lucide-react';
import { notificationService } from '../../services/api';
import type { AppNotification } from '../../types';
import { NotificationItem } from './NotificationItem';

interface Props {
  align?: 'left' | 'right';
}

export const NotificationBell: React.FC<Props> = ({ align = 'right' }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: unread = 0 } = useQuery({
    queryKey: ['notifications', 'unread-count'],
    queryFn: notificationService.getUnreadCount,
    refetchInterval: 60_000,
  });

  const { data: latest, isLoading } = useQuery({
    queryKey: ['notifications', 'latest'],
    queryFn: () => notificationService.getNotifications({ page_size: 8 }),
    enabled: open,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['notifications'] });
  const markRead = useMutation({ mutationFn: notificationService.markRead, onSuccess: invalidate });
  const markAll = useMutation({ mutationFn: notificationService.markAllRead, onSuccess: invalidate });

  useEffect(() => {
    const onClick = (e: PointerEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('pointerdown', onClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('pointerdown', onClick);
      document.removeEventListener('keydown', onKey);
    };
  }, []);

  const handleOpen = (n: AppNotification) => {
    if (!n.is_read) markRead.mutate(n.id);
    setOpen(false);
    if (n.link) navigate(n.link);
  };

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="relative p-2 rounded-lg text-[var(--color-text-secondary)] hover:text-[var(--color-text)] hover:bg-[var(--color-hover)] min-h-[40px] min-w-[40px] flex items-center justify-center cursor-pointer"
        aria-label={unread > 0 ? `Notifications, ${unread} unread` : 'Notifications'}
        aria-expanded={open}
      >
        <Bell className="w-5 h-5" />
        {unread > 0 && (
          <span className="absolute top-1 right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-rose-600 text-white text-[10px] font-bold flex items-center justify-center">
            {unread > 99 ? '99+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div
          className={`fixed inset-x-4 top-[calc(4.25rem+env(safe-area-inset-top))] sm:absolute sm:inset-x-auto ${align === 'right' ? 'sm:right-0' : 'sm:left-0'} sm:top-12 sm:w-[22rem] bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl shadow-[var(--shadow-dropdown)] z-50 overflow-hidden`}
        >
          <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
            <span className="text-sm font-bold text-[var(--color-text)]">Notifications</span>
            {unread > 0 && (
              <button
                type="button"
                onClick={() => markAll.mutate()}
                className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--color-text-secondary)] hover:text-[var(--color-text)] cursor-pointer"
              >
                <CheckCheck className="w-3.5 h-3.5" /> Mark all read
              </button>
            )}
          </div>
          <div className="max-h-[60dvh] sm:max-h-96 overflow-y-auto overscroll-contain p-1.5">
            {isLoading ? (
              <p className="p-6 text-center text-xs text-[var(--color-text-secondary)]">Loading…</p>
            ) : latest && latest.items.length > 0 ? (
              latest.items.map((n) => <NotificationItem key={n.id} notification={n} onOpen={handleOpen} compact />)
            ) : (
              <p className="p-6 text-center text-xs text-[var(--color-text-secondary)]">You're all caught up.</p>
            )}
          </div>
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              navigate('/notifications');
            }}
            className="w-full px-4 py-2.5 text-xs font-semibold text-[var(--color-text)] border-t border-[var(--color-border)] hover:bg-[var(--color-hover)] cursor-pointer"
          >
            View all notifications
          </button>
        </div>
      )}
    </div>
  );
};
