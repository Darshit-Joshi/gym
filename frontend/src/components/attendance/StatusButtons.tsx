import React from 'react';
import { Check, Clock, X } from 'lucide-react';
import type { AttendanceStatusType } from '../../types';

export const ATTENDANCE_STYLES: Record<
  AttendanceStatusType,
  { label: string; solid: string; text: string; cell: string; active: string; idle: string; icon: React.ReactNode }
> = {
  PRESENT: {
    label: 'Present',
    solid: 'bg-emerald-500',
    text: 'text-emerald-700 dark:text-emerald-300',
    cell: 'border-emerald-500/40 bg-emerald-500/10 hover:bg-emerald-500/15',
    active: 'bg-emerald-500 border-emerald-500 text-white dark:text-emerald-950 shadow-[0_6px_18px_-6px_rgba(16,185,129,0.7)]',
    idle: 'hover:border-emerald-500/60 hover:text-emerald-600 dark:hover:text-emerald-300',
    icon: <Check className="w-4 h-4" strokeWidth={2.5} />,
  },
  LATE: {
    label: 'Late',
    solid: 'bg-amber-500',
    text: 'text-amber-700 dark:text-amber-300',
    cell: 'border-amber-500/40 bg-amber-500/10 hover:bg-amber-500/15',
    active: 'bg-amber-400 border-amber-400 text-amber-950 shadow-[0_6px_18px_-6px_rgba(245,158,11,0.7)]',
    idle: 'hover:border-amber-500/60 hover:text-amber-600 dark:hover:text-amber-300',
    icon: <Clock className="w-4 h-4" strokeWidth={2.5} />,
  },
  ABSENT: {
    label: 'Absent',
    solid: 'bg-rose-500',
    text: 'text-rose-700 dark:text-rose-300',
    cell: 'border-rose-500/40 bg-rose-500/10 hover:bg-rose-500/15',
    active: 'bg-rose-500 border-rose-500 text-white shadow-[0_6px_18px_-6px_rgba(244,63,94,0.7)]',
    idle: 'hover:border-rose-500/60 hover:text-rose-600 dark:hover:text-rose-300',
    icon: <X className="w-4 h-4" strokeWidth={2.5} />,
  },
};

interface Props {
  value: AttendanceStatusType | null;
  onChange: (status: AttendanceStatusType) => void;
  disabled?: boolean;
  size?: 'md' | 'lg';
  /** Icon-only buttons on narrow rows. */
  compact?: boolean;
  name?: string;
}

/** Present / Late / Absent as three large tap targets. */
export const StatusButtons: React.FC<Props> = ({ value, onChange, disabled, size = 'md', compact, name }) => (
  <div role="radiogroup" aria-label={name ? `Attendance for ${name}` : 'Attendance'} className="grid grid-cols-3 gap-1.5">
    {(Object.keys(ATTENDANCE_STYLES) as AttendanceStatusType[]).map((s) => {
      const st = ATTENDANCE_STYLES[s];
      const on = value === s;
      return (
        <button
          key={s}
          type="button"
          role="radio"
          aria-checked={on}
          aria-label={st.label}
          disabled={disabled}
          onClick={() => !on && onChange(s)}
          className={`flex items-center justify-center gap-1.5 rounded-xl border font-semibold transition-all duration-150 active:scale-95 cursor-pointer disabled:cursor-wait ${
            size === 'lg' ? 'h-12 text-sm' : 'h-10 text-xs'
          } ${compact ? 'px-2.5' : 'px-3'} ${
            on ? `${st.active} fx-pop` : `border-[var(--color-border)] bg-[var(--color-surface-secondary)] text-[var(--color-text-secondary)] ${st.idle}`
          }`}
        >
          {st.icon}
          {!compact && <span>{st.label}</span>}
        </button>
      );
    })}
  </div>
);
