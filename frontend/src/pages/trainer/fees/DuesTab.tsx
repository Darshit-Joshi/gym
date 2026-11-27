import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ChevronDown, ChevronLeft, ChevronRight, ChevronUp, IndianRupee, MessageCircle, Trash2 } from 'lucide-react';
import { useFeedback } from '../../../context/FeedbackContext';
import { SearchInput, Segmented } from '../../../components/common/ui';
import { feeService, getApiErrorMessage } from '../../../services/api';
import type { FeeRecord, FeeStatus } from '../../../types';
import { formatDate, formatMoney } from '../../../utils/format';
import { Button } from '../../../components/common/Button';
import { Card } from '../../../components/common/Card';
import { EmptyState } from '../../../components/common/EmptyState';
import { LoadingSpinner } from '../../../components/common/LoadingSpinner';
import { FeeStatusBadge } from '../../../components/fees/FeeStatusBadge';
import { RecordPaymentModal } from '../../../components/fees/FeeModals';

const STATUS_FILTERS: { key: '' | FeeStatus | 'UNPAID'; label: string }[] = [
  { key: 'UNPAID', label: 'Unpaid' },
  { key: 'OVERDUE', label: 'Overdue' },
  { key: 'PENDING', label: 'Due' },
  { key: 'PARTIAL', label: 'Partial' },
  { key: 'UPCOMING', label: 'Upcoming' },
  { key: 'PAID', label: 'Paid' },
  { key: 'WAIVED', label: 'Waived' },
  { key: '', label: 'All' },
];

interface Props {
  month: string;
  onToast: (kind: 'success' | 'error', text: string) => void;
}

