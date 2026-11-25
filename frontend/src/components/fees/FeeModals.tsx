import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { feeService, getApiErrorMessage } from '../../services/api';
import type { ClientMembershipInfo, FeeRecord, MembershipPlan, PaymentMethod } from '../../types';
import { cycleLabel, formatDate, formatMoney, todayIso } from '../../utils/format';
import { Modal } from '../common/Modal';
import { Input } from '../common/Input';
import { Select } from '../common/Select';
import { Button } from '../common/Button';

const PAYMENT_METHODS: { value: PaymentMethod; label: string }[] = [
  { value: 'CASH', label: 'Cash' },
  { value: 'UPI', label: 'UPI' },
  { value: 'CARD', label: 'Card' },
  { value: 'BANK_TRANSFER', label: 'Bank transfer' },
  { value: 'OTHER', label: 'Other' },
];

const MONEY_PATTERN = /^\d{1,8}(\.\d{1,2})?$/;

const ErrorBox: React.FC<{ message: string | null }> = ({ message }) =>
  message ? (
    <div role="alert" className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-sm text-rose-600 dark:text-rose-400">
      {message}
    </div>
  ) : null;

const invalidateFees = (qc: ReturnType<typeof useQueryClient>) => {
  qc.invalidateQueries({ queryKey: ['fees'] });
  qc.invalidateQueries({ queryKey: ['trainer-dashboard'] });
  qc.invalidateQueries({ queryKey: ['monthly-report'] });
};

// ----------------------------------------------------------------------------- Record payment

type RecordPaymentProps = {
  fee: FeeRecord | null;
  currency: string;
  onClose: () => void;
  onSaved?: (fee: FeeRecord) => void;
};

export const RecordPaymentModal: React.FC<RecordPaymentProps> = (props) => (
  <Modal
    isOpen={!!props.fee}
    onClose={props.onClose}
    title="Record payment"
    description={props.fee ? `${props.fee.client_name} · ${formatDate(props.fee.period_start)} – ${formatDate(props.fee.period_end)}` : undefined}
  >
    {props.fee && <RecordPaymentForm key={props.fee.id} {...props} fee={props.fee} />}
  </Modal>
);

