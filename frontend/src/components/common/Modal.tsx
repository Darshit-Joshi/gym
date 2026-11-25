import React, { useEffect, useId } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: React.ReactNode;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl';
  size?: 'sm' | 'md' | 'lg' | 'xl' | '2xl';
  /** Sticky action row at the bottom of the dialog. */
  footer?: React.ReactNode;
}

const WIDTHS = {
  sm: 'sm:max-w-sm',
  md: 'sm:max-w-md',
  lg: 'sm:max-w-lg',
  xl: 'sm:max-w-xl',
  '2xl': 'sm:max-w-2xl',
};

/**
 * Centered dialog on wider screens; a bottom sheet on phones so actions stay under the thumb.
 * Rendered into <body> so transformed ancestors can't clip it.
 */
export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, description, children, maxWidth, size = 'md', footer }) => {
  const titleId = useId();

  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = previous;
      window.removeEventListener('keydown', onKey);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      className="fx-backdrop fixed inset-0 z-[60] flex items-end sm:items-center justify-center sm:p-4 bg-black/70 backdrop-blur-[2px]"
    >
      <div className="fixed inset-0" onClick={onClose} aria-hidden="true" />
      <div
        className={`fx-dialog relative z-10 w-full ${WIDTHS[maxWidth || size]} max-h-[92vh] sm:max-h-[88vh] flex flex-col bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text)] rounded-t-3xl sm:rounded-2xl shadow-[var(--shadow-dropdown)]`}
      >
        <div className="sm:hidden mx-auto mt-2.5 h-1 w-10 rounded-full bg-[var(--color-border-strong)]" aria-hidden="true" />
        <div className="flex items-start justify-between gap-4 px-5 sm:px-6 pt-4 sm:pt-5 pb-3">
          <div className="min-w-0">
            <h2 id={titleId} className="text-lg font-semibold text-[var(--color-text)]">
              {title}
            </h2>
            {description && <p className="text-sm text-[var(--color-text-secondary)] mt-0.5">{description}</p>}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 -mr-1.5 p-2 rounded-lg text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-hover)] transition-colors cursor-pointer"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="px-5 sm:px-6 pb-5 sm:pb-6 overflow-y-auto">{children}</div>
        {footer && (
          <div className="px-5 sm:px-6 py-3.5 border-t border-[var(--color-border)] flex justify-end gap-2 pb-safe">{footer}</div>
        )}
      </div>
    </div>,
    document.body,
  );
};
