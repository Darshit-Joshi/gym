import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { MessageCircle } from 'lucide-react';
import { feeService, getApiErrorMessage } from '../../services/api';
import type { FeeRecord } from '../../types';
import { cycleLabel, formatDate, formatMoney } from '../../utils/format';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { FeeStatusBadge } from './FeeStatusBadge';
import { AssignMembershipModal, RecordPaymentModal } from './FeeModals';
import { useFeedback } from '../../context/FeedbackContext';

/** Membership details, dues and payment history for one client. */
export const ClientFeesSection: React.FC<{ clientId: number }> = ({ clientId }) => {
  const qc = useQueryClient();
  const { confirm } = useFeedback();
  const [assignOpen, setAssignOpen] = useState(false);
  const [payFee, setPayFee] = useState<FeeRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['fees', 'client', clientId],
    queryFn: () => feeService.getClientAccount(clientId),
  });

  const stop = useMutation({
    mutationFn: () => feeService.stopMembership(clientId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['fees'] }),
    onError: (e) => setError(getApiErrorMessage(e)),
  });

  if (isLoading || !data) return <LoadingSpinner message="Loading fees..." />;
  const { membership: m, fees, currency } = data;

  return (
    <div className="space-y-4">
      <Card className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="font-semibold text-[var(--color-text)]">Membership</h2>
            {m.plan_id ? (
              <p className="text-sm text-[var(--color-text-secondary)]">
                {m.plan_name} · {formatMoney(m.fee_amount, currency)} {cycleLabel(m.duration_months).toLowerCase()} · since{' '}
                {formatDate(m.billing_start_date)}
              </p>
            ) : (
              <p className="text-sm text-[var(--color-text-secondary)]">No plan assigned, so no fees are tracked yet.</p>
            )}
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant={m.plan_id ? 'secondary' : 'primary'} onClick={() => setAssignOpen(true)}>
              {m.plan_id ? 'Change plan' : 'Assign plan'}
            </Button>
            {m.plan_id && (
              <Button
                size="sm"
                variant="ghost"
                isLoading={stop.isPending}
                onClick={async () => {
                  const ok = await confirm({
                    title: 'Stop billing this client?',
                    message: 'No new dues will be created. Existing fees and payments are kept.',
                    confirmLabel: 'Stop billing',
                    danger: true,
                  });
                  if (ok) stop.mutate();
                }}
              >
                Stop billing
              </Button>
            )}
          </div>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
          <div>
            <p className="text-xs text-[var(--color-text-secondary)]">Next due</p>
            <p className="font-semibold text-[var(--color-text)]">{formatDate(m.next_due_date)}</p>
          </div>
          <div>
            <p className="text-xs text-[var(--color-text-secondary)]">Balance</p>
            <p className={`font-semibold ${m.overdue_count > 0 ? 'text-rose-600 dark:text-rose-400' : 'text-[var(--color-text)]'}`}>
              {formatMoney(m.outstanding_amount, currency)}
            </p>
          </div>
          <div>
            <p className="text-xs text-[var(--color-text-secondary)]">Total paid</p>
            <p className="font-semibold text-[var(--color-text)]">{formatMoney(data.total_paid, currency)}</p>
          </div>
        </div>
        {error && <p className="text-sm text-rose-600 dark:text-rose-400">{error}</p>}
      </Card>

      <Card className="p-0 overflow-hidden">
        <h2 className="font-semibold text-[var(--color-text)] px-4 pt-4 pb-2">Fees & payments</h2>
        {fees.length === 0 ? (
          <p className="px-4 pb-4 text-sm text-[var(--color-text-secondary)]">No fees yet.</p>
        ) : (
          <ul className="divide-y divide-[var(--color-border)]">
            {fees.map((f) => (
              <li key={f.id} className="px-4 py-3 space-y-1.5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-sm font-medium text-[var(--color-text)]">
                      {formatDate(f.period_start)} – {formatDate(f.period_end)}
                    </p>
                    <p className="text-xs text-[var(--color-text-secondary)]">
                      Due {formatDate(f.due_date)} · {formatMoney(f.amount_due, currency)}
                      {f.balance > 0 && f.amount_paid > 0 && ` · ${formatMoney(f.balance, currency)} left`}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <FeeStatusBadge status={f.status} />
                    {f.balance > 0 && (
                      <Button size="sm" onClick={() => setPayFee(f)}>
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
                        className="p-2 rounded-lg text-emerald-700 dark:text-emerald-300 bg-emerald-500/10 border border-emerald-500/30 hover:bg-emerald-500/20"
                      >
                        <MessageCircle className="w-4 h-4" />
                      </a>
                    )}
                  </div>
                </div>
                {f.payments.map((p) => (
                  <p key={p.id} className="text-xs text-[var(--color-text-secondary)]">
                    Paid {formatMoney(p.amount, currency)} on {formatDate(p.paid_on)} ({p.method.replace('_', ' ').toLowerCase()}
                    {p.reference ? `, ref ${p.reference}` : ''})
                  </p>
                ))}
              </li>
            ))}
          </ul>
        )}
      </Card>

      <AssignMembershipModal member={assignOpen ? m : null} currency={currency} onClose={() => setAssignOpen(false)} />
      <RecordPaymentModal fee={payFee} currency={currency} onClose={() => setPayFee(null)} />
    </div>
  );
};
