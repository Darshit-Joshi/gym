import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  CalendarCheck2,
  CheckCircle2,
  Dumbbell,
  IndianRupee,
  TrendingUp,
  UserPlus,
  Users,
  Wallet,
  Activity,
} from 'lucide-react';
import { dashboardService } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import { formatDate, formatMoney, formatRelativeTime, greeting, relativeDay, todayIso, weekdayShort } from '../../utils/format';
import type { ActivityItem, AttendanceTrendDay } from '../../types';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { Avatar } from '../../components/common/Avatar';
import { EmptyState } from '../../components/common/EmptyState';
import { Skeleton } from '../../components/common/LoadingSpinner';
import { CountUp } from '../../components/common/CountUp';
import { FeeStatusBadge } from '../../components/fees/FeeStatusBadge';
import { PageHeader, ProgressRing, SectionTitle, StatTile } from '../../components/common/ui';

// ----------------------------------------------------------------------------- Weekly check-ins chart

const WeekChart: React.FC<{ days: AttendanceTrendDay[] }> = ({ days }) => {
  const [hover, setHover] = useState<number | null>(null);
  const max = Math.max(4, ...days.map((d) => d.checked_in));
  const total = days.reduce((s, d) => s + d.checked_in, 0);
  const today = todayIso();

  return (
    <div>
      <div className="flex items-baseline gap-2 mb-5">
        <span className="num text-3xl font-semibold">{total}</span>
        <span className="text-sm text-[var(--color-text-secondary)]">check-ins in the last 7 days</span>
      </div>
      <div className="relative h-40">
        {/* recessive gridlines */}
        {[0.5, 1].map((f) => (
          <div key={f} className="absolute inset-x-0 border-t border-dashed border-[var(--color-border)]" style={{ bottom: `${f * 100}%` }}>
            <span className="absolute -top-2.5 right-0 text-[10px] num text-[var(--color-text-muted)] bg-[var(--color-surface)] pl-1">
              {Math.round(max * f)}
            </span>
          </div>
        ))}
        <div className="absolute inset-0 right-6 grid grid-cols-7 gap-2 items-end border-b border-[var(--color-border-strong)]">
          {days.map((d, i) => {
            const isToday = d.date === today;
            const h = (d.checked_in / max) * 100;
            return (
              <div
                key={d.date}
                className="relative h-full flex items-end justify-center cursor-default"
                onMouseEnter={() => setHover(i)}
                onMouseLeave={() => setHover(null)}
                onFocus={() => setHover(i)}
                onBlur={() => setHover(null)}
                tabIndex={0}
                aria-label={`${relativeDay(d.date)}: ${d.checked_in} checked in, ${d.absent} absent`}
              >
                {isToday && d.checked_in > 0 && (
                  <span className="absolute num text-xs font-semibold text-[var(--color-text)]" style={{ bottom: `calc(${h}% + 6px)` }}>
                    {d.checked_in}
                  </span>
                )}
                <div
                  className="w-full max-w-[28px] rounded-t-[4px] transition-all duration-300"
                  style={{
                    height: `${Math.max(h, d.checked_in > 0 ? 3 : 0)}%`,
                    background: isToday ? 'var(--color-primary)' : 'rgba(var(--color-primary-rgb), 0.38)',
                    opacity: hover === null || hover === i ? 1 : 0.55,
                  }}
                />
                {hover === i && (
                  <div className="absolute z-10 bottom-full mb-2 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-elevated)] px-2.5 py-1.5 text-xs shadow-[var(--shadow-dropdown)] pointer-events-none">
                    <p className="font-semibold text-[var(--color-text)]">{relativeDay(d.date)}</p>
                    <p className="text-[var(--color-text-secondary)]">
                      <span className="num">{d.checked_in}</span> checked in · <span className="num">{d.absent}</span> absent
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
      <div className="grid grid-cols-7 gap-2 mr-6 mt-2">
        {days.map((d) => (
          <span
            key={d.date}
            className={`text-center text-[11px] ${d.date === today ? 'font-semibold text-[var(--color-text)]' : 'text-[var(--color-text-muted)]'}`}
          >
            {d.date === today ? 'Today' : weekdayShort(d.date)}
          </span>
        ))}
      </div>
    </div>
  );
};

// ----------------------------------------------------------------------------- Activity feed

const ACTIVITY_ICON: Record<ActivityItem['kind'], { icon: React.ReactNode; tone: string }> = {
  ATTENDANCE: { icon: <CheckCircle2 className="w-3.5 h-3.5" />, tone: 'bg-[var(--color-accent-soft)] text-[var(--color-accent-ink)]' },
  PAYMENT: { icon: <IndianRupee className="w-3.5 h-3.5" />, tone: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400' },
  WORKOUT: { icon: <Dumbbell className="w-3.5 h-3.5" />, tone: 'bg-sky-500/15 text-sky-600 dark:text-sky-400' },
  CLIENT_ADDED: { icon: <UserPlus className="w-3.5 h-3.5" />, tone: 'bg-amber-500/15 text-amber-600 dark:text-amber-400' },
};

const ActivityFeed: React.FC<{ items: ActivityItem[] }> = ({ items }) => {
  if (items.length === 0) {
    return <p className="text-sm text-[var(--color-text-secondary)] py-6 text-center">Activity will show up here as you mark attendance, log workouts and record payments.</p>;
  }
  return (
    <ul className="relative space-y-1">
      {items.map((a, i) => (
        <li key={`${a.kind}-${a.client_id}-${a.at}-${i}`}>
          <Link
            to={`/clients/${a.client_id}`}
            className="flex items-center gap-3 p-2 -mx-2 rounded-xl hover:bg-[var(--color-hover)] transition-colors"
          >
            <div className="relative">
              <Avatar clientId={a.client_id} photo={a.client_photo} name={a.client_name} size="md" />
              <span className={`absolute -bottom-1 -right-1 w-5 h-5 rounded-full flex items-center justify-center ring-2 ring-[var(--color-surface)] ${ACTIVITY_ICON[a.kind].tone}`}>
                {ACTIVITY_ICON[a.kind].icon}
              </span>
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-[var(--color-text)] truncate">{a.client_name}</p>
              <p className="text-xs text-[var(--color-text-secondary)] truncate">{a.detail}</p>
            </div>
            <span className="text-[11px] text-[var(--color-text-muted)] shrink-0">{formatRelativeTime(a.at)}</span>
          </Link>
        </li>
      ))}
    </ul>
  );
};

// ----------------------------------------------------------------------------- Page

const DashboardSkeleton: React.FC = () => (
  <div className="space-y-6" role="status" aria-label="Loading dashboard">
    <Skeleton className="h-10 w-72" />
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
      {[0, 1, 2, 3].map((i) => (
        <Skeleton key={i} className="h-32 rounded-2xl" />
      ))}
    </div>
    <div className="grid lg:grid-cols-3 gap-4">
      <Skeleton className="h-64 rounded-2xl lg:col-span-2" />
      <Skeleton className="h-64 rounded-2xl" />
    </div>
  </div>
);

export const TrainerDashboardPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [hour] = useState(() => new Date().getHours());
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['trainer-dashboard'],
    queryFn: dashboardService.getTrainerDashboard,
    refetchInterval: 60_000,
  });

  if (isLoading) return <DashboardSkeleton />;
  if (isError || !data) {
    return (
      <EmptyState
        tone="error"
        icon={<AlertTriangle className="w-6 h-6" />}
        title="Couldn't load the dashboard"
        description="Check your connection and try again."
        actionLabel="Try again"
        onAction={() => refetch()}
      />
    );
  }

  const { today_attendance: att, billing } = data;
  const checkedIn = att.present + att.late;
  const roster = att.present + att.late + att.absent + att.unmarked;
  const marked = roster - att.unmarked;
  const firstName = (user?.name || 'Coach').split(' ')[0];

  const summary: string[] = [];
  if (att.unmarked > 0) summary.push(`${att.unmarked} still to mark today`);
  if (billing.overdue_count > 0) summary.push(`${billing.overdue_count} fee${billing.overdue_count === 1 ? '' : 's'} overdue`);

  return (
    <div className="space-y-6 sm:space-y-8">
      <PageHeader
        eyebrow="Dashboard"
        title={`${greeting(hour)}, ${firstName}`}
        description={summary.length ? summary.join(' · ') : "You're all caught up for today."}
        actions={
          <>
            <Button variant="secondary" leftIcon={<UserPlus className="w-4 h-4" />} onClick={() => navigate('/clients?action=add')}>
              Add client
            </Button>
            <Button leftIcon={<CalendarCheck2 className="w-4 h-4" />} onClick={() => navigate('/attendance')} className="lg:hidden">
              Mark attendance
            </Button>
          </>
        }
      />

      {/* Headline numbers */}
      <section className="fx-stagger grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4" aria-label="Key numbers">
        <StatTile
          label="Active clients"
          icon={<Users className="w-4 h-4" />}
          tone="lime"
          value={<CountUp value={data.active_clients} />}
          sub={`${data.total_clients} on your books`}
          onClick={() => navigate('/clients')}
        />
        <StatTile
          label="Checked in today"
          icon={<CalendarCheck2 className="w-4 h-4" />}
          tone="lime"
          value={
            <>
              <CountUp value={checkedIn} />
              <span className="text-lg text-[var(--color-text-muted)] font-medium"> / {roster}</span>
            </>
          }
          sub={att.unmarked > 0 ? `${att.unmarked} not marked yet` : 'Everyone marked'}
          onClick={() => navigate('/attendance')}
        />
        <StatTile
          label="Pending fees"
          icon={<Wallet className="w-4 h-4" />}
          tone={billing.overdue_count > 0 ? 'rose' : 'amber'}
          emphasize={billing.overdue_count > 0}
          value={<CountUp value={billing.outstanding_total} format={(n) => formatMoney(Math.round(n), billing.currency)} />}
          sub={
            billing.overdue_count > 0 ? (
              <span className="text-rose-600 dark:text-rose-400 font-medium">
                {formatMoney(billing.overdue_total, billing.currency)} overdue
              </span>
            ) : (
              'Nothing overdue'
            )
          }
          onClick={() => navigate('/fees')}
        />
        <StatTile
          label="Collected this month"
          icon={<TrendingUp className="w-4 h-4" />}
          tone="emerald"
          value={<CountUp value={billing.collected_this_month} format={(n) => formatMoney(Math.round(n), billing.currency)} />}
          sub="Payments recorded"
          onClick={() => navigate('/fees')}
        />
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Today */}
        <Card hero className="p-5 sm:p-6 flex flex-col">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-[15px] font-semibold">Today's floor</h2>
            <span className="eyebrow">{relativeDay(todayIso())}</span>
          </div>
          <div className="flex items-center gap-5">
            <ProgressRing value={roster ? marked / roster : 0} size={96} stroke={8} label={`${marked} of ${roster} marked`}>
              <div className="text-center leading-none">
                <span className="num text-2xl font-semibold">{marked}</span>
                <span className="block text-[10px] text-[var(--color-text-muted)] mt-1">of {roster}</span>
              </div>
            </ProgressRing>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm flex-1">
              {(
                [
                  ['Present', att.present, 'bg-emerald-500'],
                  ['Late', att.late, 'bg-amber-500'],
                  ['Absent', att.absent, 'bg-rose-500'],
                  ['To mark', att.unmarked, 'bg-[var(--color-text-muted)]'],
                ] as const
              ).map(([label, n, dot]) => (
                <div key={label}>
                  <dt className="flex items-center gap-1.5 text-xs text-[var(--color-text-secondary)]">
                    <span className={`w-1.5 h-1.5 rounded-full ${dot}`} aria-hidden="true" />
                    {label}
                  </dt>
                  <dd className="num text-lg font-semibold">{n}</dd>
                </div>
              ))}
            </dl>
          </div>
          <Button className="mt-6 w-full" rightIcon={<ArrowRight className="w-4 h-4" />} onClick={() => navigate('/attendance')}>
            {att.unmarked > 0 ? `Mark ${att.unmarked} remaining` : "Open today's sheet"}
          </Button>
        </Card>

        {/* Week */}
        <Card className="lg:col-span-2 p-5 sm:p-6">
          <SectionTitle
            title="Attendance this week"
            icon={<Activity className="w-4 h-4" />}
            action={
              <Link to="/attendance?view=monthly" className="text-xs font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text)]">
                Monthly view
              </Link>
            }
          />
          <WeekChart days={data.attendance_trend} />
        </Card>
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2 p-5 sm:p-6">
          <SectionTitle title="Recent activity" icon={<Activity className="w-4 h-4" />} />
          {data.total_clients === 0 ? (
            <EmptyState
              bare
              icon={<Users className="w-6 h-6" />}
              title="Add your first client"
              description="Once clients are on your books you can mark attendance, track fees and log workouts."
              actionLabel="Add client"
              actionIcon={<UserPlus className="w-4 h-4" />}
              onAction={() => navigate('/clients?action=add')}
            />
          ) : (
            <ActivityFeed items={data.recent_activity} />
          )}
        </Card>

        <Card className="p-5 sm:p-6">
          <SectionTitle
            title="Fees due soon"
            icon={<Wallet className="w-4 h-4" />}
            action={
              <Link to="/fees" className="text-xs font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text)]">
                All fees
              </Link>
            }
          />
          {billing.overdue_count > 0 && (
            <button
              type="button"
              onClick={() => navigate('/fees')}
              className="w-full mb-4 flex items-center gap-3 p-3 rounded-xl border border-rose-500/30 bg-rose-500/10 text-left cursor-pointer hover:bg-rose-500/15 transition-colors"
            >
              <AlertTriangle className="w-5 h-5 text-rose-500 shrink-0" />
              <span className="text-sm">
                <span className="font-semibold text-rose-700 dark:text-rose-300">
                  {billing.overdue_count} overdue · {formatMoney(billing.overdue_total, billing.currency)}
                </span>
                <span className="block text-xs text-[var(--color-text-secondary)]">Follow up and record payments</span>
              </span>
            </button>
          )}
          {data.upcoming_dues.length === 0 ? (
            <p className="text-sm text-[var(--color-text-secondary)] py-4 text-center">No fees due in the next 7 days.</p>
          ) : (
            <ul className="space-y-1">
              {data.upcoming_dues.map((d) => (
                <li key={d.fee_id}>
                  <Link
                    to={`/clients/${d.client_id}?tab=fees`}
                    className="flex items-center justify-between gap-3 p-2 -mx-2 rounded-xl hover:bg-[var(--color-hover)] transition-colors"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">{d.client_name}</p>
                      <p className="text-xs text-[var(--color-text-secondary)]">Due {formatDate(d.due_date)}</p>
                    </div>
                    <div className="text-right shrink-0 space-y-1">
                      <p className="num text-sm font-semibold">{formatMoney(d.balance, billing.currency)}</p>
                      <FeeStatusBadge status={d.status} />
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </section>
    </div>
  );
};
