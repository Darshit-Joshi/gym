import React, { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { CalendarCheck2, Dumbbell, Wallet } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useQuery } from '@tanstack/react-query';
import { authService, getApiErrorMessage } from '../../services/api';
import { Input } from '../../components/common/Input';
import { Button } from '../../components/common/Button';

const FEATURES = [
  { icon: CalendarCheck2, text: 'Mark attendance in one tap' },
  { icon: Wallet, text: 'See who has paid and who owes' },
  { icon: Dumbbell, text: "Log every client's workouts" },
];

export const LoginPage: React.FC = () => {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const { data: setup } = useQuery({ queryKey: ['setup-status'], queryFn: authService.getSetupStatus, staleTime: Infinity });

  if (isAuthenticated) return <Navigate to="/dashboard" replace />;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      await login(email.trim().toLowerCase(), password);
      navigate('/dashboard');
    } catch (err) {
      setError(getApiErrorMessage(err, 'Invalid email or password.'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative isolate min-h-screen bg-[var(--color-background)] text-[var(--color-text)] grid lg:grid-cols-[1.1fr_1fr]">
      <div className="fx-ambient" aria-hidden="true" />

      {/* Brand panel */}
      <section className="hidden lg:flex panel-hero !rounded-none !border-0 !border-r !border-[var(--color-border)] flex-col justify-between p-12">
        <div className="flex items-center gap-3">
          <span
            className="w-10 h-10 rounded-xl bg-[var(--color-primary)] text-[var(--color-primary-text)] flex items-center justify-center text-xl font-bold"
            style={{ fontFamily: 'var(--font-display)' }}
            aria-hidden="true"
          >
            1
          </span>
          <span className="text-sm font-semibold tracking-[0.2em] uppercase text-[var(--color-text-secondary)]">Trainer workspace</span>
        </div>
        <div className="max-w-md">
          <p className="eyebrow mb-4">OneCountry Fitness</p>
          <h1 className="text-5xl font-semibold leading-[1.05]">
            Run your floor.
            <br />
            <span className="text-[var(--color-accent-ink)]">Not your paperwork.</span>
          </h1>
          <ul className="mt-10 space-y-4">
            {FEATURES.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-3 text-[var(--color-text-secondary)]">
                <span className="w-9 h-9 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-elevated)] flex items-center justify-center text-[var(--color-accent-ink)]">
                  <Icon className="w-4 h-4" />
                </span>
                {text}
              </li>
            ))}
          </ul>
        </div>
        <p className="text-xs text-[var(--color-text-muted)]">© {new Date().getFullYear()} OneCountry Fitness n Spa</p>
      </section>

      {/* Form */}
      <section className="flex items-center justify-center px-4 py-10 sm:px-8">
        <div className="fx-page w-full max-w-sm">
          <div className="mb-8 text-center lg:text-left">
            <div className="inline-flex items-center justify-center w-44 h-20 rounded-2xl bg-white overflow-hidden shadow-[var(--shadow-card)] mb-8">
              <img src="/logo.png" alt="OneCountry Fitness n Spa" className="w-full h-full object-cover scale-[1.35]" />
            </div>
            <h2 className="text-2xl font-semibold">Welcome back</h2>
            <p className="text-sm text-[var(--color-text-secondary)] mt-1">Sign in to your trainer account.</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input label="Email" type="email" autoComplete="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
            <Input label="Password" isPassword autoComplete="current-password" placeholder="Your password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            {error && (
              <p role="alert" className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-sm text-rose-700 dark:text-rose-300">
                {error}
              </p>
            )}
            <Button type="submit" size="lg" isLoading={isLoading} className="w-full">
              Sign in
            </Button>
          </form>

          {setup?.can_register_trainer && (
          <p className="mt-8 text-sm text-center text-[var(--color-text-secondary)]">
            New here?{' '}
            <Link to="/register-trainer" className="font-semibold text-[var(--color-accent-ink)] hover:underline">
              Create a trainer account
            </Link>
          </p>
          )}
        </div>
      </section>
    </div>
  );
};
