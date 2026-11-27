import React, { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, CalendarDays, CheckCheck, ChevronLeft, ChevronRight, Clock, MessageSquare, RotateCcw, SearchX, Users } from 'lucide-react';
import { attendanceService, getApiErrorMessage } from '../../services/api';
import { addDays, currentMonth, longDay, monthLabel, parseIso, relativeDay, shiftMonth, todayIso } from '../../utils/format';
import { useFeedback } from '../../context/FeedbackContext';
import type { AttendanceStatusType, DailyAttendanceClientItem, DailyAttendanceResponse } from '../../types';
import { Avatar } from '../../components/common/Avatar';
import { Button } from '../../components/common/Button';
import { Card } from '../../components/common/Card';
import { EmptyState } from '../../components/common/EmptyState';
import { Textarea } from '../../components/common/Input';
import { SkeletonList } from '../../components/common/LoadingSpinner';
import { Modal } from '../../components/common/Modal';
import { PageHeader, SearchInput, Segmented } from '../../components/common/ui';
import { ATTENDANCE_STYLES, StatusButtons } from '../../components/attendance/StatusButtons';

type View = 'daily' | 'monthly';
type Filter = 'ALL' | 'UNMARKED' | AttendanceStatusType;

// ============================================================================= Daily sheet

const DailySheet: React.FC = () => {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { toast, confirm } = useFeedback();
  const [date, setDate] = useState(todayIso);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<Filter>('ALL');
  const [noteFor, setNoteFor] = useState<DailyAttendanceClientItem | null>(null);
  const [noteText, setNoteText] = useState('');
  const [bulkBusy, setBulkBusy] = useState(false);
  const today = todayIso();
  const key = ['daily-attendance', date];

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: key,
    queryFn: () => attendanceService.getDailyAttendance(date),
    placeholderData: keepPreviousData,
  });

  const invalidateOthers = (clientId?: number) => {
    qc.invalidateQueries({ queryKey: ['trainer-dashboard'] });
    qc.invalidateQueries({ queryKey: ['attendance-monthly-overview'] });
    if (clientId) qc.invalidateQueries({ queryKey: ['client-attendance', clientId] });
  };

  /** Rewrites one client's row in the cached sheet, keeping the counts in step. */
  const patchRow = (clientId: number, patch: Partial<DailyAttendanceClientItem>) =>
    qc.setQueryData<DailyAttendanceResponse>(key, (old) => {
      if (!old) return old;
      const clients = old.clients.map((c) => (c.client_id === clientId ? { ...c, ...patch } : c));
      const count = (s: AttendanceStatusType | null) => clients.filter((c) => (c.status ?? null) === s).length;
      return { ...old, clients, present_count: count('PRESENT'), late_count: count('LATE'), absent_count: count('ABSENT'), unmarked_count: count(null) };
    });

  const mark = useMutation({
    mutationFn: (v: { client: DailyAttendanceClientItem; status: AttendanceStatusType; notes?: string }) =>
      attendanceService.recordAttendance({ client_id: v.client.client_id, date, status: v.status, notes: v.notes }),
    onMutate: async (v) => {
      await qc.cancelQueries({ queryKey: key });
      const previous = qc.getQueryData<DailyAttendanceResponse>(key);
      patchRow(v.client.client_id, { status: v.status, ...(v.notes !== undefined ? { notes: v.notes } : {}) });
      return { previous };
    },
    onSuccess: (rec) => {
      patchRow(rec.client_id, { attendance_id: rec.id, attendance_time: rec.attendance_time, notes: rec.notes });
      invalidateOthers(rec.client_id);
    },
    onError: (e, v, ctx) => {
      if (ctx?.previous) qc.setQueryData(key, ctx.previous);
      toast(`${v.client.client_name}: ${getApiErrorMessage(e, 'could not save attendance.')}`, 'error');
    },
  });

  const unmark = useMutation({
    mutationFn: (c: DailyAttendanceClientItem) => attendanceService.deleteAttendance(c.attendance_id!),
    onMutate: async (c) => {
      await qc.cancelQueries({ queryKey: key });
      const previous = qc.getQueryData<DailyAttendanceResponse>(key);
      patchRow(c.client_id, { status: null, attendance_id: undefined, attendance_time: undefined, notes: undefined });
      return { previous };
    },
    onSuccess: (_, c) => invalidateOthers(c.client_id),
    onError: (e, _c, ctx) => {
      if (ctx?.previous) qc.setQueryData(key, ctx.previous);
      toast(getApiErrorMessage(e, 'Could not clear attendance.'), 'error');
    },
  });

  const clients = data?.clients ?? [];
  const unmarked = clients.filter((c) => !c.status);
  const q = search.trim().toLowerCase();
  const visible = clients.filter((c) => {
    if (q && !c.client_name.toLowerCase().includes(q)) return false;
    if (filter === 'ALL') return true;
    if (filter === 'UNMARKED') return !c.status;
    return c.status === filter;
  });

  const markRemainingPresent = async () => {
    const ok = await confirm({
      title: `Mark ${unmarked.length} client${unmarked.length === 1 ? '' : 's'} present?`,
      message: `Everyone not yet marked for ${relativeDay(date).toLowerCase() === 'today' ? 'today' : longDay(date)} will be marked present. You can change anyone afterwards.`,
      confirmLabel: 'Mark present',
    });
    if (!ok) return;
    setBulkBusy(true);
    unmarked.forEach((c) => patchRow(c.client_id, { status: 'PRESENT' }));
    const results = await Promise.allSettled(
      unmarked.map((c) => attendanceService.recordAttendance({ client_id: c.client_id, date, status: 'PRESENT' })),
    );
    setBulkBusy(false);
    const failed = results.filter((r) => r.status === 'rejected').length;
    qc.invalidateQueries({ queryKey: key });
    invalidateOthers();
    unmarked.forEach((c) => qc.invalidateQueries({ queryKey: ['client-attendance', c.client_id] }));
    toast(failed ? `${failed} could not be saved. Please check and try again.` : `${unmarked.length} marked present.`, failed ? 'error' : 'success');
  };

  const openNote = (c: DailyAttendanceClientItem) => {
    setNoteFor(c);
    setNoteText(c.notes ?? '');
  };

  const total = data?.total_clients ?? 0;
  const marked = total - (data?.unmarked_count ?? 0);
  const pct = total ? Math.round((marked / total) * 100) : 0;

  return (
    <div className="space-y-5">
      {/* Day + progress */}
      <Card hero className="p-5 sm:p-6">
        <div className="flex flex-col lg:flex-row lg:items-center gap-5">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setDate((d) => addDays(d, -1))}
              className="w-11 h-11 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-secondary)] flex items-center justify-center hover:border-[var(--color-border-strong)] cursor-pointer"
              aria-label="Previous day"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <label className="relative flex-1 lg:flex-none min-w-0 lg:min-w-[15rem] cursor-pointer">
              <span className="block text-center lg:text-left px-3">
                <span className="eyebrow block">{relativeDay(date) === 'Today' || relativeDay(date) === 'Yesterday' ? relativeDay(date) : 'Viewing'}</span>
                <span className="block text-lg sm:text-xl font-semibold truncate" style={{ fontFamily: 'var(--font-display)' }}>
                  <span className="sm:hidden">{parseIso(date).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' })}</span>
                  <span className="hidden sm:inline">{longDay(date)}</span>
                </span>
              </span>
              <input
                type="date"
                value={date}
                max={today}
                onChange={(e) => e.target.value && setDate(e.target.value > today ? today : e.target.value)}
                className="absolute inset-0 opacity-0 cursor-pointer"
                aria-label="Pick a date"
              />
            </label>
            <button
              type="button"
              onClick={() => setDate((d) => addDays(d, 1))}
              disabled={date >= today}
              className="w-11 h-11 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-secondary)] flex items-center justify-center hover:border-[var(--color-border-strong)] cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
              aria-label="Next day"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
            {date !== today && (
              <Button variant="ghost" size="sm" leftIcon={<RotateCcw className="w-3.5 h-3.5" />} onClick={() => setDate(today)} className="hidden sm:inline-flex">
                Today
              </Button>
            )}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-baseline justify-between gap-3 mb-2">
              <p className="text-sm text-[var(--color-text-secondary)]">
                <span className="num text-2xl font-semibold text-[var(--color-text)]">{marked}</span> of <span className="num">{total}</span> marked
              </p>
              <span className="num text-sm font-semibold text-[var(--color-accent-ink)]">{pct}%</span>
            </div>
            <div className="h-2.5 rounded-full bg-[var(--color-surface-secondary)] border border-[var(--color-border)] overflow-hidden flex" aria-hidden="true">
              {total > 0 &&
                (['PRESENT', 'LATE', 'ABSENT'] as const).map((s) => {
                  const n = s === 'PRESENT' ? data?.present_count ?? 0 : s === 'LATE' ? data?.late_count ?? 0 : data?.absent_count ?? 0;
                  return <div key={s} className={`${ATTENDANCE_STYLES[s].solid} h-full transition-all duration-500 border-r-2 border-[var(--color-surface)] last:border-r-0`} style={{ width: `${(n / total) * 100}%` }} />;
                })}
            </div>
          </div>

          {unmarked.length > 0 && date <= today && (
            <Button variant="secondary" leftIcon={<CheckCheck className="w-4 h-4" />} isLoading={bulkBusy} onClick={markRemainingPresent} className="lg:self-center">
              Mark {unmarked.length} remaining present
            </Button>
          )}
        </div>
      </Card>

      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-3 md:items-center">
        <SearchInput value={search} onChange={setSearch} placeholder="Find a client" className="md:w-72" />
        <Segmented
          label="Show"
          value={filter}
          onChange={setFilter}
          options={[
            { value: 'ALL', label: 'All', count: total },
            { value: 'UNMARKED', label: 'To mark', count: data?.unmarked_count ?? 0 },
            { value: 'PRESENT', label: 'Present', count: data?.present_count ?? 0 },
            { value: 'LATE', label: 'Late', count: data?.late_count ?? 0 },
            { value: 'ABSENT', label: 'Absent', count: data?.absent_count ?? 0 },
          ]}
        />
      </div>

      {/* Sheet */}
      {isLoading ? (
        <SkeletonList rows={6} />
      ) : isError ? (
        <EmptyState tone="error" icon={<AlertTriangle className="w-6 h-6" />} title="Couldn't load attendance" actionLabel="Try again" onAction={() => refetch()} />
      ) : total === 0 ? (
        <EmptyState
          icon={<Users className="w-6 h-6" />}
          title="No active clients"
          description="Clients marked Active appear here every day."
          actionLabel="Go to clients"
          onAction={() => navigate('/clients')}
        />
      ) : visible.length === 0 ? (
        <EmptyState
          icon={filter === 'UNMARKED' && !q ? <CheckCheck className="w-6 h-6" /> : <SearchX className="w-6 h-6" />}
          title={filter === 'UNMARKED' && !q ? 'Everyone is marked' : 'Nobody matches'}
          description={filter === 'UNMARKED' && !q ? 'Nice work. All clients have attendance for this day.' : undefined}
          actionLabel="Show everyone"
          onAction={() => {
            setFilter('ALL');
            setSearch('');
          }}
        />
      ) : (
        <ul className="panel divide-y divide-[var(--color-border)] overflow-hidden">
          {visible.map((c) => (
            <li key={c.client_id} className={`flex flex-col sm:flex-row sm:items-center gap-3 px-4 py-3.5 transition-colors ${!c.status ? '' : 'bg-[var(--color-surface-secondary)]/40'}`}>
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <div className="relative">
                  <Avatar clientId={c.client_id} photo={c.client_photo} name={c.client_name} />
                  {c.status && (
                    <span className={`absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full ring-2 ring-[var(--color-surface)] ${ATTENDANCE_STYLES[c.status].solid}`} aria-hidden="true" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <Link to={`/clients/${c.client_id}?tab=attendance&month=${date.slice(0, 7)}`} className="font-medium truncate block hover:text-[var(--color-accent-ink)]">
                    {c.client_name}
                  </Link>
                  <p className="text-xs text-[var(--color-text-muted)] flex items-center gap-1.5 truncate">
                    {c.status && c.attendance_time ? (
                      <>
                        <Clock className="w-3 h-3" /> {c.attendance_time}
                      </>
                    ) : c.status ? (
                      'Saving…'
                    ) : (
                      'Not marked'
                    )}
                    {c.membership_status !== 'Active' && c.membership_status !== 'Pending Activation' && <span>· {c.membership_status}</span>}
                    {c.notes && <span className="truncate italic">· “{c.notes}”</span>}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => openNote(c)}
                  className={`sm:hidden p-2 rounded-lg cursor-pointer ${c.notes ? 'text-[var(--color-accent-ink)]' : 'text-[var(--color-text-muted)]'}`}
                  aria-label={c.notes ? 'Edit note' : 'Add note'}
                >
                  <MessageSquare className="w-4 h-4" />
                </button>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="flex-1 sm:w-[19rem]">
                  <StatusButtons value={c.status ?? null} name={c.client_name} onChange={(status) => mark.mutate({ client: c, status })} />
                </div>
                <button
                  type="button"
                  onClick={() => openNote(c)}
                  className={`hidden sm:flex w-10 h-10 items-center justify-center rounded-xl border cursor-pointer transition-colors ${
                    c.notes
                      ? 'border-[rgba(var(--color-primary-rgb),0.4)] text-[var(--color-accent-ink)] bg-[var(--color-accent-soft)]'
                      : 'border-[var(--color-border)] text-[var(--color-text-muted)] hover:text-[var(--color-text)]'
                  }`}
                  aria-label={c.notes ? 'Edit note' : 'Add note'}
                  title={c.notes ? 'Edit note' : 'Add note'}
                >
                  <MessageSquare className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={() => c.attendance_id && unmark.mutate(c)}
                  disabled={!c.attendance_id}
                  className="w-10 h-10 flex items-center justify-center rounded-xl text-[var(--color-text-muted)] hover:text-rose-500 hover:bg-rose-500/10 cursor-pointer disabled:opacity-0 disabled:pointer-events-none"
                  aria-label={`Clear attendance for ${c.client_name}`}
                  title="Clear"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <Modal
        isOpen={!!noteFor}
        onClose={() => setNoteFor(null)}
        title={noteFor ? `Note for ${noteFor.client_name}` : ''}
        description={noteFor && !noteFor.status ? 'Saving a note marks them present. Change it afterwards if needed.' : longDay(date)}
        size="sm"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!noteFor) return;
            mark.mutate(
              { client: noteFor, status: noteFor.status ?? 'PRESENT', notes: noteText.trim() },
              { onSuccess: () => toast('Note saved.') },
            );
            setNoteFor(null);
          }}
          className="space-y-4"
        >
          <Textarea autoFocus rows={3} value={noteText} onChange={(e) => setNoteText(e.target.value)} placeholder="e.g. Left early, knee pain" />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setNoteFor(null)}>
              Cancel
            </Button>
            <Button type="submit">Save note</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

// ============================================================================= Monthly overview

const MonthlyOverview: React.FC = () => {
  const [month, setMonth] = useState(currentMonth);
  const [search, setSearch] = useState('');
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['attendance-monthly-overview', month],
    queryFn: () => attendanceService.getMonthlyOverview({ month, page_size: 100 }),
    placeholderData: keepPreviousData,
  });

  const q = search.trim().toLowerCase();
  const rows = (data?.clients ?? []).filter((c) => !q || c.client_name.toLowerCase().includes(q));
  const sorted = [...rows].sort((a, b) => b.attendance_percentage - a.attendance_percentage || b.present_count - a.present_count);

  return (
    <div className="space-y-5">
      <div className="flex flex-col md:flex-row md:items-center gap-3">
        <div className="flex items-center justify-between gap-1 panel p-1 w-full md:w-fit">
          <button type="button" onClick={() => setMonth((m) => shiftMonth(m, -1))} className="w-10 h-10 flex items-center justify-center rounded-lg hover:bg-[var(--color-hover)] cursor-pointer" aria-label="Previous month">
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-sm font-semibold min-w-[9.5rem] text-center">{monthLabel(month)}</span>
          <button
            type="button"
            onClick={() => setMonth((m) => shiftMonth(m, 1))}
            disabled={month >= currentMonth()}
            className="w-10 h-10 flex items-center justify-center rounded-lg hover:bg-[var(--color-hover)] cursor-pointer disabled:opacity-30"
            aria-label="Next month"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
        <SearchInput value={search} onChange={setSearch} placeholder="Find a client" className="md:w-72 md:ml-auto" />
      </div>

      {isLoading ? (
        <SkeletonList rows={6} />
      ) : isError ? (
        <EmptyState tone="error" icon={<AlertTriangle className="w-6 h-6" />} title="Couldn't load the month" actionLabel="Try again" onAction={() => refetch()} />
      ) : sorted.length === 0 ? (
        <EmptyState icon={<CalendarDays className="w-6 h-6" />} title={q ? 'Nobody matches' : 'No clients'} />
      ) : (
        <ul className="panel divide-y divide-[var(--color-border)] overflow-hidden">
          {sorted.map((c) => {
            const pct = c.total_recorded ? c.attendance_percentage : 0;
            const bar = pct >= 80 ? 'bg-[var(--color-primary)]' : pct >= 50 ? 'bg-amber-500' : 'bg-rose-500';
            return (
              <li key={c.client_id}>
                <Link to={`/clients/${c.client_id}?tab=attendance&month=${month}`} className="flex items-center gap-3 sm:gap-4 px-4 py-3.5 hover:bg-[var(--color-hover)] transition-colors">
                  <Avatar clientId={c.client_id} photo={c.client_photo} name={c.client_name} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline justify-between gap-3">
                      <p className="font-medium truncate">{c.client_name}</p>
                      <span className="sm:hidden num text-sm font-semibold shrink-0">{c.total_recorded ? `${Math.round(pct)}%` : '—'}</span>
                    </div>
                    <p className="text-xs text-[var(--color-text-muted)] whitespace-nowrap truncate">
                      <span className="text-emerald-600 dark:text-emerald-400 num">{c.present_count}</span> present ·{' '}
                      <span className="text-amber-600 dark:text-amber-400 num">{c.late_count}</span> late ·{' '}
                      <span className="text-rose-600 dark:text-rose-400 num">{c.absent_count}</span> absent
                    </p>
                    <div className="sm:hidden mt-2 h-1.5 rounded-full bg-[var(--color-surface-secondary)] overflow-hidden" aria-hidden="true">
                      <div className={`h-full rounded-full ${bar}`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                  <div className="hidden sm:block w-40 shrink-0">
                    <div className="flex justify-end mb-1.5">
                      <span className="num text-sm font-semibold">{c.total_recorded ? `${Math.round(pct)}%` : '—'}</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-[var(--color-surface-secondary)] overflow-hidden">
                      <div className={`h-full rounded-full ${bar}`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-[var(--color-text-muted)] shrink-0 hidden sm:block" />
                </Link>
              </li>
            );
          })}
        </ul>
      )}
      <p className="text-xs text-[var(--color-text-muted)]">Percentages count present and late days out of days marked.</p>
    </div>
  );
};

// ============================================================================= Page

export const AttendancePage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const view: View = searchParams.get('view') === 'monthly' ? 'monthly' : 'daily';

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Check-ins"
        title="Attendance"
        description={view === 'daily' ? 'Tap Present, Late or Absent. Each client gets one record per day.' : 'How often each client came in this month.'}
        actions={
          <Segmented
            label="View"
            value={view}
            onChange={(v) => setSearchParams(v === 'daily' ? {} : { view: v }, { replace: true })}
            options={[
              { value: 'daily', label: 'Daily sheet' },
              { value: 'monthly', label: 'Monthly' },
            ]}
          />
        }
      />
      {view === 'daily' ? <DailySheet /> : <MonthlyOverview />}
    </div>
  );
};