const RecordPaymentForm: React.FC<RecordPaymentProps & { fee: FeeRecord }> = ({ fee, currency, onClose, onSaved }) => {
  const qc = useQueryClient();
  const [amount, setAmount] = useState(String(fee.balance));
  const [paidOn, setPaidOn] = useState(todayIso());
  const [method, setMethod] = useState<PaymentMethod>('CASH');
  const [reference, setReference] = useState('');
  const [notes, setNotes] = useState('');
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      feeService.recordPayment(fee.id, {
        amount,
        paid_on: paidOn,
        method,
        reference: reference.trim() || undefined,
        notes: notes.trim() || undefined,
      }),
    onSuccess: (updated) => {
      invalidateFees(qc);
      onSaved?.(updated);
      onClose();
    },
    onError: (e) => setError(getApiErrorMessage(e)),
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!MONEY_PATTERN.test(amount) || Number(amount) <= 0) return setError('Enter a valid amount, e.g. 1500 or 1500.50');
    if (Number(amount) > fee.balance) return setError(`Amount cannot exceed the balance of ${formatMoney(fee.balance, currency)}`);
    if (paidOn > todayIso()) return setError('Payment date cannot be in the future');
    setError(null);
    mutation.mutate();
  };

  return (
        <form onSubmit={submit} className="space-y-4">
          <div className="grid grid-cols-3 gap-2 text-center">
            {[
              ['Due', fee.amount_due],
              ['Paid', fee.amount_paid],
              ['Balance', fee.balance],
            ].map(([label, value]) => (
              <div key={label as string} className="p-2.5 rounded-lg bg-[var(--color-surface-elevated)] border border-[var(--color-border)]">
                <div className="text-[11px] uppercase tracking-wider font-semibold text-[var(--color-text-secondary)]">{label}</div>
                <div className="text-sm font-bold text-[var(--color-text)]">{formatMoney(value as number, currency)}</div>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input label="Amount" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} required />
            <Input label="Paid on" type="date" max={todayIso()} value={paidOn} onChange={(e) => setPaidOn(e.target.value)} required />
          </div>
          <Select label="Method" options={PAYMENT_METHODS} value={method} onChange={(e) => setMethod(e.target.value as PaymentMethod)} />
          <Input label="Reference" placeholder="UPI / transaction ID (optional)" maxLength={100} value={reference} onChange={(e) => setReference(e.target.value)} />
          <Input label="Notes" placeholder="Optional" maxLength={500} value={notes} onChange={(e) => setNotes(e.target.value)} />
          <ErrorBox message={error} />
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" isLoading={mutation.isPending}>
              Save payment
            </Button>
          </div>
        </form>
  );
};

// ----------------------------------------------------------------------------- Assign membership

type AssignProps = {
  member: ClientMembershipInfo | null;
  currency: string;
  onClose: () => void;
  onSaved?: (dues: number) => void;
};

export const AssignMembershipModal: React.FC<AssignProps> = (props) => (
  <Modal
    isOpen={!!props.member}
    onClose={props.onClose}
    title={props.member?.plan_id ? 'Change membership' : 'Assign membership'}
    description={props.member?.client_name}
  >
    {props.member && <AssignMembershipForm key={props.member.client_id} {...props} member={props.member} />}
  </Modal>
);

const AssignMembershipForm: React.FC<AssignProps & { member: ClientMembershipInfo }> = ({ member, currency, onClose, onSaved }) => {
  const qc = useQueryClient();
  const { data: plans = [] } = useQuery({ queryKey: ['fees', 'plans'], queryFn: feeService.getPlans });
  const selectable = plans.filter((p) => p.is_active || p.id === member.plan_id);
  const [planId, setPlanId] = useState<string>(member.plan_id ? String(member.plan_id) : '');
  const [feeAmount, setFeeAmount] = useState(member.fee_amount != null ? String(member.fee_amount) : '');
  const [startDate, setStartDate] = useState(member.billing_start_date ?? todayIso());
  const [error, setError] = useState<string | null>(null);

  const selectedPlan = plans.find((p) => String(p.id) === planId);

  const mutation = useMutation({
    mutationFn: () =>
      feeService.assignMembership(member.client_id, {
        plan_id: Number(planId),
        fee_amount: feeAmount || undefined,
        billing_start_date: startDate,
      }),
    onSuccess: (account) => {
      invalidateFees(qc);
      onSaved?.(account.fees.length);
      onClose();
    },
    onError: (e) => setError(getApiErrorMessage(e)),
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!planId) return setError('Choose a plan');
    if (feeAmount && (!MONEY_PATTERN.test(feeAmount) || Number(feeAmount) <= 0)) return setError('Enter a valid fee amount');
    setError(null);
    mutation.mutate();
  };

  return (
        <form onSubmit={submit} className="space-y-4">
          {selectable.length === 0 ? (
            <p className="text-sm text-[var(--color-text-secondary)]">Create a membership plan first (Fees → Manage plans).</p>
          ) : (
            <Select
              label="Plan"
              placeholder="Select a plan"
              value={planId}
              onChange={(e) => {
                setPlanId(e.target.value);
                const p = plans.find((x) => String(x.id) === e.target.value);
                if (p) setFeeAmount(String(p.price));
              }}
              options={selectable.map((p) => ({
                value: p.id,
                label: `${p.name} · ${formatMoney(p.price, currency)} ${cycleLabel(p.duration_months).toLowerCase()}`,
              }))}
              required
            />
          )}
          <Input
            label="Fee per cycle"
            inputMode="decimal"
            value={feeAmount}
            onChange={(e) => setFeeAmount(e.target.value)}
            helperText={selectedPlan ? `Plan price ${formatMoney(selectedPlan.price, currency)}. Change it to give this client a custom rate.` : undefined}
          />
          <Input
            label="Billing starts on"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            helperText="Each cycle's fee is due on its start date. Cycles that have already started are billed right away."
            required
          />
          <ErrorBox message={error} />
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" isLoading={mutation.isPending} disabled={selectable.length === 0}>
              Save
            </Button>
          </div>
        </form>
  );
};

// ----------------------------------------------------------------------------- Plans

/** One dialog to list, add, edit, deactivate and delete membership plans. */
export const ManagePlansModal: React.FC<{ open: boolean; currency: string; onClose: () => void }> = ({ open, currency, onClose }) => {
  const qc = useQueryClient();
  const [editing, setEditing] = useState<MembershipPlan | 'new' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { data: plans = [], isLoading } = useQuery({ queryKey: ['fees', 'plans'], queryFn: feeService.getPlans, enabled: open });

  const toggle = useMutation({
    mutationFn: (p: MembershipPlan) => feeService.updatePlan(p.id, { is_active: !p.is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['fees'] }),
    onError: (e) => setError(getApiErrorMessage(e)),
  });
  const remove = useMutation({
    mutationFn: feeService.deletePlan,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['fees'] }),
    onError: (e) => setError(getApiErrorMessage(e)),
  });

  const close = () => {
    setEditing(null);
    setError(null);
    onClose();
  };

  return (
    <Modal
      isOpen={open}
      onClose={close}
      title={editing === null ? 'Membership plans' : editing === 'new' ? 'New plan' : 'Edit plan'}
      description={editing && editing !== 'new' ? 'Changes apply to future dues. Existing fees keep their amounts.' : undefined}
    >
      {editing !== null ? (
        <PlanForm key={editing === 'new' ? 'new' : editing.id} plan={editing === 'new' ? null : editing} onDone={() => setEditing(null)} />
      ) : (
        <div className="space-y-3">
          {isLoading ? (
            <p className="text-sm text-[var(--color-text-secondary)]">Loading…</p>
          ) : plans.length === 0 ? (
            <p className="text-sm text-[var(--color-text-secondary)]">No plans yet. Add one, e.g. "Monthly" for {formatMoney(1500, currency)}.</p>
          ) : (
            <ul className="divide-y divide-[var(--color-border)] border border-[var(--color-border)] rounded-lg">
              {plans.map((p) => (
                <li key={p.id} className={`flex items-center justify-between gap-2 p-3 ${p.is_active ? '' : 'opacity-60'}`}>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-[var(--color-text)] truncate">
                      {p.name} {!p.is_active && <span className="text-xs font-normal">(inactive)</span>}
                    </p>
                    <p className="text-xs text-[var(--color-text-secondary)]">
                      {formatMoney(p.price, currency)} · {cycleLabel(p.duration_months)} · {p.client_count} client{p.client_count === 1 ? '' : 's'}
                    </p>
                  </div>
                  <div className="flex gap-1 shrink-0">
                    <Button size="sm" variant="ghost" onClick={() => setEditing(p)}>
                      Edit
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => toggle.mutate(p)}>
                      {p.is_active ? 'Deactivate' : 'Activate'}
                    </Button>
                    {p.client_count === 0 && (
                      <Button size="sm" variant="ghost" className="text-rose-600 dark:text-rose-400" onClick={() => remove.mutate(p.id)}>
                        Delete
                      </Button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
          <ErrorBox message={error} />
          <div className="flex justify-between gap-2 pt-1">
            <Button variant="ghost" onClick={close}>
              Close
            </Button>
            <Button onClick={() => setEditing('new')}>Add plan</Button>
          </div>
        </div>
      )}
    </Modal>
  );
};

const PlanForm: React.FC<{ plan: MembershipPlan | null; onDone: () => void }> = ({ plan, onDone }) => {
  const qc = useQueryClient();
  const [name, setName] = useState(plan?.name ?? '');
  const [price, setPrice] = useState(plan ? String(plan.price) : '');
  const [months, setMonths] = useState(String(plan?.duration_months ?? 1));
  const [description, setDescription] = useState(plan?.description ?? '');
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => {
      const body = { name: name.trim(), price, duration_months: Number(months), description: description.trim() || undefined };
      return plan ? feeService.updatePlan(plan.id, body) : feeService.createPlan(body);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['fees'] });
      onDone();
    },
    onError: (e) => setError(getApiErrorMessage(e)),
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return setError('Plan name is required');
    if (!MONEY_PATTERN.test(price) || Number(price) <= 0) return setError('Enter a valid price, e.g. 1500');
    setError(null);
    mutation.mutate();
  };

  return (
      <form onSubmit={submit} className="space-y-4">
        <Input label="Plan name" placeholder="e.g. Monthly Standard" maxLength={100} value={name} onChange={(e) => setName(e.target.value)} required />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Input label="Price" inputMode="decimal" value={price} onChange={(e) => setPrice(e.target.value)} required />
          <Select
            label="Billing cycle"
            value={months}
            onChange={(e) => setMonths(e.target.value)}
            options={[1, 2, 3, 6, 12].map((m) => ({ value: String(m), label: cycleLabel(m) }))}
          />
        </div>
        <Input label="Description" placeholder="Optional" maxLength={1000} value={description} onChange={(e) => setDescription(e.target.value)} />
        <ErrorBox message={error} />
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="ghost" onClick={onDone}>
            Back
          </Button>
          <Button type="submit" isLoading={mutation.isPending}>
            {plan ? 'Save changes' : 'Create plan'}
          </Button>
        </div>
      </form>
  );
};
