import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, ChevronLeft, ChevronRight, CircleDollarSign, Clock, Tag, TrendingUp, Wallet } from 'lucide-react';
import { feeService } from '../../services/api';
import { currentMonth, formatMoney, monthLabel, shiftMonth } from '../../utils/format';
import { useFeedback } from '../../context/FeedbackContext';
import { Button } from '../../components/common/Button';
import { Skeleton } from '../../components/common/LoadingSpinner';
import { PageHeader, Segmented, StatTile } from '../../components/common/ui';
import { ManagePlansModal } from '../../components/fees/FeeModals';
import { DuesTab } from './fees/DuesTab';
import { MembershipsTab } from './fees/MembershipsTab';

type View = 'dues' | 'memberships';

export const FeesPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const view: View = searchParams.get('view') === 'memberships' ? 'memberships' : 'dues';
  const [month, setMonth] = useState(currentMonth());
  const [plansOpen, setPlansOpen] = useState(false);
  const [membershipFilter, setMembershipFilter] = useState<'all' | 'without'>('all');
  const { toast } = useFeedback();

  const onToast = (kind: 'success' | 'error', text: string) => toast(text, kind);
  const setView = (v: View) => setSearchParams(v === 'dues' ? {} : { view: v }, { replace: true });

  const { data: summary } = useQuery({ queryKey: ['fees', 'summary', month], queryFn: () => feeService.getSummary(month) });
  const currency = summary?.currency ?? 'INR';
  const collectionPct = summary && summary.billed_amount > 0 ? Math.min(100, summary.collection_rate) : 0;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Billing"
        title="Fees"
        description="Who has paid, who owes, and what's coming up."
        actions={
          <>
            <div className="flex flex-1 sm:flex-none items-center justify-between gap-1 panel p-1">
              <button type="button" onClick={() => setMonth((m) => shiftMonth(m, -1))} className="w-10 h-10 flex items-center justify-center rounded-lg hover:bg-[var(--color-hover)] cursor-pointer" aria-label="Previous month">
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-sm font-semibold min-w-[7.5rem] sm:min-w-[8.5rem] text-center">{monthLabel(month)}</span>
              <button type="button" onClick={() => setMonth((m) => shiftMonth(m, 1))} className="w-10 h-10 flex items-center justify-center rounded-lg hover:bg-[var(--color-hover)] cursor-pointer" aria-label="Next month">
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
            <Button variant="secondary" leftIcon={<Tag className="w-4 h-4" />} onClick={() => setPlansOpen(true)}>
              Plans
            </Button>
          </>
        }
      />

      {!summary ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-32 rounded-2xl" />
          ))}
        </div>
      ) : (
        <section className="fx-stagger grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4" aria-label="Fee summary">
          <StatTile
            label={`Collected · ${summary.month_name.split(' ')[0]}`}
            icon={<TrendingUp className="w-4 h-4" />}
            tone="emerald"
            value={formatMoney(summary.collected_amount, currency)}
            sub="Payments received this month"
          />
          <StatTile
            label="Due this month"
            icon={<CircleDollarSign className="w-4 h-4" />}
            tone="lime"
            value={formatMoney(summary.billed_amount, currency)}
            sub={`${summary.paid_count} of ${summary.fees_due_count} paid`}
          >
            <div className="h-1.5 rounded-full bg-[var(--color-surface-secondary)] overflow-hidden" aria-hidden="true">
              <div className="h-full rounded-full bg-[var(--color-primary)] transition-all duration-500" style={{ width: `${collectionPct}%` }} />
            </div>
          </StatTile>
          <StatTile
            label="Pending (all)"
            icon={<Clock className="w-4 h-4" />}
            tone="amber"
            value={formatMoney(summary.outstanding_total, currency)}
            sub="Everything still unpaid"
          />
          <StatTile
            label="Overdue"
            icon={<AlertTriangle className="w-4 h-4" />}
            tone="rose"
            emphasize={summary.overdue_count > 0}
            value={formatMoney(summary.overdue_total, currency)}
            sub={summary.overdue_count ? `${summary.overdue_count} fee${summary.overdue_count === 1 ? '' : 's'} past grace` : 'Nothing overdue'}
          />
        </section>
      )}

      {summary && summary.clients_without_plan > 0 && (
        <div className="flex flex-col sm:flex-row sm:items-center gap-3 p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30">
          <Wallet className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0" />
          <p className="text-sm flex-1">
            <span className="font-semibold">{summary.clients_without_plan} active client{summary.clients_without_plan === 1 ? ' has' : 's have'} no membership plan</span>
            <span className="text-[var(--color-text-secondary)]">, so no fees are tracked for them.</span>
          </p>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              setMembershipFilter('without');
              setView('memberships');
            }}
          >
            Assign plans
          </Button>
        </div>
      )}

      <Segmented
        label="Fees view"
        value={view}
        onChange={setView}
        options={[
          { value: 'dues', label: 'Dues & payments' },
          { value: 'memberships', label: 'Memberships' },
        ]}
        className="w-fit"
      />

      {view === 'dues' ? (
        <DuesTab month={month} onToast={onToast} />
      ) : (
        <MembershipsTab key={membershipFilter} initialFilter={membershipFilter} onToast={onToast} />
      )}

      <ManagePlansModal open={plansOpen} currency={currency} onClose={() => setPlansOpen(false)} />
    </div>
  );
};
