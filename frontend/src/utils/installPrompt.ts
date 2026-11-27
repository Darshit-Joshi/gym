import { useSyncExternalStore } from 'react';

/**
 * "Install app" support. Chrome and Edge (Android and desktop) fire `beforeinstallprompt` when the
 * site can be installed; we keep the event so a button can show the install dialog later.
 * iPhone and iPad Safari have no such event: the user adds the app from the Share menu instead.
 *
 * Imported from main.tsx so the listener is attached before the browser fires the event.
 */
interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

let deferred: BeforeInstallPromptEvent | null = null;
const listeners = new Set<() => void>();
const notify = () => listeners.forEach((l) => l());

if (typeof window !== 'undefined') {
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault(); // we offer our own button instead of the browser's mini banner
    deferred = e as BeforeInstallPromptEvent;
    notify();
  });
  window.addEventListener('appinstalled', () => {
    deferred = null;
    notify();
  });
}

const subscribe = (cb: () => void) => {
  listeners.add(cb);
  return () => listeners.delete(cb);
};

/** Already running from the home screen (no browser bars). */
export const isStandalone = (): boolean =>
  typeof window !== 'undefined' &&
  (window.matchMedia('(display-mode: standalone)').matches || (navigator as Navigator & { standalone?: boolean }).standalone === true);

const isIos = (): boolean =>
  typeof navigator !== 'undefined' &&
  (/iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1));

export function useInstallPrompt() {
  const event = useSyncExternalStore(subscribe, () => deferred, () => null);
  const standalone = isStandalone();
  const iosManual = !standalone && isIos();

  /** Shows the browser's install dialog. Returns false when there is none (e.g. on iPhone). */
  const promptInstall = async (): Promise<boolean> => {
    if (!deferred) return false;
    const e = deferred;
    deferred = null; // the event can only be used once
    notify();
    await e.prompt();
    await e.userChoice.catch(() => undefined);
    return true;
  };

  return {
    /** Something useful to offer: a real install dialog, or Add to Home Screen steps on iOS. */
    available: !standalone && (!!event || iosManual),
    iosManual: iosManual && !event,
    promptInstall,
  };
}
