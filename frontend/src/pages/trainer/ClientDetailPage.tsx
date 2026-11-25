import React, { useRef, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Archive,
  ArchiveRestore,
  ArrowLeft,
  CalendarCheck2,
  Camera,
  Dumbbell,
  Mail,
  MoreHorizontal,
  Pencil,
  Phone,
  ShieldAlert,
  StickyNote,
  Target,
  Trash2,
  UserX,
  Wallet,
} from 'lucide-react';
import { attendanceService, clientService, feeService, getApiErrorMessage, noteService, sessionService } from '../../services/api';
import { addDays, currentMonth, formatDate, formatMoney, relativeDay, todayIso, weekdayShort } from '../../utils/format';
import { useFeedback } from '../../context/FeedbackContext';
import type { AttendanceRecord, Client } from '../../types';
import { Avatar } from '../../components/common/Avatar';
import { ClientStatusBadge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { Card } from '../../components/common/Card';
import { EmptyState } from '../../components/common/EmptyState';
import { Textarea } from '../../components/common/Input';
import { Skeleton } from '../../components/common/LoadingSpinner';
import { Modal } from '../../components/common/Modal';
import { SectionTitle, Segmented, StatTile } from '../../components/common/ui';
import { ClientAttendanceCalendar } from '../../components/attendance/ClientAttendanceCalendar';
import { ClientFeesSection } from '../../components/fees/ClientFeesSection';
import { FeeStatusBadge } from '../../components/fees/FeeStatusBadge';
import { ClientProgressPhotos } from '../../components/progress/ClientProgressPhotos';
import { ClientFormModal } from '../../components/clients/ClientFormModal';
import { WorkoutDayCard } from '../../components/workouts/WorkoutDayCard';

type Tab = 'overview' | 'attendance' | 'fees' | 'workouts' | 'progress' | 'notes';
const TABS: { value: Tab; label: string }[] = [
  { value: 'overview', label: 'Overview' },
  { value: 'attendance', label: 'Attendance' },
  { value: 'fees', label: 'Fees' },
  { value: 'workouts', label: 'Workouts' },
  { value: 'progress', label: 'Progress' },
  { value: 'notes', label: 'Notes' },
];
// Old links used ?tab=details / ?tab=exercises
const TAB_ALIASES: Record<string, Tab> = { details: 'overview', exercises: 'workouts' };

const STATUS_DOT: Record<string, string> = {
  PRESENT: 'bg-emerald-500',
  LATE: 'bg-amber-500',
  ABSENT: 'bg-rose-500',
};

/** The last 14 days as a strip of dots. */
const AttendanceStrip: React.FC<{ records: AttendanceRecord[] }> = ({ records }) => {
  const byDate = new Map(records.map((r) => [r.date, r.status]));
  const today = todayIso();
  const days = Array.from({ length: 14 }, (_, i) => addDays(today, i - 13));
  return (
    <div>
      <div className="grid gap-1.5" style={{ gridTemplateColumns: 'repeat(14, minmax(0, 1fr))' }}>
        {days.map((d) => {
          const st = byDate.get(d);
          return (
            <div key={d} className="flex flex-col items-center gap-1.5" title={`${relativeDay(d)}: ${st ? st.toLowerCase() : 'not marked'}`}>
              <span
                className={`w-full aspect-square max-w-7 rounded-md ${
                  st ? STATUS_DOT[st] : 'bg-[var(--color-surface-secondary)] border border-[var(--color-border)]'
                } ${d === today ? 'ring-2 ring-offset-2 ring-offset-[var(--color-surface)] ring-[var(--color-primary)]' : ''}`}
              />
              <span className="text-[9px] text-[var(--color-text-muted)] hidden sm:block">{weekdayShort(d).slice(0, 2)}</span>
            </div>
          );
        })}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-3 text-[11px] text-[var(--color-text-secondary)]">
        {(
          [
            ['Present', 'bg-emerald-500'],
            ['Late', 'bg-amber-500'],
            ['Absent', 'bg-rose-500'],
          ] as const
        ).map(([l, c]) => (
          <span key={l} className="inline-flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-sm ${c}`} /> {l}
          </span>
        ))}
      </div>
    </div>
  );
};

export const ClientDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const clientId = parseInt(id || '0', 10);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { toast, confirm } = useFeedback();
  const [searchParams, setSearchParams] = useSearchParams();
  const rawTab = searchParams.get('tab') ?? 'overview';
  const tab: Tab = TAB_ALIASES[rawTab] ?? (TABS.some((t) => t.value === rawTab) ? (rawTab as Tab) : 'overview');
  const setTab = (t: Tab) => setSearchParams(t === 'overview' ? {} : { tab: t }, { replace: true });

  const photoInputRef = useRef<HTMLInputElement>(null);
  const [editOpen, setEditOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [pendingPhoto, setPendingPhoto] = useState<{ file: File; preview: string } | null>(null);
  const [noteText, setNoteText] = useState('');

  const { data: client, isLoading, isError } = useQuery({
    queryKey: ['client', clientId],
    queryFn: () => clientService.getClient(clientId),
    enabled: !!clientId,
  });
  const { data: attendance } = useQuery({
    queryKey: ['client-attendance', clientId, 'all'],
    queryFn: () => attendanceService.getClientAttendanceHistory(clientId),
    enabled: !!clientId,
  });
  const { data: monthAttendance } = useQuery({
    queryKey: ['client-attendance', clientId, currentMonth()],
    queryFn: () => attendanceService.getClientAttendanceHistory(clientId, { month: currentMonth() }),
    enabled: !!clientId,
  });
  const { data: account } = useQuery({
    queryKey: ['fees', 'client', clientId],
    queryFn: () => feeService.getClientAccount(clientId),
    enabled: !!clientId,
  });
  const { data: sessions = [] } = useQuery({
    queryKey: ['sessions', { client_id: clientId }],
    queryFn: () => sessionService.getSessions({ client_id: clientId, limit: 60 }),
    enabled: !!clientId,
  });
  const { data: notes = [] } = useQuery({
    queryKey: ['client-notes', clientId],
    queryFn: () => noteService.getClientNotes(clientId),
    enabled: !!clientId && (tab === 'notes' || tab === 'overview'),
  });

  const refreshClient = () => {
    qc.invalidateQueries({ queryKey: ['client', clientId] });
    qc.invalidateQueries({ queryKey: ['clients'] });
    qc.invalidateQueries({ queryKey: ['roster'] });
    qc.invalidateQueries({ queryKey: ['daily-attendance'] });
    qc.invalidateQueries({ queryKey: ['trainer-dashboard'] });
  };
  const fail = (fallback: string) => (e: unknown) => toast(getApiErrorMessage(e, fallback), 'error');

  const uploadPhoto = useMutation({
    mutationFn: (file: File) => clientService.uploadPhoto(clientId, file),
    onSuccess: () => {
      refreshClient();
      setPendingPhoto(null);
      toast('Photo updated.');
    },
    onError: fail('Could not upload the photo.'),
  });
  const deletePhoto = useMutation({
    mutationFn: () => clientService.deletePhoto(clientId),
    onSuccess: () => {
      refreshClient();
      setPendingPhoto(null);
      toast('Photo removed.');
    },
    onError: fail('Could not remove the photo.'),
  });
  const setStatus = useMutation({
    mutationFn: async (status: 'Active' | 'Archived'): Promise<void> => {
      if (status === 'Archived') await clientService.archiveClient(clientId);
      else await clientService.updateClient(clientId, { status });
    },
    onSuccess: (_, status) => {
      refreshClient();
      toast(status === 'Archived' ? 'Client archived. Their history is kept.' : 'Client restored to your roster.');
    },
    onError: fail('Could not update the client.'),
  });
  const deleteForever = useMutation({
    mutationFn: () => clientService.deleteClientPermanently(clientId),
    onSuccess: (res) => {
      qc.removeQueries({ queryKey: ['client', clientId] });
      refreshClient();
      toast(res.message);
      navigate('/clients');
    },
    onError: fail('Could not delete the client.'),
  });
  const addNote = useMutation({
    mutationFn: (text: string) => noteService.createClientNote(clientId, text),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['client-notes', clientId] });
      setNoteText('');
      toast('Note saved.');
    },
    onError: fail('Could not save the note.'),
  });
  const deleteNote = useMutation({
    mutationFn: (noteId: number) => noteService.deleteNote(noteId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['client-notes', clientId] }),
    onError: fail('Could not delete the note.'),
  });

  if (isLoading) {
    return (
      <div className="space-y-5" role="status" aria-label="Loading client">
        <Skeleton className="h-5 w-24" />
        <Skeleton className="h-40 rounded-2xl" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-28 rounded-2xl" />
          ))}
        </div>
      </div>
    );
  }
  if (isError || !client) {
    return (
      <EmptyState
        icon={<UserX className="w-6 h-6" />}
        title="Client not found"
        description="They may have been deleted, or the link is wrong."
        actionLabel="Back to clients"
        onAction={() => navigate('/clients')}
      />
    );
  }

  const archived = client.status === 'Archived';
  const m = account?.membership;
  const currency = account?.currency ?? 'INR';
  const daysAttended = (attendance?.present_count ?? 0) + (attendance?.late_count ?? 0);
  const monthRecorded = monthAttendance?.total_recorded ?? 0;
  const lastWorkout = sessions[0];
  const openFees = (account?.fees ?? []).filter((f) => f.balance > 0);
  const logWorkout = () => navigate(`/workouts?action=log&clientId=${client.id}`);

  const askArchive = async () => {
    const ok = await confirm({
      title: `Archive ${client.name}?`,
      message: 'They leave your roster and attendance sheet and stop being billed. All history is kept and you can restore them later.',
      confirmLabel: 'Archive',
      danger: true,
    });
    if (ok) setStatus.mutate('Archived');
  };
  const askDelete = async () => {
    const ok = await confirm({
      title: `Delete ${client.name} permanently?`,
      message: (
        <>
          This removes the client <strong className="text-[var(--color-text)]">and all of their attendance, fees, payments, workouts, photos and notes</strong>.
          It cannot be undone.
        </>
      ),
      confirmLabel: 'Delete forever',
      danger: true,
    });
    if (ok) deleteForever.mutate();
  };

  const details: [string, React.ReactNode][] = [
    ['Phone', client.phone],
    ['Email', client.email],
    ['Date of birth', client.date_of_birth ? `${formatDate(client.date_of_birth)}${client.age ? ` · ${client.age} yrs` : ''}` : client.age ? `${client.age} yrs` : null],
    ['Gender', client.gender],
    ['Height', client.height ? `${client.height} cm` : null],
    ['Weight', client.current_weight ? `${client.current_weight} kg` : null],
    ['Emergency contact', client.emergency_contact],
    ['Joined', formatDate(client.joined_date)],
  ];

  return (
    <div className="space-y-6">
      <Link to="/clients" className="inline-flex items-center gap-1.5 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text)]">
        <ArrowLeft className="w-4 h-4" /> Clients
      </Link>

      {archived && (
        <div className="flex flex-col sm:flex-row sm:items-center gap-3 p-4 rounded-2xl border border-[var(--color-border-strong)] bg-[var(--color-surface-secondary)]">
          <Archive className="w-5 h-5 text-[var(--color-text-muted)] shrink-0" />
          <p className="text-sm text-[var(--color-text-secondary)] flex-1">
            This client is archived. They're hidden from attendance and not billed.
          </p>
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" leftIcon={<ArchiveRestore className="w-4 h-4" />} isLoading={setStatus.isPending} onClick={() => setStatus.mutate('Active')}>
              Restore
            </Button>
            <Button size="sm" variant="ghost" className="text-rose-600 dark:text-rose-400" leftIcon={<Trash2 className="w-4 h-4" />} onClick={askDelete}>
              Delete forever
            </Button>
          </div>
        </div>
      )}

      {/* Identity */}
      <Card hero className="p-5 sm:p-7">
        <div className="flex flex-col md:flex-row md:items-center gap-5">
          <div className="flex items-center gap-4 sm:gap-5 min-w-0 flex-1">
            <div className="relative shrink-0">
              <Avatar clientId={client.id} photo={client.profile_photo} name={client.name} size="xl" />
              <button
                type="button"
                onClick={() => photoInputRef.current?.click()}
                className="absolute -bottom-1 -right-1 w-9 h-9 rounded-full bg-[var(--color-primary)] text-[var(--color-primary-text)] flex items-center justify-center ring-4 ring-[var(--color-surface)] cursor-pointer hover:scale-105 transition-transform"
                aria-label="Change photo"
              >
                <Camera className="w-4 h-4" />
              </button>
              <input
                ref={photoInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) setPendingPhoto({ file, preview: URL.createObjectURL(file) });
                  e.target.value = '';
                }}
              />
            </div>
            <div className="min-w-0 space-y-2.5">
              <h1 className="text-2xl sm:text-3xl font-semibold leading-tight break-words">{client.name}</h1>
              <div className="flex flex-wrap gap-1.5">
                <ClientStatusBadge status={client.status} size="md" />
                {m && (m.overdue_count > 0 ? <FeeStatusBadge status="OVERDUE" size="md" /> : m.outstanding_amount > 0 ? <FeeStatusBadge status="PENDING" size="md" /> : m.plan_id ? <FeeStatusBadge status="PAID" size="md" /> : null)}
              </div>
              <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-sm text-[var(--color-text-secondary)]">
                {client.phone && (
                  <a href={`tel:${client.phone}`} className="inline-flex items-center gap-1.5 hover:text-[var(--color-text)]">
                    <Phone className="w-3.5 h-3.5" /> {client.phone}
                  </a>
                )}
                {client.email && (
                  <a href={`mailto:${client.email}`} className="inline-flex items-center gap-1.5 hover:text-[var(--color-text)] min-w-0">
                    <Mail className="w-3.5 h-3.5 shrink-0" /> <span className="truncate">{client.email}</span>
                  </a>
                )}
                <span className="inline-flex items-center gap-1.5">
                  <Target className="w-3.5 h-3.5" /> {client.fitness_goal || 'General Fitness'}
                </span>
              </div>
            </div>
          </div>

          <div className="flex gap-2 md:self-start">
            {!archived && (
              <Button leftIcon={<Dumbbell className="w-4 h-4" />} onClick={logWorkout} className="flex-1 md:flex-none">
                Log workout
              </Button>
            )}
            <Button variant="secondary" leftIcon={<Pencil className="w-4 h-4" />} onClick={() => setEditOpen(true)} className="flex-1 md:flex-none">
              Edit
            </Button>
            {!archived && (
              <div className="relative">
                <Button variant="secondary" onClick={() => setMenuOpen((o) => !o)} aria-label="More actions" aria-expanded={menuOpen} className="px-3">
                  <MoreHorizontal className="w-4 h-4" />
                </Button>
                {menuOpen && (
                  <>
                    <div className="fixed inset-0 z-40" onClick={() => setMenuOpen(false)} aria-hidden="true" />
                    <div role="menu" className="fx-dialog absolute right-0 top-12 z-50 w-56 p-1.5 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] shadow-[var(--shadow-dropdown)]">
                      <button
                        role="menuitem"
                        type="button"
                        onClick={() => {
                          setMenuOpen(false);
                          askArchive();
                        }}
                        className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm text-left text-rose-600 dark:text-rose-400 hover:bg-rose-500/10 cursor-pointer"
                      >
                        <Archive className="w-4 h-4" /> Archive client
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* At a glance */}
      <section className="fx-stagger grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4" aria-label="At a glance">
        <StatTile
          label="This month"
          icon={<CalendarCheck2 className="w-4 h-4" />}
          tone="lime"
          value={monthRecorded ? `${Math.round(monthAttendance?.attendance_percentage ?? 0)}%` : '—'}
          sub={monthRecorded ? `${(monthAttendance?.present_count ?? 0) + (monthAttendance?.late_count ?? 0)} of ${monthRecorded} days attended` : 'No attendance yet'}
          onClick={() => setTab('attendance')}
        />
        <StatTile
          label="Total visits"
          icon={<CalendarCheck2 className="w-4 h-4" />}
          tone="neutral"
          value={daysAttended}
          sub={`Since ${formatDate(client.joined_date)}`}
          onClick={() => setTab('attendance')}
        />
        <StatTile
          label="Balance due"
          icon={<Wallet className="w-4 h-4" />}
          tone={m && m.overdue_count > 0 ? 'rose' : 'amber'}
          emphasize={!!m && m.overdue_count > 0}
          value={m ? formatMoney(m.outstanding_amount, currency) : '—'}
          sub={m?.next_due_date ? `Next due ${formatDate(m.next_due_date)}` : m?.plan_name ? m.plan_name : 'No membership plan'}
          onClick={() => setTab('fees')}
        />
        <StatTile
          label="Last workout"
          icon={<Dumbbell className="w-4 h-4" />}
          tone="sky"
          value={lastWorkout ? <span className="text-xl sm:text-2xl">{relativeDay(lastWorkout.date)}</span> : '—'}
          sub={lastWorkout ? lastWorkout.workout_name : 'Nothing logged yet'}
          onClick={() => setTab('workouts')}
        />
      </section>

      <Segmented label="Client sections" value={tab} onChange={setTab} options={TABS} className="w-fit" />

      {tab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card className="lg:col-span-2 p-5 sm:p-6">
            <SectionTitle
              title="Last 14 days"
              icon={<CalendarCheck2 className="w-4 h-4" />}
              action={
                <button type="button" onClick={() => setTab('attendance')} className="text-xs font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text)] cursor-pointer">
                  Full calendar
                </button>
              }
            />
            <AttendanceStrip records={attendance?.records ?? []} />
          </Card>

          <Card className="p-5 sm:p-6">
            <SectionTitle
              title="Fees"
              icon={<Wallet className="w-4 h-4" />}
              action={
                <button type="button" onClick={() => setTab('fees')} className="text-xs font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text)] cursor-pointer">
                  Manage
                </button>
              }
            />
            {!m ? (
              <Skeleton className="h-20" />
            ) : !m.plan_id && openFees.length === 0 ? (
              <div className="text-sm text-[var(--color-text-secondary)] space-y-3">
                <p>No membership plan, so no fees are tracked.</p>
                <Button size="sm" variant="secondary" onClick={() => setTab('fees')}>
                  Assign a plan
                </Button>
              </div>
            ) : (
              <dl className="space-y-3 text-sm">
                <div className="flex justify-between gap-3">
                  <dt className="text-[var(--color-text-secondary)]">Plan</dt>
                  <dd className="font-medium text-right">{m.plan_name ?? '—'}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-[var(--color-text-secondary)]">Next due</dt>
                  <dd className="font-medium">{formatDate(m.next_due_date)}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-[var(--color-text-secondary)]">Outstanding</dt>
                  <dd className={`num font-semibold ${m.overdue_count > 0 ? 'text-rose-600 dark:text-rose-400' : ''}`}>{formatMoney(m.outstanding_amount, currency)}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-[var(--color-text-secondary)]">Paid to date</dt>
                  <dd className="num font-medium">{formatMoney(account?.total_paid ?? 0, currency)}</dd>
                </div>
                {openFees.length > 0 && (
                  <Button size="sm" className="w-full mt-1" onClick={() => setTab('fees')}>
                    Record payment
                  </Button>
                )}
              </dl>
            )}
          </Card>

          <Card className="lg:col-span-2 p-5 sm:p-6">
            <SectionTitle
              title="Recent workouts"
              icon={<Dumbbell className="w-4 h-4" />}
              action={
                !archived && (
                  <button type="button" onClick={logWorkout} className="text-xs font-medium text-[var(--color-accent-ink)] hover:underline cursor-pointer">
                    + Log workout
                  </button>
                )
              }
            />
            {sessions.length === 0 ? (
              <p className="text-sm text-[var(--color-text-secondary)] py-4">No workouts logged yet.</p>
            ) : (
              <div className="space-y-3">
                {sessions.slice(0, 3).map((s) => (
                  <WorkoutDayCard key={s.id} session={s} compact />
                ))}
              </div>
            )}
          </Card>

          <Card className="p-5 sm:p-6">
            <SectionTitle title="Profile" icon={<ShieldAlert className="w-4 h-4" />} />
            <dl className="space-y-3 text-sm">
              {details.map(([label, value]) => (
                <div key={label} className="flex justify-between gap-3">
                  <dt className="text-[var(--color-text-secondary)] shrink-0">{label}</dt>
                  <dd className="font-medium text-right break-words min-w-0">{value || <span className="text-[var(--color-text-muted)]">—</span>}</dd>
                </div>
              ))}
            </dl>
            {client.training_preferences && (
              <div className="mt-4 p-3 rounded-xl bg-amber-500/10 border border-amber-500/25 text-sm">
                <p className="eyebrow !text-amber-700 dark:!text-amber-300 mb-1">Training notes</p>
                <p className="whitespace-pre-wrap">{client.training_preferences}</p>
              </div>
            )}
            {notes[0] && (
              <button type="button" onClick={() => setTab('notes')} className="mt-3 w-full text-left p-3 rounded-xl bg-[var(--color-surface-secondary)] border border-[var(--color-border)] text-sm cursor-pointer hover:border-[var(--color-border-strong)]">
                <p className="eyebrow mb-1 flex items-center gap-1.5">
                  <StickyNote className="w-3 h-3" /> Latest note
                </p>
                <p className="line-clamp-2 text-[var(--color-text-secondary)]">{notes[0].note}</p>
              </button>
            )}
          </Card>
        </div>
      )}

      {tab === 'attendance' && (
        <ClientAttendanceCalendar clientId={client.id} initialMonth={searchParams.get('month') || undefined} />
      )}

      {tab === 'fees' && <ClientFeesSection clientId={client.id} />}

      {tab === 'progress' && <ClientProgressPhotos clientId={client.id} clientName={client.name} currentWeight={client.current_weight} />}

      {tab === 'workouts' && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm text-[var(--color-text-secondary)]">
              {sessions.length} workout day{sessions.length === 1 ? '' : 's'} logged
            </p>
            {!archived && (
              <Button size="sm" leftIcon={<Dumbbell className="w-4 h-4" />} onClick={logWorkout}>
                Log workout
              </Button>
            )}
          </div>
          {sessions.length === 0 ? (
            <EmptyState icon={<Dumbbell className="w-6 h-6" />} title="No workouts logged yet" description="Log what they trained today to start their history." actionLabel={archived ? undefined : 'Log workout'} onAction={logWorkout} />
          ) : (
            sessions.map((s) => (
              <WorkoutDayCard key={s.id} session={s} onEdit={archived ? undefined : () => navigate(`/workouts?action=log&clientId=${client.id}&date=${s.date}`)} />
            ))
          )}
        </div>
      )}

      {tab === 'notes' && (
        <div className="space-y-3">
          <Card>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (noteText.trim()) addNote.mutate(noteText.trim());
              }}
              className="space-y-3"
            >
              <Textarea label="New note" rows={3} value={noteText} onChange={(e) => setNoteText(e.target.value)} placeholder="Private notes, e.g. progress, injuries, goals discussed…" />
              <div className="flex justify-end">
                <Button type="submit" size="sm" isLoading={addNote.isPending} disabled={!noteText.trim()}>
                  Save note
                </Button>
              </div>
            </form>
          </Card>
          {notes.length === 0 ? (
            <p className="text-sm text-[var(--color-text-secondary)] text-center py-6">No notes yet.</p>
          ) : (
            notes.map((n) => (
              <Card key={n.id} className="flex items-start justify-between gap-3 p-4">
                <div className="min-w-0">
                  <p className="text-sm whitespace-pre-wrap break-words">{n.note}</p>
                  <p className="text-xs text-[var(--color-text-muted)] mt-1.5">{new Date(n.created_at).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })}</p>
                </div>
                <button
                  type="button"
                  onClick={async () => {
                    if (await confirm({ title: 'Delete this note?', confirmLabel: 'Delete', danger: true })) deleteNote.mutate(n.id);
                  }}
                  className="p-2 rounded-lg text-[var(--color-text-muted)] hover:text-rose-500 hover:bg-rose-500/10 cursor-pointer shrink-0"
                  aria-label="Delete note"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </Card>
            ))
          )}
        </div>
      )}

      <ClientFormModal
        isOpen={editOpen}
        client={client}
        onClose={() => setEditOpen(false)}
        onSaved={(c: Client) => {
          setEditOpen(false);
          refreshClient();
          toast(`${c.name}'s details saved.`);
        }}
      />

      <Modal isOpen={!!pendingPhoto} onClose={() => setPendingPhoto(null)} title="Profile photo" size="sm">
        {pendingPhoto && (
          <div className="space-y-5 text-center">
            <img src={pendingPhoto.preview} alt="New photo preview" className="w-36 h-36 mx-auto rounded-full object-cover ring-4 ring-[rgba(var(--color-primary-rgb),0.3)]" />
            <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2">
              {client.profile_photo && (
                <Button variant="ghost" isLoading={deletePhoto.isPending} onClick={() => deletePhoto.mutate()}>
                  Remove current photo
                </Button>
              )}
              <Button isLoading={uploadPhoto.isPending} onClick={() => uploadPhoto.mutate(pendingPhoto.file)}>
                Save photo
              </Button>
            </div>
          </div>
        )}
      </Modal>

    </div>
  );
};
