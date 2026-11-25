import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ChevronDown } from 'lucide-react';
import { clientService, getApiErrorMessage } from '../../services/api';
import { todayIso } from '../../utils/format';
import type { Client } from '../../types';
import { Modal } from '../common/Modal';
import { Input, Textarea } from '../common/Input';
import { Select } from '../common/Select';
import { Button } from '../common/Button';

const GOALS = ['General Fitness', 'Weight Loss', 'Muscle Gain', 'Strength', 'Endurance', 'Other'];

interface Props {
  isOpen: boolean;
  onClose: () => void;
  /** Edit this client; omit to add a new one. */
  client?: Client;
  onSaved: (client: Client) => void;
}

const formFrom = (c?: Client) => ({
  name: c?.name ?? '',
  phone: c?.phone ?? '',
  email: c?.email ?? '',
  gender: c?.gender ?? '',
  fitness_goal: c?.fitness_goal ?? 'General Fitness',
  status: c ? (c.status === 'Pending Activation' ? 'Active' : c.status) : 'Active',
  joined_date: c?.joined_date ?? todayIso(),
  date_of_birth: c?.date_of_birth ?? '',
  height: c?.height ? String(c.height) : '',
  current_weight: c?.current_weight ? String(c.current_weight) : '',
  emergency_contact: c?.emergency_contact ?? '',
  training_preferences: c?.training_preferences ?? '',
});

export const ClientFormModal: React.FC<Props> = ({ isOpen, onClose, client, onSaved }) => (
  <Modal
    isOpen={isOpen}
    onClose={onClose}
    title={client ? 'Edit client' : 'Add client'}
    description={client ? client.name : 'Only the name is required. You can fill in the rest later.'}
    size="lg"
  >
    {isOpen && <ClientForm key={client?.id ?? 'new'} client={client} onClose={onClose} onSaved={onSaved} />}
  </Modal>
);

const ClientForm: React.FC<Omit<Props, 'isOpen'>> = ({ client, onClose, onSaved }) => {
  const qc = useQueryClient();
  const [form, setForm] = useState(() => formFrom(client));
  const [more, setMore] = useState(!!client);
  const [error, setError] = useState<string | null>(null);
  const set =
    (key: keyof typeof form) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setForm((f) => ({ ...f, [key]: e.target.value }));

  const save = useMutation({
    mutationFn: () => {
      const num = (v: string) => (v.trim() ? Number(v) : null);
      const payload = {
        name: form.name.trim(),
        phone: form.phone.trim() || null,
        email: form.email.trim() || (client ? '' : null),
        gender: form.gender || null,
        fitness_goal: form.fitness_goal,
        status: form.status,
        joined_date: form.joined_date || null,
        date_of_birth: form.date_of_birth || null,
        height: num(form.height),
        current_weight: num(form.current_weight),
        emergency_contact: form.emergency_contact.trim() || null,
        training_preferences: form.training_preferences.trim() || null,
      };
      return client ? clientService.updateClient(client.id, payload) : clientService.createClient(payload);
    },
    onSuccess: (saved) => {
      qc.invalidateQueries({ queryKey: ['clients'] });
      qc.invalidateQueries({ queryKey: ['client', saved.id] });
      qc.invalidateQueries({ queryKey: ['roster'] });
      qc.invalidateQueries({ queryKey: ['trainer-dashboard'] });
      qc.invalidateQueries({ queryKey: ['daily-attendance'] });
      onSaved(saved);
    },
    onError: (e) => setError(getApiErrorMessage(e, 'Could not save the client.')),
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (form.name.trim().length < 2) return setError('Enter a name of at least 2 characters.');
    for (const [key, label, max] of [
      ['height', 'Height', 300],
      ['current_weight', 'Weight', 500],
    ] as const) {
      const v = form[key].trim();
      if (v && (!(Number(v) > 0) || Number(v) > max)) return setError(`${label} must be a number between 0 and ${max}.`);
    }
    setError(null);
    save.mutate();
  };

  return (
    <form onSubmit={submit} className="space-y-5" noValidate>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="sm:col-span-2">
          <Input label="Full name" required autoFocus placeholder="e.g. Rahul Sharma" value={form.name} onChange={set('name')} maxLength={255} />
        </div>
        <Input label="Phone" type="tel" inputMode="tel" placeholder="e.g. 98765 43210" value={form.phone} onChange={set('phone')} maxLength={50} />
        <Input label="Email" type="email" placeholder="Optional" value={form.email} onChange={set('email')} />
        <Select
          label="Goal"
          value={form.fitness_goal}
          onChange={set('fitness_goal')}
          options={GOALS.map((g) => ({ value: g, label: g }))}
        />
        <Select
          label="Status"
          value={form.status}
          onChange={set('status')}
          options={(client ? ['Active', 'Inactive', 'Archived'] : ['Active', 'Inactive']).map((s) => ({ value: s, label: s }))}
        />
        <Select
          label="Gender"
          value={form.gender}
          onChange={set('gender')}
          options={[
            { value: '', label: 'Not specified' },
            { value: 'Male', label: 'Male' },
            { value: 'Female', label: 'Female' },
            { value: 'Other', label: 'Other' },
          ]}
        />
        <Input label="Joined on" type="date" max={todayIso()} value={form.joined_date} onChange={set('joined_date')} />
      </div>

      <div className="rounded-xl border border-[var(--color-border)]">
        <button
          type="button"
          onClick={() => setMore((m) => !m)}
          aria-expanded={more}
          className="w-full flex items-center justify-between px-4 h-11 text-sm font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text)] cursor-pointer"
        >
          Body, health and emergency details
          <ChevronDown className={`w-4 h-4 transition-transform ${more ? 'rotate-180' : ''}`} />
        </button>
        {more && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-4 pt-1">
            <Input label="Date of birth" type="date" max={todayIso()} value={form.date_of_birth} onChange={set('date_of_birth')} />
            <Input label="Emergency contact" placeholder="Name and phone" value={form.emergency_contact} onChange={set('emergency_contact')} maxLength={100} />
            <Input label="Height (cm)" inputMode="decimal" placeholder="e.g. 175" value={form.height} onChange={set('height')} />
            <Input label="Weight (kg)" inputMode="decimal" placeholder="e.g. 72.5" value={form.current_weight} onChange={set('current_weight')} />
            <div className="sm:col-span-2">
              <Textarea
                label="Training notes / injuries"
                rows={2}
                placeholder="e.g. Prefers mornings, recovering from a shoulder strain"
                value={form.training_preferences}
                onChange={set('training_preferences')}
              />
            </div>
          </div>
        )}
      </div>

      {error && (
        <p role="alert" className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-sm text-rose-700 dark:text-rose-300">
          {error}
        </p>
      )}

      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" isLoading={save.isPending}>
          {client ? 'Save changes' : 'Add client'}
        </Button>
      </div>
    </form>
  );
};
