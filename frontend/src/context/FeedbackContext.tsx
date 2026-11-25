import React, { createContext, useCallback, useContext, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { AlertTriangle, CheckCircle2, Info, X, XCircle } from 'lucide-react';
import { Modal } from '../components/common/Modal';
import { Button } from '../components/common/Button';

type ToastKind = 'success' | 'error' | 'info';

interface Toast {
  id: number;
  kind: ToastKind;
  text: string;
}

interface ConfirmOptions {
  title: string;
  message?: React.ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  /** Red confirm button for destructive actions. */
  danger?: boolean;
}

interface FeedbackContextType {
  toast: (text: string, kind?: ToastKind) => void;
  /** Resolves true when the person confirms. */
  confirm: (options: ConfirmOptions) => Promise<boolean>;
}

const FeedbackContext = createContext<FeedbackContextType | undefined>(undefined);

const TOAST_STYLE: Record<ToastKind, { icon: React.ReactNode; ring: string }> = {
  success: { icon: <CheckCircle2 className="w-5 h-5 text-[var(--color-primary)]" />, ring: 'border-[rgba(var(--color-primary-rgb),0.35)]' },
  error: { icon: <XCircle className="w-5 h-5 text-rose-500" />, ring: 'border-rose-500/40' },
  info: { icon: <Info className="w-5 h-5 text-sky-500" />, ring: 'border-sky-500/35' },
};

export const FeedbackProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(1);
  const [pending, setPending] = useState<(ConfirmOptions & { resolve: (ok: boolean) => void }) | null>(null);

  const dismiss = useCallback((id: number) => setToasts((all) => all.filter((t) => t.id !== id)), []);

  const toast = useCallback(
    (text: string, kind: ToastKind = 'success') => {
      const id = nextId.current++;
      setToasts((all) => [...all.slice(-2), { id, kind, text }]);
      window.setTimeout(() => dismiss(id), kind === 'error' ? 6000 : 3500);
    },
    [dismiss],
  );

  const confirm = useCallback(
    (options: ConfirmOptions) => new Promise<boolean>((resolve) => setPending({ ...options, resolve })),
    [],
  );

  const settle = (ok: boolean) => {
    pending?.resolve(ok);
    setPending(null);
  };

  return (
    <FeedbackContext.Provider value={{ toast, confirm }}>
      {children}

      {createPortal(
        <div
          aria-live="polite"
          className="fixed z-[70] left-3 right-3 bottom-[5.5rem] lg:bottom-6 lg:left-auto lg:right-6 lg:w-96 flex flex-col gap-2 pointer-events-none"
        >
          {toasts.map((t) => (
            <div
              key={t.id}
              role={t.kind === 'error' ? 'alert' : 'status'}
              className={`fx-dialog pointer-events-auto flex items-start gap-3 p-3.5 rounded-2xl border bg-[var(--color-surface-elevated)] shadow-[var(--shadow-dropdown)] ${TOAST_STYLE[t.kind].ring}`}
            >
              <span className="shrink-0 mt-px">{TOAST_STYLE[t.kind].icon}</span>
              <p className="flex-1 text-sm text-[var(--color-text)] leading-snug">{t.text}</p>
              <button
                type="button"
                onClick={() => dismiss(t.id)}
                className="shrink-0 p-0.5 rounded text-[var(--color-text-muted)] hover:text-[var(--color-text)] cursor-pointer"
                aria-label="Dismiss"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>,
        document.body,
      )}

      <Modal
        isOpen={!!pending}
        onClose={() => settle(false)}
        title={pending?.title ?? ''}
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => settle(false)}>
              {pending?.cancelLabel ?? 'Cancel'}
            </Button>
            <Button variant={pending?.danger ? 'danger' : 'primary'} onClick={() => settle(true)} autoFocus>
              {pending?.confirmLabel ?? 'Confirm'}
            </Button>
          </>
        }
      >
        {pending?.message && (
          <div className="flex gap-3 text-sm text-[var(--color-text-secondary)]">
            {pending.danger && <AlertTriangle className="w-5 h-5 shrink-0 text-rose-500" />}
            <div>{pending.message}</div>
          </div>
        )}
      </Modal>
    </FeedbackContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useFeedback = (): FeedbackContextType => {
  const ctx = useContext(FeedbackContext);
  if (!ctx) throw new Error('useFeedback must be used within a FeedbackProvider');
  return ctx;
};
