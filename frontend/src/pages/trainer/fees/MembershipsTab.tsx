import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ChevronLeft, ChevronRight, Users } from 'lucide-react';
import { useFeedback } from '../../../context/FeedbackContext';
import { SearchInput, Segmented } from '../../../components/common/ui';
import { feeService, getApiErrorMessage } from '../../../services/api';
import type { ClientMembershipInfo } from '../../../types';
import { cycleLabel, formatDate, formatMoney } from '../../../utils/format';
import { Button } from '../../../components/common/Button';
import { Badge } from '../../../components/common/Badge';
import { Card } from '../../../components/common/Card';
import { EmptyState } from '../../../components/common/EmptyState';
import { LoadingSpinner } from '../../../components/common/LoadingSpinner';
import { AssignMembershipModal } from '../../../components/fees/FeeModals';

interface Props {
  initialFilter?: 'all' | 'with' | 'without';
  onToast: (kind: 'success' | 'error', text: string) => void;
}

export const MembershipsTab: React.FC<Props> = ({ initialFilter = 'all', onToast }) => {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { confirm } = useFeedback();
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<'all' | 'with' | 'without'>(initialFilter);
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<ClientMembershipInfo | null>(null);

  const params = {
    search: search.trim() || undefined,
    has_plan: filter === 'all' ? undefined : filter === 'with',
    page,
    page_size: 20,
  };
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['fees', 'memberships', params],
    queryFn: () => feeService.getMemberships(params),
    placeholderData: (prev) => prev,
  });
  const currency = data?.currency ?? 'INR';

  const stop = useMutation({
    mutationFn: feeService.stopMembership,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['fees'] });
      onToast('success', 'Billing stopped. Existing dues were kept.');
    },
    onError: (e) => onToast('error', getApiErrorMessage(e)),
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-3 sm:items-center">
        <SearchInput
          value={search}
          onChange={(v) => {
            setSearch(v);
            setPage(1);
          }}
          placeholder="Search client name or phone"
          className="sm:w-80"
        />
        <Segmented
          label="Membership filter"
          size="sm"
          value={filter}
          onChange={(v) => {
            setFilter(v);
            setPage(1);
          }}
          options={[
            { value: 'all', label: 'All clients' },
            { value: 'with', label: 'Billed' },
            { value: 'without', label: 'No plan' },
          ]}
        />
      </div>

      {isLoading ? (
        <LoadingSpinner message="Loading memberships..." />
      ) : isError || !data ? (
        <EmptyState title="Unable to load memberships" actionLabel="Try again" onAction={() => refetch()} />
      ) : data.items.length === 0 ? (
        <EmptyState icon={<Users className="w-6 h-6" />} title="No clients found" />
      ) : (
        <Card className="p-0 overflow-hidden">
          <ul className="divide-y divide-[var(--color-border)]">
            {data.items.map((m) => (
              <li key={m.client_id} className="grid grid-cols-2 md:grid-cols-[1.5fr_1.5fr_1fr_1fr_auto] gap-x-3 gap-y-2 px-4 py-3 items-center">
                <button onClick={() => navigate(`/clients/${m.client_id}`)} className="text-left min-w-0 cursor-pointer col-span-2 md:col-span-1">
                  <p className="text-sm font-semibold text-[var(--color-text)] truncate hover:text-[var(--color-accent-ink)]">{m.client_name}</p>
                  <p className="text-xs text-[var(--color-text-secondary)]">{m.client_status}</p>
                </button>
                <div className="text-sm">
                  {m.plan_name ? (
                    <>
                      <p className="font-semibold text-[var(--color-text)]">{m.plan_name}</p>
                      <p className="text-xs text-[var(--color-text-secondary)]">
                        {formatMoney(m.fee_amount, currency)} · {cycleLabel(m.duration_months)}
                      </p>
                    </>
                  ) : (
                    <Badge variant="neutral" size="sm">
                      No plan
                    </Badge>
                  )}
                </div>
                <div className="text-xs text-[var(--color-text-secondary)]">
                  <p className="eyebrow !text-[10px]">Next due</p>
                  <p className="text-sm text-[var(--color-text)]">{formatDate(m.next_due_date)}</p>
                </div>
                <div className="text-xs">
                  <p className="eyebrow !text-[10px]">Outstanding</p>
                  <p className={`text-sm font-bold ${m.overdue_count > 0 ? 'text-rose-600 dark:text-rose-400' : 'text-[var(--color-text)]'}`}>
                    {formatMoney(m.outstanding_amount, currency)}
                  </p>
                </div>
                <div className="flex gap-1.5 justify-end col-span-2 md:col-span-1">
                  <Button size="sm" variant={m.plan_id ? 'secondary' : 'primary'} onClick={() => setEditing(m)}>
                    {m.plan_id ? 'Change' : 'Assign plan'}
                  </Button>
                  {m.plan_id && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={async () => {
                        const ok = await confirm({
                          title: `Stop billing ${m.client_name}?`,
                          message: 'No new dues will be created. Existing dues and payments are kept.',
                          confirmLabel: 'Stop billing',
                          danger: true,
                        });
                        if (ok) stop.mutate(m.client_id);
                      }}
                    >
                      Stop
                    </Button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-between text-sm text-[var(--color-text-secondary)]">
          <span>
            Page {data.page} of {data.total_pages} · {data.total} clients
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

      <AssignMembershipModal
        member={editing}
        currency={currency}
        onClose={() => setEditing(null)}
        onSaved={() => onToast('success', 'Membership saved. Dues for started cycles were created.')}
      />
    </div>
  );
};
