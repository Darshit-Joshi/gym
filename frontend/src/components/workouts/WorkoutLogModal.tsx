import React, { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Check, Library, X } from 'lucide-react';
import { clientService, exerciseService, getApiErrorMessage, sessionService } from '../../services/api';
import { formatDate, todayIso } from '../../utils/format';
import { useFeedback } from '../../context/FeedbackContext';
import type { WorkoutSession } from '../../types';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { Input } from '../common/Input';
import { Select } from '../common/Select';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { EmptyState } from '../common/EmptyState';
import { SearchInput } from '../common/ui';

const MUSCLE_GROUPS = ['Chest', 'Back', 'Shoulders', 'Biceps', 'Triceps', 'Legs', 'Core', 'Cardio', 'Other'];

interface Row {
  exercise_id: number;
  sets: string;
  reps: string;
  weight: string;
}

const rowsFrom = (day: WorkoutSession | undefined): Row[] =>
  (day?.exercises ?? []).map((e) => ({
    exercise_id: e.exercise_id,
    sets: e.sets_completed ? String(e.sets_completed) : '',
    reps: e.reps ? String(e.reps) : '',
    weight: e.weight_used ? String(e.weight_used) : '',
  }));

interface Props {
  isOpen: boolean;
  onClose: () => void;
  initialClientId?: number;
  initialDate?: string;
}

export const WorkoutLogModal: React.FC<Props> = ({ isOpen, onClose, initialClientId, initialDate }) => (
  <Modal isOpen={isOpen} onClose={onClose} title="Log workout" description="Pick the exercises they did. Sets, reps and weight are optional." size="2xl">
    {isOpen && <WorkoutLogForm key={`${initialClientId}-${initialDate}`} onClose={onClose} initialClientId={initialClientId} initialDate={initialDate} />}
  </Modal>
);

