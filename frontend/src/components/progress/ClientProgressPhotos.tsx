import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowRight,
  Camera,
  CheckCircle2,
  Columns2,
  ImagePlus,
  SplitSquareHorizontal,
  Trash2,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';
import { getApiErrorMessage, getMediaUrl, progressPhotoService } from '../../services/api';
import { formatDate, todayIso } from '../../utils/format';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { EmptyState } from '../common/EmptyState';
import { Input } from '../common/Input';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { Modal } from '../common/Modal';
import { useFeedback } from '../../context/FeedbackContext';
import type { PhotoPose, ProgressPhoto } from '../../types';

const POSES: { value: PhotoPose; label: string }[] = [
  { value: 'FRONT', label: 'Front' },
  { value: 'SIDE', label: 'Side' },
  { value: 'BACK', label: 'Back' },
  { value: 'OTHER', label: 'Other' },
];
const poseLabel = (p: string) => POSES.find((x) => x.value === p)?.label ?? p;
const MAX_MB = 10;

// ---------- date helpers (YYYY-MM-DD strings, local calendar) ----------
const parseIso = (iso: string) => {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(y, m - 1, d);
};
const toIso = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
const mondayOf = (iso: string) => {
  const d = parseIso(iso);
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
  return toIso(d);
};
const addDays = (iso: string, n: number) => {
  const d = parseIso(iso);
  d.setDate(d.getDate() + n);
  return toIso(d);
};
const daysBetween = (a: string, b: string) => Math.round((parseIso(b).getTime() - parseIso(a).getTime()) / 86_400_000);
/** "16 – 22 Nov 2026", "26 Oct – 1 Nov 2026" or "29 Dec 2025 – 4 Jan 2026". */
const shortRange = (monday: string) => {
  const start = formatDate(monday);
  const end = formatDate(addDays(monday, 6));
  const [sd, sm, sy] = start.split(' ');
  const [, em, ey] = end.split(' ');
  if (sy !== ey) return `${start} – ${end}`;
  if (sm !== em) return `${sd} ${sm} – ${end}`;
  return `${sd} – ${end}`;
};

const kg = (n: number) => `${Number.isInteger(n) ? n : n.toFixed(1)} kg`;

const WeightChange: React.FC<{ from?: number | null; to?: number | null }> = ({ from, to }) => {
  if (from == null || to == null) return null;
  const diff = Math.round((to - from) * 10) / 10;
  if (diff === 0) return <span className="text-[var(--color-text-secondary)]">No weight change</span>;
  const down = diff < 0;
  const Icon = down ? TrendingDown : TrendingUp;
  return (
    <span className="inline-flex items-center gap-1 font-semibold text-[var(--color-primary)]">
      <Icon className="w-4 h-4" />
      {down ? '' : '+'}
      {kg(diff)}
    </span>
  );
};

