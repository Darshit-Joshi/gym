import React, { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ChevronLeft, ChevronRight, StickyNote } from 'lucide-react';
import { attendanceService, getApiErrorMessage } from '../../services/api';
import { currentMonth, longDay, monthLabel, shiftMonth, todayIso } from '../../utils/format';
import { useFeedback } from '../../context/FeedbackContext';
import type { AttendanceRecord, AttendanceStatusType } from '../../types';
import { Card } from '../common/Card';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { Textarea } from '../common/Input';
import { Skeleton } from '../common/LoadingSpinner';
import { ATTENDANCE_STYLES, StatusButtons } from './StatusButtons';

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

interface Props {
  clientId: number;
  initialMonth?: string; // YYYY-MM
}

/** One client's month of attendance. Tap a day to mark or change it. */
export const ClientAttendanceCalendar: React.FC<Props> = ({ clientId, initialMonth }) => {
  const qc = useQueryClient();
  const { toast } = useFeedback();
  const [month, setMonth] = useState(() => (initialMonth && /^\d{4}-\d{2}$/.test(initialMonth) ? initialMonth : currentMonth()));
  const [selected, setSelected] = useState<string | null>(null);
  const [note, setNote] = useState('');
  const today = todayIso();

  const { data, isLoading } = useQuery({
    queryKey: ['client-attendance', clientId, month],
    queryFn: () => attendanceService.getClientAttendanceHistory(clientId, { month }),
  });

  const byDate = useMemo(() => new Map<string, AttendanceRecord>((data?.records ?? []).map((r) => [r.date, r])), [data]);

  const [y, m] = month.split('-').map(Number);
  const leading = (new Date(y, m - 1, 1).getDay() + 6) % 7; // Monday first
  const daysInMonth = new Date(y, m, 0).getDate();
  const days = Array.from({ length: daysInMonth }, (_, i) => `${month}-${String(i + 1).padStart(2, '0')}`);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['client-attendance', clientId] });
    qc.invalidateQueries({ queryKey: ['daily-attendance'] });
    qc.invalidateQueries({ queryKey: ['attendance-monthly-overview'] });
    qc.invalidateQueries({ queryKey: ['trainer-dashboard'] });
  };

  const save = useMutation({
    mutationFn: (v: { date: string; status: AttendanceStatusType; notes?: string }) =>
      attendanceService.recordAttendance({ client_id: clientId, ...v }),
    onSuccess: (rec) => {
      invalidate();
      setSelected(null);
      toast(`${longDay(rec.date)} marked ${rec.status.toLowerCase()}.`);
    },
    onError: (e) => toast(getApiErrorMessage(e, 'Could not save attendance.'), 'error'),
  });
  const clear = useMutation({
    mutationFn: (id: number) => attendanceService.deleteAttendance(id),
    onSuccess: () => {
      invalidate();
      setSelected(null);
      toast('Attendance cleared.');
    },
    onError: (e) => toast(getApiErrorMessage(e, 'Could not clear attendance.'), 'error'),
  });

  const open = (d: string) => {
    setSelected(d);
    setNote(byDate.get(d)?.notes ?? '');
  };
  const selectedRecord = selected ? byDate.get(selected) : undefined;
  const attended = (data?.present_count ?? 0) + (data?.late_count ?? 0);

  return (
    <Card className="p-4 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <div className="flex items-center gap-1">
          <button type="button" onClick={() => setMonth((mo) => shiftMonth(mo, -1))} className="p-2 rounded-lg hover:bg-[var(--color-hover)] cursor-pointer" aria-label="Previous month">
            <ChevronLeft className="w-4 h-4" />
          </button>
          <h3 className="text-lg font-semibold min-w-[10rem] text-center">{monthLabel(month)}</h3>
          <button
            type="button"
            onClick={() => setMonth((mo) => shiftMonth(mo, 1))}
            disabled={month >= currentMonth()}
            className="p-2 rounded-lg hover:bg-[var(--color-hover)] cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
            aria-label="Next month"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
          {month !== currentMonth() && (
            <Button size="sm" variant="ghost" onClick={() => setMonth(currentMonth())}>
              This month
            </Button>
          )}
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="px-2.5 py-1 rounded-full bg-[var(--color-accent-soft)] text-[var(--color-accent-ink)] font-semibold num">
            {data?.total_recorded ? `${Math.round(data.attendance_percentage)}% attendance` : 'No records'}
          </span>
          {(['PRESENT', 'LATE', 'ABSENT'] as const).map((s) => (
            <span key={s} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[var(--color-surface-secondary)] border border-[var(--color-border)]">
              <span className={`w-2 h-2 rounded-sm ${ATTENDANCE_STYLES[s].solid}`} />
              <span className="num font-semibold">{s === 'PRESENT' ? data?.present_count ?? 0 : s === 'LATE' ? data?.late_count ?? 0 : data?.absent_count ?? 0}</span>
              <span className="text-[var(--color-text-secondary)]">{ATTENDANCE_STYLES[s].label}</span>
            </span>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-7 gap-1.5 sm:gap-2 mb-2">
        {WEEKDAYS.map((d) => (
          <div key={d} className="eyebrow text-center !text-[10px]">
            {d}
          </div>
        ))}
      </div>

      {isLoading ? (
        <Skeleton className="h-72 rounded-xl" />
      ) : (
        <div className="grid grid-cols-7 gap-1.5 sm:gap-2">
          {Array.from({ length: leading }).map((_, i) => (
            <div key={`pad-${i}`} />
          ))}
          {days.map((d) => {
            const rec = byDate.get(d);
            const future = d > today;
            const style = rec ? ATTENDANCE_STYLES[rec.status] : null;
            return (
              <button
                key={d}
                type="button"
                disabled={future}
                onClick={() => open(d)}
                aria-label={`${longDay(d)}: ${rec ? style!.label : future ? 'upcoming' : 'not marked'}`}
                className={`relative aspect-square sm:aspect-auto sm:h-20 rounded-xl border p-1.5 sm:p-2 flex flex-col items-start justify-between text-left transition-colors ${
                  future
                    ? 'border-transparent text-[var(--color-text-muted)] opacity-40 cursor-not-allowed'
                    : rec
                      ? `${style!.cell} cursor-pointer`
                      : 'border-[var(--color-border)] bg-[var(--color-surface-secondary)] hover:border-[var(--color-border-strong)] cursor-pointer'
                } ${d === today ? 'ring-2 ring-[var(--color-primary)] ring-offset-2 ring-offset-[var(--color-surface)]' : ''}`}
              >
                <span className={`num text-xs sm:text-sm font-semibold ${d === today ? 'text-[var(--color-accent-ink)]' : ''}`}>{Number(d.slice(8))}</span>
                {rec && (
                  <span className="w-full flex items-center justify-between">
                    <span className={`hidden sm:inline text-[10px] font-semibold ${style!.text}`}>{style!.label}</span>
                    <span className={`sm:hidden w-1.5 h-1.5 rounded-full ${style!.solid}`} />
                    {rec.notes && <StickyNote className="w-3 h-3 text-[var(--color-text-muted)]" />}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}
      <p className="text-xs text-[var(--color-text-muted)] mt-4">
        {attended} day{attended === 1 ? '' : 's'} attended in {monthLabel(month)}. Tap a day to mark or change it.
      </p>

      <Modal isOpen={!!selected} onClose={() => setSelected(null)} title={selected ? longDay(selected) : ''} description={selectedRecord ? `Marked ${ATTENDANCE_STYLES[selectedRecord.status].label.toLowerCase()} at ${selectedRecord.attendance_time}` : 'Not marked'} size="sm">
        {selected && (
          <div className="space-y-4">
            <StatusButtons
              value={selectedRecord?.status ?? null}
              disabled={save.isPending}
              onChange={(status) => save.mutate({ date: selected, status, notes: note.trim() || undefined })}
              size="lg"
            />
            <Textarea label="Note (optional)" rows={2} value={note} onChange={(e) => setNote(e.target.value)} placeholder="e.g. Called in sick" />
            <div className="flex justify-between gap-2">
              {selectedRecord ? (
                <Button variant="ghost" className="text-rose-600 dark:text-rose-400" isLoading={clear.isPending} onClick={() => clear.mutate(selectedRecord.id)}>
                  Clear
                </Button>
              ) : (
                <span />
              )}
              {selectedRecord && (
                <Button variant="secondary" isLoading={save.isPending} onClick={() => save.mutate({ date: selected, status: selectedRecord.status, notes: note.trim() })}>
                  Save note
                </Button>
              )}
            </div>
          </div>
        )}
      </Modal>
    </Card>
  );
};
