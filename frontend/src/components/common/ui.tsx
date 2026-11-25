import React from 'react';
import { Search, X } from 'lucide-react';

// ----------------------------------------------------------------------------- Page header

interface PageHeaderProps {
  title: string;
  eyebrow?: string;
  description?: React.ReactNode;
  actions?: React.ReactNode;
}

export const PageHeader: React.FC<PageHeaderProps> = ({ title, eyebrow, description, actions }) => (
  <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
    <div className="min-w-0">
      {eyebrow && <p className="eyebrow mb-1.5">{eyebrow}</p>}
      <h1 className="text-[26px] sm:text-3xl font-semibold text-[var(--color-text)] leading-tight">{title}</h1>
      {description && <p className="text-sm text-[var(--color-text-secondary)] mt-1.5 max-w-2xl">{description}</p>}
    </div>
    {actions && <div className="flex flex-wrap items-center gap-2 shrink-0">{actions}</div>}
  </header>
);

// ----------------------------------------------------------------------------- Stat tile

type Tone = 'lime' | 'emerald' | 'amber' | 'rose' | 'sky' | 'neutral';

const TONE_ICON: Record<Tone, string> = {
  lime: 'bg-[var(--color-accent-soft)] text-[var(--color-accent-ink)] border-[rgba(var(--color-primary-rgb),0.25)]',
  emerald: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
  amber: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
  rose: 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20',
  sky: 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20',
  neutral: 'bg-[var(--color-surface-elevated)] text-[var(--color-text-secondary)] border-[var(--color-border)]',
};

export const TONE_TEXT: Record<Tone, string> = {
  lime: 'text-[var(--color-accent-ink)]',
  emerald: 'text-emerald-600 dark:text-emerald-400',
  amber: 'text-amber-600 dark:text-amber-400',
  rose: 'text-rose-600 dark:text-rose-400',
  sky: 'text-sky-600 dark:text-sky-400',
  neutral: 'text-[var(--color-text)]',
};

interface StatTileProps {
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  icon?: React.ReactNode;
  tone?: Tone;
  /** Colour the value itself in the tone, for figures that need attention. */
  emphasize?: boolean;
  onClick?: () => void;
  children?: React.ReactNode;
  className?: string;
}

export const StatTile: React.FC<StatTileProps> = ({
  label,
  value,
  sub,
  icon,
  tone = 'neutral',
  emphasize = false,
  onClick,
  children,
  className = '',
}) => {
  const Tag = onClick ? 'button' : 'div';
  return (
    <Tag
      type={onClick ? 'button' : undefined}
      onClick={onClick}
      className={`panel p-4 sm:p-5 text-left flex flex-col gap-3 min-w-0 ${onClick ? 'fx-card-interactive cursor-pointer' : ''} ${className}`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="eyebrow truncate">{label}</span>
        {icon && <span className={`hidden sm:flex w-8 h-8 rounded-lg border items-center justify-center shrink-0 ${TONE_ICON[tone]}`}>{icon}</span>}
      </div>
      <div className="min-w-0">
        <div className={`num text-[28px] sm:text-[32px] leading-none font-semibold truncate ${emphasize ? TONE_TEXT[tone] : 'text-[var(--color-text)]'}`}>
          {value}
        </div>
        {sub && <div className="text-xs text-[var(--color-text-secondary)] mt-2 line-clamp-2">{sub}</div>}
      </div>
      {children}
    </Tag>
  );
};

// ----------------------------------------------------------------------------- Segmented control

interface SegmentedOption<T extends string> {
  value: T;
  label: React.ReactNode;
  count?: number;
}

interface SegmentedProps<T extends string> {
  value: T;
  onChange: (value: T) => void;
  options: SegmentedOption<T>[];
  label: string;
  size?: 'sm' | 'md';
  className?: string;
}

/** A row of mutually exclusive choices (filters and view switches). Scrolls sideways on phones. */
export function Segmented<T extends string>({ value, onChange, options, label, size = 'md', className = '' }: SegmentedProps<T>) {
  return (
    <div
      role="radiogroup"
      aria-label={label}
      className={`flex items-center gap-1 p-1 rounded-xl bg-[var(--color-surface-secondary)] border border-[var(--color-border)] overflow-x-auto scrollbar-none max-w-full ${className}`}
    >
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(opt.value)}
            className={`flex items-center gap-1.5 rounded-lg whitespace-nowrap font-medium transition-colors cursor-pointer ${
              size === 'sm' ? 'px-2.5 h-8 text-xs' : 'px-3.5 h-9 text-sm'
            } ${
              active
                ? 'bg-[var(--color-surface-elevated)] text-[var(--color-text)] shadow-[0_1px_0_rgba(255,255,255,0.04)_inset,0_1px_3px_rgba(0,0,0,0.3)] ring-1 ring-[var(--color-border-strong)]'
                : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'
            }`}
          >
            {opt.label}
            {opt.count !== undefined && (
              <span
                className={`num text-[11px] px-1.5 rounded-md ${
                  active ? 'bg-[var(--color-accent-soft)] text-[var(--color-accent-ink)]' : 'bg-[var(--color-hover)] text-[var(--color-text-muted)]'
                }`}
              >
                {opt.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

// ----------------------------------------------------------------------------- Search

interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  autoFocus?: boolean;
}

export const SearchInput: React.FC<SearchInputProps> = ({ value, onChange, placeholder = 'Search…', className = '', autoFocus }) => (
  <div className={`relative ${className}`}>
    <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] pointer-events-none" />
    <input
      type="search"
      value={value}
      autoFocus={autoFocus}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      aria-label={placeholder}
      className="w-full h-11 pl-10 pr-10 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] hover:border-[var(--color-border-strong)] text-sm text-[var(--color-text)] placeholder-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-input-focus)] focus:ring-2 focus:ring-[rgba(var(--color-primary-rgb),0.18)] transition-colors [&::-webkit-search-cancel-button]:hidden"
    />
    {value && (
      <button
        type="button"
        onClick={() => onChange('')}
        className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-md text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-hover)] cursor-pointer"
        aria-label="Clear search"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    )}
  </div>
);

// ----------------------------------------------------------------------------- Progress ring

interface ProgressRingProps {
  /** 0 to 1 */
  value: number;
  size?: number;
  stroke?: number;
  children?: React.ReactNode;
  label: string;
}

export const ProgressRing: React.FC<ProgressRingProps> = ({ value, size = 64, stroke = 6, children, label }) => {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(1, Number.isFinite(value) ? value : 0));
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }} role="img" aria-label={label}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--color-border)" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--color-primary)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - clamped)}
          style={{ transition: 'stroke-dashoffset 0.6s cubic-bezier(0.22, 1, 0.36, 1)' }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">{children}</div>
    </div>
  );
};

// ----------------------------------------------------------------------------- Section heading inside a card

export const SectionTitle: React.FC<{ title: string; action?: React.ReactNode; icon?: React.ReactNode }> = ({ title, action, icon }) => (
  <div className="flex items-center justify-between gap-3 mb-4">
    <h2 className="flex items-center gap-2 text-[15px] font-semibold text-[var(--color-text)]">
      {icon && <span className="text-[var(--color-text-muted)]">{icon}</span>}
      {title}
    </h2>
    {action}
  </div>
);