// ---------- Before/after comparison ----------
const CompareView: React.FC<{ before: ProgressPhoto; after: ProgressPhoto }> = ({ before, after }) => {
  const [mode, setMode] = useState<'slider' | 'side'>('slider');
  const [pos, setPos] = useState(50);
  const beforeUrl = getMediaUrl(before.image_url) ?? '';
  const afterUrl = getMediaUrl(after.image_url) ?? '';
  const days = daysBetween(before.photo_date, after.photo_date);
  const weeks = Math.round(days / 7);

  const label = (text: string, side: 'left' | 'right') => (
    <span
      className={`absolute top-3 ${side === 'left' ? 'left-3' : 'right-3'} z-10 text-[11px] font-bold uppercase tracking-wider px-2 py-1 rounded-md bg-black/60 text-white backdrop-blur-sm`}
    >
      {text}
    </span>
  );

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-[var(--color-text-secondary)]">
          {formatDate(before.photo_date)} <ArrowRight className="inline w-3.5 h-3.5 mx-1" /> {formatDate(after.photo_date)}
          <span className="mx-2">·</span>
          {weeks >= 1 ? `${weeks} week${weeks === 1 ? '' : 's'}` : `${days} day${days === 1 ? '' : 's'}`}
          {before.weight != null && after.weight != null && (
            <>
              <span className="mx-2">·</span>
              <WeightChange from={before.weight} to={after.weight} />
            </>
          )}
        </p>
        <div className="inline-flex rounded-lg border border-[var(--color-border)] p-0.5 bg-[var(--color-surface-secondary)]" role="tablist">
          {(
            [
              ['slider', 'Slider', SplitSquareHorizontal],
              ['side', 'Side by side', Columns2],
            ] as const
          ).map(([key, text, Icon]) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={mode === key}
              onClick={() => setMode(key)}
              className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1.5 rounded-md transition-colors cursor-pointer ${
                mode === key
                  ? 'bg-[var(--color-primary)] text-[var(--color-primary-text)]'
                  : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {text}
            </button>
          ))}
        </div>
      </div>

      {mode === 'slider' ? (
        <div className="relative mx-auto w-full max-w-md aspect-[3/4] rounded-xl overflow-hidden bg-black select-none border border-[var(--color-border)]">
          <img src={beforeUrl} alt={`Before, ${formatDate(before.photo_date)}`} className="absolute inset-0 w-full h-full object-contain" draggable={false} />
          <img
            src={afterUrl}
            alt={`After, ${formatDate(after.photo_date)}`}
            className="absolute inset-0 w-full h-full object-contain bg-black"
            style={{ clipPath: `inset(0 0 0 ${pos}%)` }}
            draggable={false}
          />
          {label('Before', 'left')}
          {label('After', 'right')}
          {/* Divider and handle */}
          <div className="absolute inset-y-0 z-10 pointer-events-none" style={{ left: `${pos}%` }}>
            <div className="absolute inset-y-0 -translate-x-1/2 w-0.5 bg-white/90 shadow-[0_0_12px_rgba(var(--color-primary-rgb),0.9)]" />
            <div className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 w-9 h-9 rounded-full bg-[var(--color-primary)] text-[var(--color-primary-text)] flex items-center justify-center shadow-lg">
              <SplitSquareHorizontal className="w-4 h-4" />
            </div>
          </div>
          <input
            type="range"
            min={0}
            max={100}
            value={pos}
            onChange={(e) => setPos(Number(e.target.value))}
            aria-label="Drag to compare before and after"
            className="absolute inset-0 z-20 w-full h-full opacity-0 cursor-ew-resize"
          />
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          {[
            ['Before', before, beforeUrl],
            ['After', after, afterUrl],
          ].map(([text, p, url]) => {
            const photo = p as ProgressPhoto;
            return (
              <figure key={text as string} className="relative aspect-[3/4] rounded-xl overflow-hidden bg-black border border-[var(--color-border)]">
                <img src={url as string} alt={`${text}, ${formatDate(photo.photo_date)}`} className="w-full h-full object-contain" />
                {label(text as string, 'left')}
                <figcaption className="absolute bottom-0 inset-x-0 p-2.5 text-xs text-white bg-gradient-to-t from-black/80 to-transparent">
                  {formatDate(photo.photo_date)}
                  {photo.weight != null && ` · ${kg(photo.weight)}`}
                </figcaption>
              </figure>
            );
          })}
        </div>
      )}
    </div>
  );
};