const WorkoutLogForm: React.FC<Omit<Props, 'isOpen'>> = ({ onClose, initialClientId, initialDate }) => {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { toast, confirm } = useFeedback();
  const [clientId, setClientId] = useState<number | ''>(initialClientId ?? '');
  const [date, setDate] = useState(initialDate && initialDate <= todayIso() ? initialDate : todayIso());
  const [rows, setRows] = useState<Row[]>([]);
  const [search, setSearch] = useState('');
  const [group, setGroup] = useState('All');
  const [error, setError] = useState<string | null>(null);
  // The client+day the rows were loaded for, so a refetch never wipes edits.
  const [loadedKey, setLoadedKey] = useState<string | null>(null);

  const { data: roster = [] } = useQuery({ queryKey: ['roster'], queryFn: clientService.getRoster });
  const { data: exercises = [], isLoading: exercisesLoading } = useQuery({ queryKey: ['exercises'], queryFn: () => exerciseService.getExercises() });
  const byId = useMemo(() => new Map(exercises.map((e) => [e.id, e])), [exercises]);

  const dayKey = clientId && date ? `${clientId}|${date}` : null;
  const { data: daySessions, isFetching: dayLoading } = useQuery({
    queryKey: ['sessions', { client_id: clientId, session_date: date }],
    queryFn: () => sessionService.getSessions({ client_id: Number(clientId), session_date: date }),
    enabled: !!dayKey,
  });
  const existing = daySessions?.[0];
  if (dayKey && daySessions && loadedKey !== dayKey) {
    setLoadedKey(dayKey);
    setRows(rowsFrom(existing));
  }

  const selected = new Set(rows.map((r) => r.exercise_id));
  const toggle = (id: number) =>
    setRows((cur) => (cur.some((r) => r.exercise_id === id) ? cur.filter((r) => r.exercise_id !== id) : [...cur, { exercise_id: id, sets: '', reps: '', weight: '' }]));
  const setField = (id: number, field: keyof Omit<Row, 'exercise_id'>, value: string) =>
    setRows((cur) => cur.map((r) => (r.exercise_id === id ? { ...r, [field]: value.replace(/[^\d.]/g, '') } : r)));

  const q = search.trim().toLowerCase();
  const visible = exercises
    .filter((e) => (group === 'All' || e.muscle_group === group) && (!q || e.name.toLowerCase().includes(q) || e.muscle_group.toLowerCase().includes(q)))
    .sort((a, b) => a.name.localeCompare(b.name));
  const groups = ['All', ...MUSCLE_GROUPS.filter((g) => exercises.some((e) => e.muscle_group === g))];

  const save = useMutation({
    mutationFn: () =>
      sessionService.setDayExercises({
        client_id: Number(clientId),
        date,
        exercise_ids: rows.map((r) => r.exercise_id),
        details: rows.map((r) => ({
          exercise_id: r.exercise_id,
          sets_completed: r.sets ? Number(r.sets) : null,
          reps: r.reps ? Number(r.reps) : null,
          weight_used: r.weight ? Number(r.weight) : null,
        })),
      }),
    onSuccess: (saved) => {
      qc.invalidateQueries({ queryKey: ['sessions'] });
      qc.invalidateQueries({ queryKey: ['trainer-dashboard'] });
      const name = roster.find((c) => c.id === clientId)?.name ?? 'Client';
      toast(saved ? `Saved ${saved.exercises.length} exercise${saved.exercises.length === 1 ? '' : 's'} for ${name}.` : `Cleared ${name}'s workout for ${formatDate(date)}.`);
      onClose();
    },
    onError: (e) => setError(getApiErrorMessage(e, 'Could not save the workout.')),
  });

  const submit = async () => {
    if (!clientId) return setError('Choose a client.');
    for (const r of rows) {
      const name = byId.get(r.exercise_id)?.name ?? 'An exercise';
      if (r.sets && !(Number(r.sets) >= 1 && Number(r.sets) <= 50)) return setError(`${name}: sets must be 1–50.`);
      if (r.reps && !(Number(r.reps) >= 1 && Number(r.reps) <= 500)) return setError(`${name}: reps must be 1–500.`);
      if (r.weight && !(Number(r.weight) >= 0 && Number(r.weight) <= 1000)) return setError(`${name}: weight must be 0–1000 kg.`);
    }
    if (rows.length === 0) {
      if (!existing) return setError('Pick at least one exercise.');
      const ok = await confirm({ title: 'Remove this workout?', message: `No exercises are selected, so ${formatDate(date)} will be removed from the log.`, confirmLabel: 'Remove', danger: true });
      if (!ok) return;
    }
    setError(null);
    save.mutate();
  };

  const smallInput =
    'w-full h-9 rounded-lg bg-[var(--color-input)] border border-[var(--color-input-border)] px-2 text-center text-sm num focus:outline-none focus:border-[var(--color-input-focus)]';

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <Select
          label="Client"
          required
          placeholder="Choose a client"
          value={clientId}
          onChange={(e) => {
            setClientId(e.target.value ? Number(e.target.value) : '');
            setLoadedKey(null);
            setRows([]);
          }}
          options={roster.map((c) => ({ value: c.id, label: c.name }))}
        />
        <Input
          label="Date"
          type="date"
          max={todayIso()}
          value={date}
          onChange={(e) => {
            if (!e.target.value) return;
            setDate(e.target.value);
            setLoadedKey(null);
            setRows([]);
          }}
        />
      </div>

      {!clientId ? (
        <p className="text-sm text-[var(--color-text-secondary)] py-6 text-center">Choose a client to start.</p>
      ) : exercisesLoading || (dayKey && loadedKey !== dayKey && dayLoading) ? (
        <LoadingSpinner message="Loading…" />
      ) : exercises.length === 0 ? (
        <EmptyState
          bare
          icon={<Library className="w-6 h-6" />}
          title="Your exercise library is empty"
          description="Add exercises first, then come back to log them."
          actionLabel="Open exercise library"
          onAction={() => navigate('/exercises')}
        />
      ) : (
        <>
          {existing && <p className="text-xs text-[var(--color-text-secondary)] -mt-2">This day already has a workout. Saving updates it.</p>}

          {/* Selected */}
          <section aria-label="Selected exercises">
            <div className="flex items-center justify-between mb-2">
              <p className="eyebrow">
                Done today <span className="num text-[var(--color-accent-ink)]">· {rows.length}</span>
              </p>
              {rows.length > 0 && (
                <button type="button" onClick={() => setRows([])} className="text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text)] cursor-pointer">
                  Clear all
                </button>
              )}
            </div>
            {rows.length === 0 ? (
              <p className="text-sm text-[var(--color-text-muted)] py-4 text-center rounded-xl border border-dashed border-[var(--color-border)]">Tap exercises below to add them.</p>
            ) : (
              <ul className="rounded-xl border border-[var(--color-border)] divide-y divide-[var(--color-border)] bg-[var(--color-surface-secondary)]">
                <li className="hidden sm:grid grid-cols-[1fr_4.5rem_4.5rem_5rem_2rem] gap-2 px-3 py-2 eyebrow !text-[10px]">
                  <span>Exercise</span>
                  <span className="text-center">Sets</span>
                  <span className="text-center">Reps</span>
                  <span className="text-center">kg</span>
                  <span />
                </li>
                {rows.map((r) => (
                  <li key={r.exercise_id} className="grid grid-cols-[1fr_2rem] sm:grid-cols-[1fr_4.5rem_4.5rem_5rem_2rem] gap-2 items-center px-3 py-2">
                    <span className="text-sm font-medium truncate">{byId.get(r.exercise_id)?.name ?? 'Exercise'}</span>
                    <button
                      type="button"
                      onClick={() => toggle(r.exercise_id)}
                      className="sm:order-last w-8 h-8 flex items-center justify-center rounded-lg text-[var(--color-text-muted)] hover:text-rose-500 hover:bg-rose-500/10 cursor-pointer"
                      aria-label={`Remove ${byId.get(r.exercise_id)?.name}`}
                    >
                      <X className="w-4 h-4" />
                    </button>
                    <div className="col-span-2 sm:col-span-1 sm:contents grid grid-cols-3 gap-2">
                      <input inputMode="numeric" placeholder="Sets" aria-label="Sets" value={r.sets} onChange={(e) => setField(r.exercise_id, 'sets', e.target.value)} className={smallInput} />
                      <input inputMode="numeric" placeholder="Reps" aria-label="Reps" value={r.reps} onChange={(e) => setField(r.exercise_id, 'reps', e.target.value)} className={smallInput} />
                      <input inputMode="decimal" placeholder="kg" aria-label="Weight in kg" value={r.weight} onChange={(e) => setField(r.exercise_id, 'weight', e.target.value)} className={smallInput} />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* Picker */}
          <section aria-label="Exercise library" className="space-y-3">
            <SearchInput value={search} onChange={setSearch} placeholder="Search exercises" />
            <div className="flex gap-1.5 overflow-x-auto scrollbar-none -mx-1 px-1">
              {groups.map((g) => (
                <button
                  key={g}
                  type="button"
                  onClick={() => setGroup(g)}
                  className={`shrink-0 h-8 px-3 rounded-full text-xs font-medium border cursor-pointer transition-colors ${
                    group === g
                      ? 'bg-[var(--color-text)] text-[var(--color-background)] border-transparent'
                      : 'border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'
                  }`}
                >
                  {g}
                </button>
              ))}
            </div>
            <div className="max-h-[32vh] overflow-y-auto -mx-1 px-1">
              {visible.length === 0 ? (
                <p className="text-sm text-[var(--color-text-muted)] py-4 text-center">No exercises match.</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {visible.map((ex) => {
                    const on = selected.has(ex.id);
                    return (
                      <button
                        key={ex.id}
                        type="button"
                        aria-pressed={on}
                        onClick={() => toggle(ex.id)}
                        className={`inline-flex items-center gap-1.5 h-9 px-3 rounded-full border text-sm transition-colors cursor-pointer ${
                          on
                            ? 'bg-[var(--color-primary)] border-[var(--color-primary)] text-[var(--color-primary-text)] font-semibold'
                            : 'bg-[var(--color-surface-secondary)] border-[var(--color-border)] hover:border-[rgba(var(--color-primary-rgb),0.6)]'
                        }`}
                      >
                        {on && <Check className="w-3.5 h-3.5" strokeWidth={3} />}
                        {ex.name}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </section>
        </>
      )}

      {error && (
        <p role="alert" className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-sm text-rose-700 dark:text-rose-300">
          {error}
        </p>
      )}

      <div className="flex justify-end gap-2 pt-1">
        <Button variant="ghost" onClick={onClose}>
          Cancel
        </Button>
        <Button onClick={submit} isLoading={save.isPending} disabled={!clientId || (rows.length === 0 && !existing)}>
          Save workout
        </Button>
      </div>
    </div>
  );
};
