import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingSpinnerProps {
  message?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ message = 'Loading...', size = 'md' }) => {
  const sizeMap = { sm: 'w-5 h-5', md: 'w-7 h-7', lg: 'w-10 h-10' };
  return (
    <div role="status" className="flex flex-col items-center justify-center py-12 px-4 gap-3">
      <Loader2 className={`${sizeMap[size]} text-[var(--color-primary)] animate-spin`} />
      {message && <p className="text-sm text-[var(--color-text-secondary)]">{message}</p>}
    </div>
  );
};

/** Placeholder block shown while content loads. */
export const Skeleton: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`fx-shimmer rounded-lg ${className}`} aria-hidden="true" />
);

/** A stack of skeleton rows, used in place of lists while they load. */
export const SkeletonList: React.FC<{ rows?: number; className?: string }> = ({ rows = 5, className = '' }) => (
  <div role="status" aria-label="Loading" className={`space-y-2.5 ${className}`}>
    {Array.from({ length: rows }).map((_, i) => (
      <div key={i} className="panel p-4 flex items-center gap-3">
        <Skeleton className="w-10 h-10 rounded-full shrink-0" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-3.5 w-2/5" />
          <Skeleton className="h-3 w-1/4" />
        </div>
        <Skeleton className="h-8 w-24 hidden sm:block" />
      </div>
    ))}
  </div>
);
