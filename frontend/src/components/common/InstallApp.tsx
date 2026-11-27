import React, { useState } from 'react';
import { Download, Share, SquarePlus, X } from 'lucide-react';
import { Modal } from './Modal';
import { Button } from './Button';
import { useInstallPrompt } from '../../utils/installPrompt';

/** iPhone / iPad: there is no install dialog, so show the Add to Home Screen steps. */
export const IosInstallHelp: React.FC<{ isOpen: boolean; onClose: () => void }> = ({ isOpen, onClose }) => (
  <Modal
    isOpen={isOpen}
    onClose={onClose}
    title="Add to your home screen"
    description="OneCountry then opens like an app: full screen, no browser bars."
    size="sm"
    footer={<Button onClick={onClose}>Got it</Button>}
  >
    <ol className="space-y-3 text-sm">
      <li className="flex items-center gap-3">
        <span className="num w-7 h-7 shrink-0 rounded-full bg-[var(--color-accent-soft)] text-[var(--color-accent-ink)] flex items-center justify-center font-semibold">1</span>
        <span>
          Tap <Share className="inline w-4 h-4 -mt-1 mx-0.5" aria-label="Share" /> <strong>Share</strong> in Safari's toolbar.
        </span>
      </li>
      <li className="flex items-center gap-3">
        <span className="num w-7 h-7 shrink-0 rounded-full bg-[var(--color-accent-soft)] text-[var(--color-accent-ink)] flex items-center justify-center font-semibold">2</span>
        <span>
          Scroll down and tap <SquarePlus className="inline w-4 h-4 -mt-1 mx-0.5" aria-hidden="true" /> <strong>Add to Home Screen</strong>.
        </span>
      </li>
      <li className="flex items-center gap-3">
        <span className="num w-7 h-7 shrink-0 rounded-full bg-[var(--color-accent-soft)] text-[var(--color-accent-ink)] flex items-center justify-center font-semibold">3</span>
        <span>
          Tap <strong>Add</strong>, then open OneCountry from your home screen.
        </span>
      </li>
    </ol>
  </Modal>
);

const DISMISS_KEY = 'gym_install_banner_dismissed';

/** A one-line "Install the app" banner for phones. Hidden once installed or dismissed. */
export const InstallBanner: React.FC = () => {
  const { available, iosManual, promptInstall } = useInstallPrompt();
  const [iosHelp, setIosHelp] = useState(false);
  const [dismissed, setDismissed] = useState(() => {
    try {
      return localStorage.getItem(DISMISS_KEY) === '1';
    } catch {
      return false;
    }
  });

  if (!available || dismissed) return null;

  const dismiss = () => {
    setDismissed(true);
    try {
      localStorage.setItem(DISMISS_KEY, '1');
    } catch {
      /* private mode: just hide for this visit */
    }
  };

  return (
    <>
      <div className="lg:hidden panel flex items-center gap-3 p-3 pl-4 mb-5">
        <img src="/icon-192.png" alt="" className="w-10 h-10 rounded-xl shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold">Install the app</p>
          <p className="text-xs text-[var(--color-text-secondary)]">Open OneCountry from your home screen.</p>
        </div>
        <Button size="sm" leftIcon={<Download className="w-3.5 h-3.5" />} onClick={async () => (iosManual ? setIosHelp(true) : promptInstall())}>
          Install
        </Button>
        <button
          type="button"
          onClick={dismiss}
          className="w-8 h-8 shrink-0 -mr-1 flex items-center justify-center rounded-lg text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-hover)] cursor-pointer"
          aria-label="Dismiss"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
      <IosInstallHelp isOpen={iosHelp} onClose={() => setIosHelp(false)} />
    </>
  );
};
