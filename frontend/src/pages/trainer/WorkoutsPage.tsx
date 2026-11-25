import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, Dumbbell, Library, Plus } from 'lucide-react';
import { clientService, getApiErrorMessage, sessionService } from '../../services/api';
import { formatDate } from '../../utils/format';
import { useFeedback } from '../../context/FeedbackContext';
import type { WorkoutSession } from '../../types';
import { Button } from '../../components/common/Button';
import { EmptyState } from '../../components/common/EmptyState';
import { SkeletonList } from '../../components/common/LoadingSpinner';
import { PageHeader } from '../../components/common/ui';
import { WorkoutDayCard } from '../../components/workouts/WorkoutDayCard';
import { WorkoutLogModal } from '../../components/workouts/WorkoutLogModal';

const HISTORY_LIMIT = 60;

export const WorkoutsPage: React.FC = () => {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { toast, confirm } = useFeedback();
  const [searchParams, setSearchParams] = useSearchParams();
  const [clientFilter, setClientFilter] = useState<number | ''>('');

  // ?action=log&clientId=…&date=… opens the logger (used from client pages)
  const logOpen = searchParams.get('action') === 'log';
  const logClient = searchParams.get('clientId') ? Number(searchParams.get('clientId')) : undefined;
  const logDate = searchParams.get('date') ?? undefined;
  const openLog = (clientId?: number, date?: string) => {
    const p: Record<string, string> = { action: 'log' };
    if (clientId) p.clientId = String(clientId);
    if (date) p.date = date;
    setSearchParams(p, { replace: true });
  };
  const closeLog = () => setSearchParams({}, { replace: true });

  const { data: roster = [] } = useQuery({ queryKey: ['roster'], queryFn: clientService.getRoster });
  const { data: sessions = [], isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['sessions', { client_id: clientFilter || undefined, limit: HISTORY_LIMIT }],
    queryFn: () => sessionService.getSessions({ client_id: clientFilter || undefined, limit: HISTORY_LIMIT }),
    placeholderData: keepPreviousData,
  });

  const remove = useMutation({
    mutationFn: (s: WorkoutSession) => sessionService.deleteSession(s.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sessions'] });
      qc.invalidateQueries({ queryKey: ['trainer-dashboard'] });
      toast('Workout removed.');
    },
    onError: (e) => toast(getApiErrorMessage(e, 'Could not remove the workout.'), 'error'),
  });

  const askRemove = async (s: WorkoutSession) => {
    const ok = await confirm({
      title: 'Remove this workout?',
      message: `${s.client_name}'s workout on ${formatDate(s.date)} (${s.exercises.length} exercises) will be deleted.`,
      confirmLabel: 'Remove',
      danger: true,
    });
    if (ok) remove.mutate(s);
  };

  // Group by month for scanning long histories
  const groups: [string, WorkoutSession[]][] = [];
  for (const s of sessions) {
    const label = new Date(s.date + 'T00:00').toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
    const last = groups[groups.length - 1];
    if (last && last[0] === label) last[1].push(s);
    else groups.push([label, [s]]);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Training log"
        title="Workouts"
        description="What each client trained, day by day."
        actions={
          <>
            <Button variant="secondary" leftIcon={<Library className="w-4 h-4" />} onClick={() => navigate('/exercises')}>
              Exercise library
            </Button>
            <Button leftIcon={<Plus className="w-4 h-4" />} onClick={() => openLog(clientFilter || undefined)}>
              Log workout
            </Button>
          </>
        }
      />

      <div className="flex items-center gap-3">
        <select
          value={clientFilter}
          onChange={(e) => setClientFilter(e.target.value ? Number(e.target.value) : '')}
          aria-label="Filter by client"
          className="h-11 px-3.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-sm cursor-pointer w-full sm:w-72"
        >
          <option value="">All clients</option>
          {roster.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        {sessions.length >= HISTORY_LIMIT && <p className="hidden sm:block text-xs text-[var(--color-text-muted)]">Showing the latest {HISTORY_LIMIT}. Pick a client to see their full history.</p>}
      </div>

      {isLoading ? (
        <SkeletonList rows={5} />
      ) : isError ? (
        <EmptyState tone="error" icon={<AlertTriangle className="w-6 h-6" />} title="Couldn't load workouts" actionLabel="Try again" onAction={() => refetch()} />
      ) : sessions.length === 0 ? (
        <EmptyState
          icon={<Dumbbell className="w-6 h-6" />}
          title={clientFilter ? 'No workouts for this client yet' : 'No workouts logged yet'}
          description="Log what a client trained today to start their history."
          actionLabel="Log workout"
          actionIcon={<Plus className="w-4 h-4" />}
          onAction={() => openLog(clientFilter || undefined)}
        />
      ) : (
        <div className={`space-y-8 transition-opacity ${isFetching ? 'opacity-70' : ''}`}>
          {groups.map(([label, list]) => (
            <section key={label}>
              <h2 className="eyebrow mb-3">{label}</h2>
              <div className="fx-stagger space-y-3">
                {list.map((s) => (
                  <WorkoutDayCard key={s.id} session={s} showClient={!clientFilter} onEdit={() => openLog(s.client_id, s.date)} onDelete={() => askRemove(s)} />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}

      <WorkoutLogModal isOpen={logOpen} onClose={closeLog} initialClientId={logClient} initialDate={logDate} />
    </div>
  );
};
