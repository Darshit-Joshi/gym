import React, { useState } from 'react';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { AlertTriangle, Archive, ChevronLeft, ChevronRight, Phone, SearchX, UserPlus, Users } from 'lucide-react';
import { clientService, getApiErrorMessage } from '../../services/api';
import type { Client } from '../../types';
import { formatDate, formatMoney } from '../../utils/format';
import { useDebounced } from '../../utils/useDebounced';
import { useFeedback } from '../../context/FeedbackContext';
import { Button } from '../../components/common/Button';
import { Avatar } from '../../components/common/Avatar';
import { ClientStatusBadge } from '../../components/common/Badge';
import { EmptyState } from '../../components/common/EmptyState';
import { SkeletonList } from '../../components/common/LoadingSpinner';
import { PageHeader, SearchInput, Segmented } from '../../components/common/ui';
import { PaymentStandingBadge } from '../../components/fees/FeeStatusBadge';
import { ClientFormModal } from '../../components/clients/ClientFormModal';

type StatusFilter = 'current' | 'Active' | 'Inactive' | 'Archived' | 'all';
const STATUS_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: 'current', label: 'Current' },
  { value: 'Active', label: 'Active' },
  { value: 'Inactive', label: 'Inactive' },
  { value: 'Archived', label: 'Archived' },
  { value: 'all', label: 'All' },
];
const GOALS = ['All goals', 'General Fitness', 'Weight Loss', 'Muscle Gain', 'Strength', 'Endurance', 'Other'];
const PAGE_SIZE = 20;