export const DuesTab: React.FC<Props> = ({ month, onToast }) => {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { confirm } = useFeedback();
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<'' | FeeStatus | 'UNPAID'>('UNPAID');
  const [monthOnly, setMonthOnly] = useState(false);
  const [page, setPage] = useState(1);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [payFee, setPayFee] = useState<FeeRecord | null>(null);

  const params = {
    month: monthOnly ? month : undefined,
    status: status && status !== 'UNPAID' ? status : undefined,
    unpaid_only: status === 'UNPAID' || undefined,
    search: search.trim() || undefined,
    page,
    page_size: 20,
  };
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['fees', 'list', params],
    queryFn: () => feeService.getFees(params),
    placeholderData: (prev) => prev,
  });
  const currency = data?.currency ?? 'INR';

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ['fees'] });
    qc.invalidateQueries({ queryKey: ['trainer-dashboard'] });
  };
  const waive = useMutation({
    mutationFn: ({ id, waived }: { id: number; waived: boolean }) => feeService.updateFee(id, { is_waived: waived }),
    onSuccess: (f) => {
      refresh();
      onToast('success', f.is_waived ? 'Fee waived.' : 'Waiver removed.');
    },
    onError: (e) => onToast('error', getApiErrorMessage(e)),
  });
  const deletePayment = useMutation({
    mutationFn: feeService.deletePayment,
    onSuccess: () => {
      refresh();
      onToast('success', 'Payment deleted.');
    },
    onError: (e) => onToast('error', getApiErrorMessage(e)),
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-col lg:flex-row gap-3 lg:items-center">
        <SearchInput
          value={search}
          onChange={(v) => {
            setSearch(v);
            setPage(1);
          }}
          placeholder="Search client name or phone"
          className="lg:w-80"
        />
        <Segmented
          label="Fee status"
          size="sm"
          value={status || 'ALL'}
          onChange={(v) => {
            setStatus(v === 'ALL' ? '' : (v as '' | FeeStatus | 'UNPAID'));
            setPage(1);
          }}
          options={STATUS_FILTERS.map((f) => ({ value: f.key || 'ALL', label: f.label }))}
        />
        <label className="inline-flex items-center gap-2 text-sm text-[var(--color-text-secondary)] cursor-pointer whitespace-nowrap lg:ml-auto">
          <input
            type="checkbox"
            checked={monthOnly}
            onChange={(e) => {
              setMonthOnly(e.target.checked);
              setPage(1);
            }}
            className="accent-[var(--color-primary)] w-4 h-4"
          />
          Only this month's dues
        </label>
      </div>

      {isLoading ? (
        <LoadingSpinner message="Loading dues..." />
      ) : isError || !data ? (
        <EmptyState title="Unable to load dues" actionLabel="Try again" onAction={() => refetch()} />
      ) : data.items.length === 0 ? (
        <EmptyState
          icon={<IndianRupee className="w-6 h-6" />}
          title="No dues match these filters"
          description="Dues are created automatically for clients with a membership plan. Assign plans in the Memberships tab."
        />
      ) : (
        <Card className="p-0 overflow-hidden">
          <div className="hidden md:grid grid-cols-[1.6fr_1.3fr_1fr_1fr_1fr_auto] gap-3 px-4 py-3 eyebrow border-b border-[var(--color-border)] bg-[var(--color-surface-secondary)]">
            <span>Client</span>
            <span>Period · Due</span>
            <span className="text-right">Amount</span>
            <span className="text-right">Balance</span>
            <span>Status</span>
            <span className="w-[13rem] text-right">Actions</span>
          </div>
          <ul className="fx-stagger divide-y divide-[var(--color-border)]">
            {data.items.map((f) => (
              <li key={f.id}>
                <div className="grid grid-cols-[minmax(0,1fr)_auto] md:grid-cols-[1.6fr_1.3fr_1fr_1fr_1fr_auto] gap-x-3 gap-y-2.5 px-4 py-3.5 md:py-3 items-center">
                  <button onClick={() => navigate(`/clients/${f.client_id}`)} className="text-left min-w-0 cursor-pointer md:order-1">
                    <p className="text-sm font-bold text-[var(--color-text)] truncate hover:underline">{f.client_name}</p>
                    <p className="text-xs text-[var(--color-text-secondary)] truncate">{f.plan_name ?? '—'}</p>
                  </button>
                  {/* Phones: balance and status stacked at the right of the name. md+: separate columns. */}
                  <div className="flex flex-col items-end gap-1 md:contents">
                    <div className="hidden md:block md:order-3 text-right text-sm text-[var(--color-text)]">
                      {formatMoney(f.amount_due, currency)}
                      {f.amount_paid > 0 && <p className="text-[11px] text-[var(--color-text-secondary)]">paid {formatMoney(f.amount_paid, currency)}</p>}
                    </div>
                    <div className="md:order-4 text-right text-sm font-semibold num text-[var(--color-text)]">{formatMoney(f.balance, currency)}</div>
                    <div className="md:order-5">
                      <FeeStatusBadge status={f.status} />
                    </div>
                  </div>
                  <div className="col-span-2 md:col-span-1 md:order-2 text-xs text-[var(--color-text-secondary)]">
                    <p>
                      {formatDate(f.period_start)} – {formatDate(f.period_end)}
                    </p>
                    <p className={f.days_overdue > 0 ? 'text-rose-600 dark:text-rose-400 font-semibold' : ''}>
                      Due {formatDate(f.due_date)}
                      {f.days_overdue > 0 && ` · ${f.days_overdue}d late`}
                    </p>
                    {f.amount_paid > 0 && (
                      <p className="md:hidden">
                        Paid {formatMoney(f.amount_paid, currency)} of {formatMoney(f.amount_due, currency)}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center justify-end gap-1.5 col-span-2 md:col-span-1 md:order-6 md:w-[13rem]">
                    {f.balance > 0 && (
                      <Button size="sm" leftIcon={<IndianRupee className="w-3.5 h-3.5" />} onClick={() => setPayFee(f)} className="flex-1 md:flex-none">
                        Record payment
                      </Button>
                    )}
                    {f.reminder_whatsapp_link && (
                      <a
                        href={f.reminder_whatsapp_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        title="Send fee reminder on WhatsApp"
                        aria-label="Send fee reminder on WhatsApp"
                        className="w-9 h-9 shrink-0 flex items-center justify-center rounded-lg text-emerald-700 dark:text-emerald-300 bg-emerald-500/10 border border-emerald-500/30 hover:bg-emerald-500/20"
                      >
                        <MessageCircle className="w-4 h-4" />
                      </a>
                    )}
                    <button
                      onClick={() => setExpanded(expanded === f.id ? null : f.id)}
                      className="w-9 h-9 shrink-0 flex items-center justify-center rounded-lg text-[var(--color-text-secondary)] hover:bg-[var(--color-hover)] cursor-pointer"
                      aria-label="Show details"
                      aria-expanded={expanded === f.id}
                    >
                      {expanded === f.id ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {expanded === f.id && (
                  <div className="px-4 pb-4 space-y-3 bg-[var(--color-surface-elevated)]/50">
                    {f.notes && <p className="text-xs text-[var(--color-text-secondary)] pt-3">Note: {f.notes}</p>}
                    <div className="pt-3">
                      <p className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-2">Payments</p>
                      {f.payments.length === 0 ? (
                        <p className="text-xs text-[var(--color-text-muted)]">No payments recorded.</p>
                      ) : (
                        <ul className="space-y-1.5">
                          {f.payments.map((p) => (
                            <li key={p.id} className="flex items-center justify-between gap-2 text-xs p-2 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)]">
                              <span className="text-[var(--color-text)]">
                                <strong>{formatMoney(p.amount, currency)}</strong> · {p.method.replace('_', ' ')} · {formatDate(p.paid_on)}
                                {p.reference && <span className="text-[var(--color-text-secondary)]"> · Ref {p.reference}</span>}
                              </span>
                              <button
                                onClick={async () => {
                                  const ok = await confirm({
                                    title: `Delete payment of ${formatMoney(p.amount, currency)}?`,
                                    message: 'The balance reopens and the fee may show as due again.',
                                    confirmLabel: 'Delete payment',
                                    danger: true,
                                  });
                                  if (ok) deletePayment.mutate(p.id);
                                }}
                                className="w-8 h-8 shrink-0 flex items-center justify-center rounded-lg text-rose-600 dark:text-rose-400 hover:bg-rose-500/10 cursor-pointer"
                                aria-label="Delete payment"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                    <div className="flex gap-2">
                      {(f.status !== 'PAID' || f.is_waived) && (
                        <Button
                          variant="outline"
                          size="sm"
                          isLoading={waive.isPending}
                          onClick={async () => {
                            const ok = await confirm(
                              f.is_waived
                                ? { title: 'Remove the waiver?', message: 'The balance becomes payable again.', confirmLabel: 'Remove waiver' }
                                : { title: `Waive ${formatMoney(f.balance, currency)}?`, message: `${f.client_name} won't owe the rest of this fee.`, confirmLabel: 'Waive fee' },
                            );
                            if (ok) waive.mutate({ id: f.id, waived: !f.is_waived });
                          }}
                        >
                          {f.is_waived ? 'Remove waiver' : 'Waive fee'}
                        </Button>
                      )}
                    </div>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {data && data.total_pages > 1 && (
        <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-[var(--color-text-secondary)]">
          <span>
            Page {data.page} of {data.total_pages} · {data.total} dues
          </span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)} leftIcon={<ChevronLeft className="w-4 h-4" />}>
              Previous
            </Button>
            <Button variant="outline" size="sm" disabled={page >= data.total_pages} onClick={() => setPage((p) => p + 1)} rightIcon={<ChevronRight className="w-4 h-4" />}>
              Next
            </Button>
          </div>
        </div>
      )}

      <RecordPaymentModal
        fee={payFee}
        currency={currency}
        onClose={() => setPayFee(null)}
        onSaved={(f) => onToast('success', f.status === 'PAID' ? `${f.client_name}'s fee is fully paid.` : 'Payment recorded.')}
      />
    </div>
  );
};
