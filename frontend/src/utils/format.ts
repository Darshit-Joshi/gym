const MONTHS_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export const formatMoney = (amount: number | null | undefined, currency = 'INR'): string => {
  const value = amount ?? 0;
  try {
    return new Intl.NumberFormat(currency === 'INR' ? 'en-IN' : undefined, {
      style: 'currency',
      currency,
      minimumFractionDigits: Number.isInteger(value) ? 0 : 2,
      maximumFractionDigits: 2,
    }).format(value);
  } catch {
    return `${currency} ${value.toFixed(2)}`;
  }
};

/** Formats an ISO date (YYYY-MM-DD) without timezone shifts, e.g. "21 Nov 2026". */
export const formatDate = (iso: string | null | undefined): string => {
  if (!iso) return '—';
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number);
  if (!y || !m || !d) return iso;
  return `${d} ${MONTHS_SHORT[m - 1]} ${y}`;
};

export const formatRelativeTime = (isoDateTime: string): string => {
  const diffSec = Math.round((Date.now() - new Date(isoDateTime).getTime()) / 1000);
  if (diffSec < 60) return 'just now';
  const mins = Math.floor(diffSec / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(isoDateTime).toLocaleDateString();
};

/** Local (not UTC) date as YYYY-MM-DD. */
export const todayIso = (): string => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
};

export const currentMonth = (): string => todayIso().slice(0, 7);

/** Parses YYYY-MM-DD as a local date (no UTC shift). */
export const parseIso = (iso: string): Date => {
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number);
  return new Date(y, m - 1, d);
};

const toIso = (d: Date): string =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

/** Adds days to a YYYY-MM-DD date, staying in local time. */
export const addDays = (iso: string, days: number): string => {
  const d = parseIso(iso);
  d.setDate(d.getDate() + days);
  return toIso(d);
};

/** "Today", "Yesterday", or e.g. "Mon, 21 Nov". */
export const relativeDay = (iso: string): string => {
  const today = todayIso();
  if (iso === today) return 'Today';
  if (iso === addDays(today, -1)) return 'Yesterday';
  return parseIso(iso).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' });
};

/** e.g. "Monday, 24 November". */
export const longDay = (iso: string): string =>
  parseIso(iso).toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' });

/** Short weekday letter-pair for charts, e.g. "Mo". */
export const weekdayShort = (iso: string): string =>
  parseIso(iso).toLocaleDateString(undefined, { weekday: 'short' });

/** Greeting for the time of day. */
export const greeting = (hour: number): string => (hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening');

export const shiftMonth = (month: string, delta: number): string => {
  const [y, m] = month.split('-').map(Number);
  const idx = y * 12 + (m - 1) + delta;
  return `${Math.floor(idx / 12)}-${String((idx % 12) + 1).padStart(2, '0')}`;
};

export const monthLabel = (month: string): string => {
  const [y, m] = month.split('-').map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
};

export const cycleLabel = (months?: number | null): string => {
  if (!months) return '—';
  if (months === 1) return 'Monthly';
  if (months === 3) return 'Quarterly';
  if (months === 6) return 'Half-yearly';
  if (months === 12) return 'Yearly';
  return `Every ${months} months`;
};