export const ClientsPage: React.FC = () => {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { toast, confirm } = useFeedback();
  const [searchParams, setSearchParams] = useSearchParams();

  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<StatusFilter>('current');
  const [goal, setGoal] = useState('All goals');
  const [page, setPage] = useState(1);
  const debouncedSearch = useDebounced(search.trim());

  const addOpen = searchParams.get('action') === 'add';
  const setAddOpen = (open: boolean) => setSearchParams(open ? { action: 'add' } : {}, { replace: true });

  const filters = { search: debouncedSearch, status, goal };
  const { data, isLoading, isError, isFetching, refetch } = useQuery({
    queryKey: ['clients', 'list', filters, page],
    queryFn: () =>
      clientService.getClients({
        search: debouncedSearch || undefined,
        status,
        goal: goal === 'All goals' ? undefined : goal,
        page,
        page_size: PAGE_SIZE,
      }),
    placeholderData: keepPreviousData,
  });

  const archive = useMutation({
    mutationFn: (c: Client) => clientService.archiveClient(c.id),
    onSuccess: (_, c) => {
      qc.invalidateQueries({ queryKey: ['clients'] });
      qc.invalidateQueries({ queryKey: ['roster'] });
      qc.invalidateQueries({ queryKey: ['trainer-dashboard'] });
      toast(`${c.name} archived. Their history is kept.`);
    },
    onError: (e) => toast(getApiErrorMessage(e, 'Could not archive the client.'), 'error'),
  });

  const askArchive = async (c: Client) => {
    const ok = await confirm({
      title: `Archive ${c.name}?`,
      message: 'They leave your roster and attendance sheet and stop being billed. Attendance, fees and workouts are kept, and you can restore them any time.',
      confirmLabel: 'Archive',
      danger: true,
    });
    if (ok) archive.mutate(c);
  };

  const changeFilter = <T,>(setter: (v: T) => void) => (v: T) => {
    setter(v);
    setPage(1);
  };

  const clients = data?.items ?? [];
  const filtered = !!debouncedSearch || status !== 'current' || goal !== 'All goals';

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Roster"
        title="Clients"
        description={data ? `${data.total} ${status === 'current' ? 'current' : status === 'all' ? '' : status.toLowerCase()} client${data.total === 1 ? '' : 's'}`.replace('  ', ' ') : undefined}
        actions={
          <Button leftIcon={<UserPlus className="w-4 h-4" />} onClick={() => setAddOpen(true)}>
            Add client
          </Button>
        }
      />

      <div className="flex flex-col lg:flex-row gap-3 lg:items-center">
        <SearchInput
          value={search}
          onChange={(v) => {
            setSearch(v);
            setPage(1);
          }}
          placeholder="Search name, phone or email"
          className="lg:w-80"
        />
        <Segmented label="Status" value={status} onChange={changeFilter(setStatus)} options={STATUS_OPTIONS} />
        <select
          value={goal}
          onChange={(e) => changeFilter(setGoal)(e.target.value)}
          aria-label="Filter by goal"
          className="h-11 px-3.5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-sm text-[var(--color-text)] cursor-pointer lg:ml-auto"
        >
          {GOALS.map((g) => (
            <option key={g} value={g}>
              {g}
            </option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <SkeletonList rows={6} />
      ) : isError ? (
        <EmptyState
          tone="error"
          icon={<AlertTriangle className="w-6 h-6" />}
          title="Couldn't load clients"
          description="Check your connection and try again."
          actionLabel="Try again"
          onAction={() => refetch()}
        />
      ) : clients.length === 0 ? (
        filtered ? (
          <EmptyState
            icon={<SearchX className="w-6 h-6" />}
            title="No clients match"
            description="Try a different name or clear the filters."
            actionLabel="Clear filters"
            onAction={() => {
              setSearch('');
              setStatus('current');
              setGoal('All goals');
            }}
          />
        ) : (
          <EmptyState
            icon={<Users className="w-6 h-6" />}
            title="No clients yet"
            description="Add the people you train to start tracking their attendance, fees and workouts."
            actionLabel="Add your first client"
            actionIcon={<UserPlus className="w-4 h-4" />}
            onAction={() => setAddOpen(true)}
          />
        )
      ) : (
        <div className={`transition-opacity ${isFetching ? 'opacity-70' : ''}`}>
          {/* Phone and tablet: cards */}
          <ul className="fx-stagger grid grid-cols-1 sm:grid-cols-2 gap-3 lg:hidden">
            {clients.map((c) => (
              <li key={c.id}>
                <Link to={`/clients/${c.id}`} className="panel fx-card-interactive flex items-center gap-3.5 p-4">
                  <Avatar clientId={c.id} photo={c.profile_photo} name={c.name} size="lg" />
                  <div className="min-w-0 flex-1 space-y-1.5">
                    <p className="font-semibold truncate">{c.name}</p>
                    <p className="text-xs text-[var(--color-text-secondary)] truncate">
                      {c.phone || 'No phone'} · {c.fitness_goal || 'General Fitness'}
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      <ClientStatusBadge status={c.status} />
                      <PaymentStandingBadge status={c.payment_status} />
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-[var(--color-text-muted)] shrink-0" />
                </Link>
              </li>
            ))}
          </ul>

          {/* Desktop: table */}
          <div className="hidden lg:block panel overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b border-[var(--color-border)] bg-[var(--color-surface-secondary)]">
                  {['Client', 'Phone', 'Joined', 'Status', 'Fees', ''].map((h) => (
                    <th key={h} className="eyebrow font-semibold px-5 py-3">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-border)]">
                {clients.map((c) => (
                  <tr
                    key={c.id}
                    onClick={() => navigate(`/clients/${c.id}`)}
                    className="group cursor-pointer hover:bg-[var(--color-hover)] transition-colors"
                  >
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-3">
                        <Avatar clientId={c.id} photo={c.profile_photo} name={c.name} />
                        <div className="min-w-0">
                          <Link
                            to={`/clients/${c.id}`}
                            onClick={(e) => e.stopPropagation()}
                            className="font-semibold group-hover:text-[var(--color-accent-ink)] transition-colors"
                          >
                            {c.name}
                          </Link>
                          <p className="text-xs text-[var(--color-text-muted)]">{c.fitness_goal || 'General Fitness'}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3 text-[var(--color-text-secondary)]">
                      {c.phone ? (
                        <span className="inline-flex items-center gap-1.5">
                          <Phone className="w-3.5 h-3.5 text-[var(--color-text-muted)]" />
                          {c.phone}
                        </span>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="px-5 py-3 text-[var(--color-text-secondary)] whitespace-nowrap">{formatDate(c.joined_date)}</td>
                    <td className="px-5 py-3">
                      <ClientStatusBadge status={c.status} />
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2">
                        <PaymentStandingBadge status={c.payment_status} />
                        {!!c.outstanding_amount && (
                          <span className="num text-xs text-[var(--color-text-secondary)]">{formatMoney(c.outstanding_amount)}</span>
                        )}
                      </div>
                    </td>
                    <td className="px-5 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                      {c.status !== 'Archived' && (
                        <button
                          type="button"
                          onClick={() => askArchive(c)}
                          className="p-2 rounded-lg text-[var(--color-text-muted)] opacity-0 group-hover:opacity-100 focus:opacity-100 hover:text-rose-500 hover:bg-rose-500/10 transition cursor-pointer"
                          aria-label={`Archive ${c.name}`}
                          title="Archive"
                        >
                          <Archive className="w-4 h-4" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {data && data.total_pages > 1 && (
            <div className="flex items-center justify-between gap-3 mt-4 text-sm text-[var(--color-text-secondary)]">
              <span>
                {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, data.total)} of {data.total}
              </span>
              <div className="flex gap-2">
                <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)} leftIcon={<ChevronLeft className="w-4 h-4" />}>
                  Previous
                </Button>
                <Button variant="secondary" size="sm" disabled={page >= data.total_pages} onClick={() => setPage((p) => p + 1)} rightIcon={<ChevronRight className="w-4 h-4" />}>
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      <ClientFormModal
        isOpen={addOpen}
        onClose={() => setAddOpen(false)}
        onSaved={(c) => {
          setAddOpen(false);
          toast(`${c.name} added.`);
          navigate(`/clients/${c.id}`);
        }}
      />
    </div>
  );
};
