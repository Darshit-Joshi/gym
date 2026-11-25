import React from 'react';
import { Link } from 'react-router-dom';
import { Pencil, Trash2 } from 'lucide-react';
import type { SessionExercise, WorkoutSession } from '../../types';
import { parseIso, relativeDay } from '../../utils/format';
import { Avatar } from '../common/Avatar';

/** "4 × 10 · 60 kg" when detail was recorded; empty when only the exercise was ticked. */
export const exerciseDetail = (se: SessionExercise): string => {
  const parts: string[] = [];
  if (se.sets_completed && se.reps) parts.push(`${se.sets_completed} × ${se.reps}`);
  else if (se.sets_completed) parts.push(`${se.sets_completed} sets`);
  else if (se.reps) parts.push(`${se.reps} reps`);
  if (se.weight_used) parts.push(`${se.weight_used} kg`);
  return parts.join(' · ');
};

interface Props {
  session: WorkoutSession;
  /** Show the client (on the all-clients log). */
  showClient?: boolean;
  /** Smaller, for previews. */
  compact?: boolean;
  onEdit?: () => void;
  onDelete?: () => void;
}

export const WorkoutDayCard: React.FC<Props> = ({ session, showClient, compact, onEdit, onDelete }) => {
  const date = parseIso(session.date);
  const withDetail = session.exercises.some((e) => exerciseDetail(e));

  return (
    <article className={`flex gap-4 ${compact ? 'p-3 rounded-xl bg-[var(--color-surface-secondary)] border border-[var(--color-border)]' : 'panel p-4 sm:p-5'}`}>
      {/* Date block */}
      <div className="w-12 shrink-0 text-center">
        <p className="eyebrow !text-[10px]">{date.toLocaleDateString(undefined, { month: 'short' })}</p>
        <p className="num text-2xl font-semibold leading-tight">{date.getDate()}</p>
        <p className="text-[10px] text-[var(--color-text-muted)]">{date.toLocaleDateString(undefined, { weekday: 'short' })}</p>
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            {showClient ? (
              <Link to={`/clients/${session.client_id}?tab=workouts`} className="flex items-center gap-2 group">
                <Avatar name={session.client_name || 'Client'} size="sm" />
                <span className="font-semibold truncate group-hover:text-[var(--color-accent-ink)]">{session.client_name}</span>
              </Link>
            ) : (
              <p className="font-semibold truncate">{session.workout_name || 'Workout'}</p>
            )}
            <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
              {showClient && session.workout_name ? `${session.workout_name} · ` : ''}
              {session.exercises.length} exercise{session.exercises.length === 1 ? '' : 's'}
              {['Today', 'Yesterday'].includes(relativeDay(session.date)) && ` · ${relativeDay(session.date)}`}
            </p>
          </div>
          {(onEdit || onDelete) && (
            <div className="flex gap-0.5 shrink-0 -mr-1.5 -mt-1">
              {onEdit && (
                <button type="button" onClick={onEdit} className="p-2 rounded-lg text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-hover)] cursor-pointer" aria-label="Edit this workout">
                  <Pencil className="w-4 h-4" />
                </button>
              )}
              {onDelete && (
                <button type="button" onClick={onDelete} className="p-2 rounded-lg text-[var(--color-text-muted)] hover:text-rose-500 hover:bg-rose-500/10 cursor-pointer" aria-label="Delete this workout">
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
            </div>
          )}
        </div>

        {session.exercises.length > 0 &&
          (withDetail && !compact ? (
            <ul className="mt-3 divide-y divide-[var(--color-border)] rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-secondary)]">
              {session.exercises.map((se) => (
                <li key={se.id ?? se.exercise_id} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
                  <span className="truncate">{se.exercise_name}</span>
                  <span className="num text-xs text-[var(--color-text-secondary)] shrink-0">{exerciseDetail(se) || '—'}</span>
                </li>
              ))}
            </ul>
          ) : (
            <ul className="mt-2.5 flex flex-wrap gap-1.5">
              {session.exercises.map((se) => {
                const d = exerciseDetail(se);
                return (
                  <li key={se.id ?? se.exercise_id} className="text-xs px-2.5 py-1 rounded-full bg-[var(--color-surface-elevated)] border border-[var(--color-border)]">
                    {se.exercise_name}
                    {d && <span className="num ml-1.5 text-[var(--color-text-muted)]">{d}</span>}
                  </li>
                );
              })}
            </ul>
          ))}
        {session.notes && !compact && <p className="mt-2.5 text-xs text-[var(--color-text-secondary)]">“{session.notes}”</p>}
      </div>
    </article>
  );
};