// ---------- Upload ----------
const UploadPhotoModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  clientId: number;
  defaultWeight?: number | null;
  onSaved: (photo: ProgressPhoto) => void;
}> = ({ isOpen, onClose, clientId, defaultWeight, onSaved }) => {
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [photoDate, setPhotoDate] = useState(todayIso());
  const [pose, setPose] = useState<PhotoPose>('FRONT');
  const [weight, setWeight] = useState(defaultWeight != null ? String(defaultWeight) : '');
  const [notes, setNotes] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  const reset = () => {
    setFile(null);
    setPreview(null);
    setPhotoDate(todayIso());
    setPose('FRONT');
    setWeight(defaultWeight != null ? String(defaultWeight) : '');
    setNotes('');
    setError(null);
  };

  const close = () => {
    reset();
    onClose();
  };

  const pick = (f: File | undefined) => {
    if (!f) return;
    if (!f.type.startsWith('image/')) return setError('Choose an image file (JPEG, PNG or WebP).');
    if (f.size > MAX_MB * 1024 * 1024) return setError(`Photos must be under ${MAX_MB} MB.`);
    setError(null);
    setFile(f);
    setPreview(URL.createObjectURL(f));
  };

  const mutation = useMutation({
    mutationFn: progressPhotoService.upload,
    onSuccess: (photo) => {
      onSaved(photo);
      close();
    },
    onError: (e) => setError(getApiErrorMessage(e, 'Could not upload the photo.')),
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return setError('Add a photo first.');
    const w = weight.trim() ? Number(weight) : undefined;
    if (w !== undefined && (!Number.isFinite(w) || w <= 0 || w > 500)) return setError('Enter a valid weight in kg.');
    mutation.mutate({ client_id: clientId, photo_date: photoDate, category: pose, weight: w, notes: notes.trim() || undefined, file });
  };

  return (
    <Modal isOpen={isOpen} onClose={close} title="Add progress photo" description="Use the same pose, spot and lighting each week for a fair comparison." maxWidth="lg">
      <form onSubmit={submit} className="space-y-4">
        <input
          ref={fileRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={(e) => pick(e.target.files?.[0])}
        />
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            pick(e.dataTransfer.files?.[0]);
          }}
          className={`group relative w-full rounded-xl border-2 border-dashed transition-colors cursor-pointer overflow-hidden ${
            preview
              ? 'border-transparent'
              : 'border-[var(--color-input-border)] hover:border-[var(--color-primary)] bg-[var(--color-surface-secondary)]'
          }`}
          aria-label={preview ? 'Change photo' : 'Take or choose a photo'}
        >
          {preview ? (
            <div className="relative aspect-[3/4] max-h-[42vh] mx-auto bg-black">
              <img src={preview} alt="Selected photo preview" className="w-full h-full object-contain" />
              <span className="absolute bottom-2 left-1/2 -translate-x-1/2 text-xs font-semibold px-3 py-1.5 rounded-full bg-black/70 text-white">
                Tap to change
              </span>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center gap-2 py-10 px-4 text-center">
              <span className="w-12 h-12 rounded-full flex items-center justify-center bg-[rgba(var(--color-primary-rgb),0.12)] text-[var(--color-primary)] transition-transform group-hover:scale-110">
                <Camera className="w-6 h-6" />
              </span>
              <span className="text-sm font-semibold text-[var(--color-text)]">Take or choose a photo</span>
              <span className="text-xs text-[var(--color-text-secondary)]">JPEG, PNG or WebP, up to {MAX_MB} MB. You can also drop a file here.</span>
            </div>
          )}
        </button>

        <div>
          <span className="block text-sm font-medium text-[var(--color-text)] mb-1.5">Pose</span>
          <div className="grid grid-cols-4 gap-2" role="radiogroup" aria-label="Pose">
            {POSES.map((p) => (
              <button
                key={p.value}
                type="button"
                role="radio"
                aria-checked={pose === p.value}
                onClick={() => setPose(p.value)}
                className={`text-sm font-semibold py-2 rounded-lg border transition-colors cursor-pointer ${
                  pose === p.value
                    ? 'bg-[var(--color-primary)] border-[var(--color-primary)] text-[var(--color-primary-text)]'
                    : 'border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-text)] hover:border-[var(--color-primary)]'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Input label="Date" type="date" required max={todayIso()} value={photoDate} onChange={(e) => setPhotoDate(e.target.value)} />
          <Input label="Weight (kg)" type="number" step="0.1" min="1" inputMode="decimal" placeholder="Optional" value={weight} onChange={(e) => setWeight(e.target.value)} />
        </div>
        <Input label="Note" placeholder="Optional, e.g. after 4 weeks of cardio" value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={1000} />

        {error && <p className="text-sm text-rose-600 dark:text-rose-400" role="alert">{error}</p>}

        <div className="flex justify-end gap-3 pt-3 border-t border-[var(--color-border)]">
          <Button type="button" variant="outline" onClick={close}>Cancel</Button>
          <Button type="submit" isLoading={mutation.isPending} leftIcon={<ImagePlus className="w-4 h-4" />}>Save photo</Button>
        </div>
      </form>
    </Modal>
  );
};

// ---------- Main section ----------
export const ClientProgressPhotos: React.FC<{ clientId: number; clientName: string; currentWeight?: number | null }> = ({
  clientId,
  clientName,
  currentWeight,
}) => {
  const qc = useQueryClient();
  const { confirm } = useFeedback();
  const [uploadOpen, setUploadOpen] = useState(false);
  const [viewing, setViewing] = useState<ProgressPhoto | null>(null);
  const [poseFilter, setPoseFilter] = useState<PhotoPose | 'ALL'>('ALL');
  const [beforeId, setBeforeId] = useState<number | null>(null);
  const [afterId, setAfterId] = useState<number | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const { data: photos = [], isLoading, isError, refetch } = useQuery({
    queryKey: ['progress-photos', clientId],
    queryFn: () => progressPhotoService.list(clientId),
  });

  const deleteMutation = useMutation({
    mutationFn: progressPhotoService.remove,
    onSuccess: () => {
      setViewing(null);
      qc.invalidateQueries({ queryKey: ['progress-photos', clientId] });
      setNotice('Photo deleted.');
    },
    onError: (e) => setNotice(getApiErrorMessage(e, 'Could not delete the photo.')),
  });

  const thisWeek = mondayOf(todayIso());
  const takenThisWeek = photos.filter((p) => p.week_start === thisWeek);
  const filtered = poseFilter === 'ALL' ? photos : photos.filter((p) => p.category === poseFilter);

  // Default comparison: oldest vs newest photo of the selected pose (or of the most used pose).
  const comparePool = useMemo(() => {
    if (poseFilter !== 'ALL') return filtered;
    const counts = new Map<string, number>();
    photos.forEach((p) => counts.set(p.category, (counts.get(p.category) ?? 0) + 1));
    const top = [...counts.entries()].sort((a, b) => b[1] - a[1])[0]?.[0];
    return photos.filter((p) => p.category === top);
  }, [photos, filtered, poseFilter]);
  const byId = new Map(photos.map((p) => [p.id, p]));
  const before = (beforeId != null && byId.get(beforeId)) || comparePool[comparePool.length - 1];
  const after = (afterId != null && byId.get(afterId)) || comparePool[0];
  const canCompare = before && after && before.id !== after.id;

  const firstWeek = photos.length ? photos[photos.length - 1].week_start : thisWeek;
  const weekNumber = (monday: string) => Math.round(daysBetween(firstWeek, monday) / 7) + 1;

  // Every week from the first photo to this week, newest first, so missed weeks show as gaps.
  const weeks = useMemo(() => {
    const byWeek = new Map<string, ProgressPhoto[]>();
    filtered.forEach((p) => {
      if (!byWeek.has(p.week_start)) byWeek.set(p.week_start, []);
      byWeek.get(p.week_start)!.push(p);
    });
    const out: [string, ProgressPhoto[]][] = [];
    for (let monday = thisWeek; monday >= firstWeek; monday = addDays(monday, -7)) {
      out.push([monday, byWeek.get(monday) ?? []]);
    }
    return out;
  }, [filtered, thisWeek, firstWeek]);

  const weighed = photos.filter((p) => p.weight != null);
  const firstWeighed = weighed[weighed.length - 1];
  const lastWeighed = weighed[0];

  if (isLoading) return <LoadingSpinner message="Loading progress photos..." />;
  if (isError) return <EmptyState title="Could not load progress photos" actionLabel="Try again" onAction={() => refetch()} />;

  return (
    <div className="space-y-4">
      {notice && (
        <div role="status" className="text-sm px-3 py-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-elevated)] flex justify-between gap-2">
          <span>{notice}</span>
          <button className="text-[var(--color-text-secondary)] hover:text-[var(--color-text)] cursor-pointer" onClick={() => setNotice(null)} aria-label="Dismiss">✕</button>
        </div>
      )}

      {/* This week + summary */}
      <Card className="flex flex-col md:flex-row md:items-center gap-4 justify-between">
        <div className="flex items-start gap-3">
          <span
            className={`mt-0.5 w-10 h-10 shrink-0 rounded-full flex items-center justify-center ${
              takenThisWeek.length
                ? 'bg-[rgba(var(--color-primary-rgb),0.15)] text-[var(--color-primary)]'
                : 'bg-amber-500/15 text-amber-600 dark:text-amber-300'
            }`}
          >
            {takenThisWeek.length ? <CheckCircle2 className="w-5 h-5" /> : <Camera className="w-5 h-5" />}
          </span>
          <div>
            <p className="font-semibold text-[var(--color-text)]">
              {takenThisWeek.length
                ? `This week's photo is done (${takenThisWeek.map((p) => poseLabel(p.category)).join(', ')})`
                : "This week's photo hasn't been taken yet"}
            </p>
            <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
              Week of {shortRange(thisWeek)}
              {photos.length > 0 && (
                <>
                  {' · '}
                  {photos.length} photo{photos.length === 1 ? '' : 's'} over {weekNumber(thisWeek)} week{weekNumber(thisWeek) === 1 ? '' : 's'}
                </>
              )}
              {firstWeighed && lastWeighed && firstWeighed.id !== lastWeighed.id && (
                <>
                  {' · '}
                  {kg(firstWeighed.weight!)} → {kg(lastWeighed.weight!)}{' '}
                  <WeightChange from={firstWeighed.weight} to={lastWeighed.weight} />
                </>
              )}
            </p>
          </div>
        </div>
        <Button leftIcon={<Camera className="w-4 h-4" />} onClick={() => setUploadOpen(true)} className="shrink-0">
          {takenThisWeek.length ? 'Add another photo' : "Add this week's photo"}
        </Button>
      </Card>

      {photos.length === 0 ? (
        <EmptyState
          icon={<Camera className="w-10 h-10 text-[var(--color-primary)]" />}
          title={`No progress photos for ${clientName} yet`}
          description="Take a photo every week in the same pose and spot. You'll be able to compare any two weeks side by side."
          actionLabel="Add the first photo"
          onAction={() => setUploadOpen(true)}
        />
      ) : (
        <>
          {/* Pose filter */}
          <div className="flex flex-wrap gap-2" role="tablist" aria-label="Filter by pose">
            {([{ value: 'ALL', label: 'All poses' }, ...POSES] as { value: PhotoPose | 'ALL'; label: string }[]).map((p) => {
              const count = p.value === 'ALL' ? photos.length : photos.filter((x) => x.category === p.value).length;
              if (p.value !== 'ALL' && count === 0) return null;
              const on = poseFilter === p.value;
              return (
                <button
                  key={p.value}
                  role="tab"
                  aria-selected={on}
                  onClick={() => {
                    setPoseFilter(p.value);
                    setBeforeId(null);
                    setAfterId(null);
                  }}
                  className={`text-xs font-semibold px-3 py-1.5 rounded-full border transition-colors cursor-pointer ${
                    on
                      ? 'bg-[var(--color-primary)] border-[var(--color-primary)] text-[var(--color-primary-text)]'
                      : 'border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'
                  }`}
                >
                  {p.label} <span className="opacity-70">{count}</span>
                </button>
              );
            })}
          </div>

          {/* Compare */}
          <Card className="space-y-3">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <h3 className="font-semibold text-[var(--color-text)]">Compare</h3>
                <p className="text-xs text-[var(--color-text-secondary)]">Pick any two photos. Defaults to the first and latest.</p>
              </div>
              {canCompare && (
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  {(
                    [
                      ['Before', before, setBeforeId],
                      ['After', after, setAfterId],
                    ] as const
                  ).map(([text, current, setter]) => (
                    <label key={text} className="flex items-center gap-1.5 text-[var(--color-text-secondary)]">
                      {text}
                      <select
                        value={current.id}
                        onChange={(e) => setter(Number(e.target.value))}
                        className="bg-[var(--color-input)] border border-[var(--color-input-border)] rounded-lg px-2 py-1.5 text-[var(--color-text)] focus:outline-none focus:border-[var(--color-input-focus)]"
                      >
                        {[...filtered].reverse().map((p) => (
                          <option key={p.id} value={p.id}>
                            {formatDate(p.photo_date)} · {poseLabel(p.category)}
                          </option>
                        ))}
                      </select>
                    </label>
                  ))}
                </div>
              )}
            </div>
            {canCompare ? (
              <CompareView key={`${before.id}-${after.id}`} before={before} after={after} />
            ) : (
              <p className="text-sm text-[var(--color-text-secondary)] py-4 text-center">
                Add one more {poseFilter === 'ALL' ? '' : `${poseLabel(poseFilter).toLowerCase()} `}photo to start comparing.
              </p>
            )}
          </Card>

          {/* Weekly timeline: one tile per photo, dashed tiles for missed weeks */}
          <Card className="space-y-3">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="font-semibold text-[var(--color-text)]">Week by week</h3>
              <p className="text-xs text-[var(--color-text-secondary)]">
                {weeks.filter(([, l]) => l.length > 0).length} of {weeks.length} weeks photographed
              </p>
            </div>
            <div className="fx-stagger grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
              {weeks.flatMap(([monday, list]) => {
                const head = (
                  <span className="block text-[11px] font-bold uppercase tracking-wider">
                    Week {weekNumber(monday)}
                    {monday === thisWeek && <span className="ml-1 normal-case tracking-normal font-semibold text-[var(--color-primary)]">· now</span>}
                  </span>
                );
                if (list.length === 0) {
                  const isNow = monday === thisWeek;
                  return [
                    <button
                      key={monday}
                      type="button"
                      disabled={!isNow}
                      onClick={() => setUploadOpen(true)}
                      className={`aspect-[3/4] rounded-xl border-2 border-dashed border-[var(--color-border)] flex flex-col items-center justify-center gap-1.5 p-2 text-center text-[var(--color-text-muted)] ${
                        isNow ? 'cursor-pointer hover:border-[var(--color-primary)] hover:text-[var(--color-primary)] transition-colors' : 'cursor-default'
                      }`}
                      aria-label={isNow ? "Add this week's photo" : `Week ${weekNumber(monday)}: no photo`}
                    >
                      {head}
                      {isNow ? <Camera className="w-5 h-5" /> : null}
                      <span className="text-xs">{isNow ? 'Add photo' : 'No photo'}</span>
                      <span className="text-[10px]">{shortRange(monday)}</span>
                    </button>,
                  ];
                }
                return list.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => setViewing(p)}
                    className="group relative aspect-[3/4] rounded-xl overflow-hidden bg-black border border-[var(--color-border)] cursor-pointer transition-all duration-300 hover:border-[rgba(var(--color-primary-rgb),0.6)] hover:-translate-y-0.5 hover:shadow-[0_10px_30px_-10px_rgba(var(--color-primary-rgb),0.5)]"
                    aria-label={`Week ${weekNumber(monday)}, ${poseLabel(p.category)} photo, ${formatDate(p.photo_date)}`}
                  >
                    <img
                      src={getMediaUrl(p.image_url) ?? ''}
                      alt=""
                      loading="lazy"
                      className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                    />
                    <span className="absolute top-0 inset-x-0 p-2 text-left text-white bg-gradient-to-b from-black/70 to-transparent">
                      {head}
                    </span>
                    <span className="absolute bottom-0 inset-x-0 p-2 text-left text-xs text-white bg-gradient-to-t from-black/85 via-black/40 to-transparent">
                      <span className="block font-semibold">{formatDate(p.photo_date)}</span>
                      <span className="opacity-80">
                        {poseLabel(p.category)}
                        {p.weight != null && ` · ${kg(p.weight)}`}
                      </span>
                    </span>
                  </button>
                ));
              })}
            </div>
          </Card>
        </>
      )}

      <UploadPhotoModal
        isOpen={uploadOpen}
        onClose={() => setUploadOpen(false)}
        clientId={clientId}
        defaultWeight={currentWeight}
        onSaved={(photo) => {
          qc.invalidateQueries({ queryKey: ['progress-photos', clientId] });
          qc.invalidateQueries({ queryKey: ['client', clientId] });
          setNotice(`Photo for ${formatDate(photo.photo_date)} saved.`);
        }}
      />

      {/* Full-size viewer */}
      <Modal
        isOpen={!!viewing}
        onClose={() => setViewing(null)}
        title={viewing ? `${poseLabel(viewing.category)} · ${formatDate(viewing.photo_date)}` : ''}
        description={viewing ? `Week ${weekNumber(viewing.week_start)}${viewing.weight != null ? ` · ${kg(viewing.weight)}` : ''}` : undefined}
        maxWidth="lg"
      >
        {viewing && (
          <div className="space-y-3">
            <div className="rounded-xl overflow-hidden bg-black">
              <img src={getMediaUrl(viewing.image_url) ?? ''} alt={`${poseLabel(viewing.category)} photo, ${formatDate(viewing.photo_date)}`} className="w-full max-h-[60vh] object-contain" />
            </div>
            {viewing.notes && <p className="text-sm text-[var(--color-text-secondary)]">{viewing.notes}</p>}
            <div className="flex flex-wrap justify-between gap-2 pt-2 border-t border-[var(--color-border)]">
              <Button
                variant="ghost"
                size="sm"
                leftIcon={<Trash2 className="w-4 h-4" />}
                className="text-rose-600 dark:text-rose-400"
                isLoading={deleteMutation.isPending}
                onClick={async () => {
                  if (await confirm({ title: 'Delete this photo?', message: 'This cannot be undone.', confirmLabel: 'Delete', danger: true })) {
                    deleteMutation.mutate(viewing.id);
                  }
                }}
              >
                Delete
              </Button>
              <div className="flex gap-2">
                <Button variant="secondary" size="sm" onClick={() => { setPoseFilter('ALL'); setBeforeId(viewing.id); setViewing(null); }}>
                  Compare as before
                </Button>
                <Button size="sm" onClick={() => { setPoseFilter('ALL'); setAfterId(viewing.id); setViewing(null); }}>
                  Compare as after
                </Button>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};
