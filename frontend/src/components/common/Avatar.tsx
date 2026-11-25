import React, { useState } from 'react';
import { getMediaUrl } from '../../services/api';

interface AvatarProps {
  /** A media path, e.g. "/clients/5/photo". Prefer `clientId` + `photo` for client photos. */
  src?: string | null;
  /** With `photo`, loads the client's profile photo through the access-controlled endpoint. */
  clientId?: number;
  /** The client's stored photo key; changes when the photo is replaced, which busts the cache. */
  photo?: string | null;
  name: string;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

const SIZES = {
  xs: 'w-6 h-6 text-[10px]',
  sm: 'w-8 h-8 text-[11px]',
  md: 'w-10 h-10 text-xs',
  lg: 'w-14 h-14 text-base',
  xl: 'w-20 h-20 sm:w-24 sm:h-24 text-2xl',
};

/** Path of a client's profile photo, or null when they have none. */
export const clientPhotoPath = (clientId: number, photo?: string | null): string | null =>
  photo ? `/clients/${clientId}/photo?v=${encodeURIComponent(photo)}` : null;

export const Avatar: React.FC<AvatarProps> = ({ src, clientId, photo, name, size = 'md', className = '' }) => {
  const path = clientId !== undefined ? clientPhotoPath(clientId, photo) : src;
  const photoUrl = getMediaUrl(path);
  // Remember which URL failed so a new photo gets a fresh attempt.
  const [failedUrl, setFailedUrl] = useState<string | null>(null);

  const initials =
    name
      .trim()
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((n) => n[0].toUpperCase())
      .join('') || '?';

  return (
    <div
      className={`relative inline-flex items-center justify-center shrink-0 rounded-full overflow-hidden select-none ring-1 ring-[var(--color-border-strong)] bg-gradient-to-br from-[var(--color-surface-elevated)] to-[var(--color-surface-secondary)] ${SIZES[size]} ${className}`}
    >
      {photoUrl && failedUrl !== photoUrl ? (
        <img src={photoUrl} alt={name} onError={() => setFailedUrl(photoUrl)} className="w-full h-full object-cover" loading="lazy" />
      ) : (
        <span className="font-semibold tracking-wide text-[var(--color-accent-ink)]" style={{ fontFamily: 'var(--font-display)' }}>
          {initials}
        </span>
      )}
    </div>
  );
};
