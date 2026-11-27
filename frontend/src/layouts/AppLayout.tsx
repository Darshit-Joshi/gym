import React, { useEffect, useRef, useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  Dumbbell,
  CalendarCheck2,
  LogOut,
  KeyRound,
  Wallet,
  Library,
  Bell,
  ChevronUp,
  Sun,
  Moon,
  Download,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { NotificationBell } from '../components/notifications/NotificationBell';
import { ChangePasswordModal } from '../components/auth/ChangePasswordModal';
import { longDay, todayIso } from '../utils/format';
import { useInstallPrompt } from '../utils/installPrompt';
import { InstallBanner, IosInstallHelp } from '../components/common/InstallApp';

const PRIMARY_NAV = [
  { name: 'Dashboard', short: 'Home', path: '/dashboard', icon: LayoutDashboard },
  { name: 'Clients', short: 'Clients', path: '/clients', icon: Users },
  { name: 'Attendance', short: 'Attendance', path: '/attendance', icon: CalendarCheck2 },
  { name: 'Fees', short: 'Fees', path: '/fees', icon: Wallet },
  { name: 'Workouts', short: 'Workouts', path: '/workouts', icon: Dumbbell },
];

const SECONDARY_NAV = [
  { name: 'Exercise library', path: '/exercises', icon: Library },
  { name: 'Alerts', path: '/notifications', icon: Bell },
];

const Brand: React.FC<{ compact?: boolean }> = ({ compact }) => (
  <Link to="/dashboard" className="flex items-center gap-3 group" aria-label="OneCountry Fitness, go to dashboard">
    <span
      aria-hidden="true"
      className="w-10 h-10 rounded-xl bg-[var(--color-primary)] text-[var(--color-primary-text)] flex items-center justify-center text-xl font-bold shadow-[0_6px_20px_-6px_rgba(var(--color-primary-rgb),0.6)] transition-transform group-hover:-rotate-6"
      style={{ fontFamily: 'var(--font-display)' }}
    >
      1
    </span>
    {!compact && (
      <span className="leading-none">
        <span className="block font-semibold text-[15px] text-[var(--color-text)]" style={{ fontFamily: 'var(--font-display)' }}>
          OneCountry
        </span>
        <span className="block text-[10px] font-semibold tracking-[0.22em] uppercase text-[var(--color-accent-ink)] mt-1">
          Fitness Studio
        </span>
      </span>
    )}
  </Link>
);

/** Profile menu: password, theme and sign out. Opens upward from the sidebar, downward from the top bar. */
const ProfileMenu: React.FC<{ placement: 'up' | 'down'; onChangePassword: () => void }> = ({ placement, onChangePassword }) => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [iosHelp, setIosHelp] = useState(false);
  const install = useInstallPrompt();
  const ref = useRef<HTMLDivElement>(null);
  const initial = user?.name?.trim().charAt(0).toUpperCase() || 'T';

  useEffect(() => {
    const onDown = (e: PointerEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('pointerdown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('pointerdown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, []);

  const item = 'w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm text-left transition-colors cursor-pointer';

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="menu"
        className={
          placement === 'up'
            ? 'w-full flex items-center gap-3 p-2 rounded-xl hover:bg-[var(--color-hover)] transition-colors cursor-pointer'
            : 'w-10 h-10 flex items-center justify-center rounded-full cursor-pointer'
        }
      >
        <span className="w-9 h-9 rounded-full flex items-center justify-center text-sm font-semibold bg-[var(--color-primary)] text-[var(--color-primary-text)]">
          {initial}
        </span>
        {placement === 'up' && (
          <>
            <span className="flex-1 min-w-0 text-left">
              <span className="block text-sm font-semibold text-[var(--color-text)] truncate">{user?.name}</span>
              <span className="block text-xs text-[var(--color-text-muted)]">Trainer</span>
            </span>
            <ChevronUp className={`w-4 h-4 text-[var(--color-text-muted)] transition-transform ${open ? '' : 'rotate-180'}`} />
          </>
        )}
      </button>
      {open && (
        <div
          role="menu"
          className={`fx-dialog absolute z-50 w-60 p-1.5 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] shadow-[var(--shadow-dropdown)] ${
            placement === 'up' ? 'bottom-full mb-2 left-0 right-0 w-auto' : 'top-12 right-0'
          }`}
        >
          {placement === 'down' && (
            <>
              <div className="px-3 py-2 mb-1 border-b border-[var(--color-border)]">
                <p className="text-sm font-semibold truncate">{user?.name}</p>
                <p className="text-xs text-[var(--color-text-muted)]">Trainer</p>
              </div>
              {/* The phone tab bar only fits the five main pages; the library lives here. */}
              {SECONDARY_NAV.map(({ name, path, icon: Icon }) => (
                <button
                  key={path}
                  role="menuitem"
                  type="button"
                  onClick={() => {
                    setOpen(false);
                    navigate(path);
                  }}
                  className={`${item} hover:bg-[var(--color-hover)]`}
                >
                  <Icon className="w-4 h-4 text-[var(--color-text-muted)]" /> {name}
                </button>
              ))}
              <div className="my-1 border-t border-[var(--color-border)]" />
            </>
          )}
          <button
            role="menuitem"
            type="button"
            onClick={() => {
              setOpen(false);
              onChangePassword();
            }}
            className={`${item} hover:bg-[var(--color-hover)]`}
          >
            <KeyRound className="w-4 h-4 text-[var(--color-text-muted)]" /> Change password
          </button>
          {install.available && (
            <button
              role="menuitem"
              type="button"
              onClick={() => {
                setOpen(false);
                if (install.iosManual) setIosHelp(true);
                else void install.promptInstall();
              }}
              className={`${item} hover:bg-[var(--color-hover)]`}
            >
              <Download className="w-4 h-4 text-[var(--color-text-muted)]" /> Install app
            </button>
          )}
          <button role="menuitem" type="button" onClick={toggleTheme} className={`${item} hover:bg-[var(--color-hover)]`}>
            {theme === 'dark' ? <Sun className="w-4 h-4 text-[var(--color-text-muted)]" /> : <Moon className="w-4 h-4 text-[var(--color-text-muted)]" />}
            {theme === 'dark' ? 'Light mode' : 'Dark mode'}
          </button>
          <button
            role="menuitem"
            type="button"
            onClick={async () => {
              await logout();
              navigate('/login');
            }}
            className={`${item} text-rose-600 dark:text-rose-400 hover:bg-rose-500/10`}
          >
            <LogOut className="w-4 h-4" /> Sign out
          </button>
        </div>
      )}
      <IosInstallHelp isOpen={iosHelp} onClose={() => setIosHelp(false)} />
    </div>
  );
};

export const AppLayout: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [changePasswordOpen, setChangePasswordOpen] = useState(false);

  return (
    <div className="relative isolate min-h-dvh bg-[var(--color-background)] text-[var(--color-text)]">
      <div className="fx-ambient" aria-hidden="true" />

      {/* Desktop sidebar */}
      <aside className="hidden lg:flex fixed inset-y-0 left-0 z-40 w-64 flex-col border-r border-[var(--color-sidebar-border)] bg-[var(--color-sidebar)]">
        <div className="px-5 h-20 flex items-center">
          <Brand />
        </div>

        <div className="px-4">
          <button
            type="button"
            onClick={() => navigate('/attendance')}
            className="fx-btn-primary w-full h-11 flex items-center justify-center gap-2 rounded-xl bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-[var(--color-primary-text)] text-sm font-semibold transition-colors cursor-pointer"
          >
            <CalendarCheck2 className="w-4 h-4" /> Mark attendance
          </button>
        </div>

        <nav aria-label="Main" className="flex-1 overflow-y-auto px-4 pt-6 space-y-6">
          <div>
            <p className="eyebrow px-3 mb-2">Manage</p>
            <ul className="space-y-0.5">
              {PRIMARY_NAV.map(({ name, path, icon: Icon }) => (
                <li key={path}>
                  <NavLink
                    to={path}
                    className={({ isActive }) =>
                      `flex items-center gap-3 px-3 h-10 rounded-lg text-sm font-medium transition-colors ${
                        isActive
                          ? 'fx-nav-active bg-[var(--color-nav-active)] text-[var(--color-nav-active-text)]'
                          : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)] hover:bg-[var(--color-hover)]'
                      }`
                    }
                  >
                    <Icon className="w-[18px] h-[18px] shrink-0" />
                    {name}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="eyebrow px-3 mb-2">Library</p>
            <ul className="space-y-0.5">
              {SECONDARY_NAV.map(({ name, path, icon: Icon }) => (
                <li key={path}>
                  <NavLink
                    to={path}
                    className={({ isActive }) =>
                      `flex items-center gap-3 px-3 h-10 rounded-lg text-sm font-medium transition-colors ${
                        isActive
                          ? 'fx-nav-active bg-[var(--color-nav-active)] text-[var(--color-nav-active-text)]'
                          : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)] hover:bg-[var(--color-hover)]'
                      }`
                    }
                  >
                    <Icon className="w-[18px] h-[18px] shrink-0" />
                    {name}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        </nav>

        <div className="p-3 border-t border-[var(--color-sidebar-border)]">
          <ProfileMenu placement="up" onChangePassword={() => setChangePasswordOpen(true)} />
        </div>
      </aside>

      <div className="lg:pl-64 flex flex-col min-h-dvh">
        {/* Top bar */}
        <header className="sticky top-0 z-30 pt-[env(safe-area-inset-top)] border-b border-[var(--color-sidebar-border)] bg-[var(--color-background)]/80 backdrop-blur-md">
          <div className="h-16 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center gap-3">
            <div className="lg:hidden">
              <Brand compact />
            </div>
            <p className="hidden lg:flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
              <span className="fx-live-dot" aria-hidden="true" />
              {longDay(todayIso())}
            </p>
            <div className="ml-auto flex items-center gap-1">
              <NotificationBell />
              <div className="lg:hidden">
                <ProfileMenu placement="down" onChangePassword={() => setChangePasswordOpen(true)} />
              </div>
            </div>
          </div>
        </header>

        <main className="flex-1 min-w-0 pb-28 lg:pb-12">
          <div key={location.pathname} className="fx-page max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 sm:pt-8">
            {location.pathname === '/dashboard' && <InstallBanner />}
            <Outlet />
          </div>
        </main>
      </div>

      {/* Phone and tablet tab bar */}
      <nav
        aria-label="Main"
        className="lg:hidden fixed bottom-0 inset-x-0 z-40 border-t border-[var(--color-sidebar-border)] bg-[var(--color-sidebar)]/95 backdrop-blur-md pb-safe"
      >
        <ul className="grid grid-cols-5 max-w-lg mx-auto px-1 pt-1.5">
          {PRIMARY_NAV.map(({ short, path, icon: Icon }) => (
            <li key={path}>
              <NavLink
                to={path}
                className={({ isActive }) =>
                  `flex flex-col items-center gap-1 py-1.5 rounded-xl text-[10.5px] font-medium transition-colors ${
                    isActive ? 'text-[var(--color-nav-active-text)]' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)]'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <span
                      className={`w-12 h-8 rounded-full flex items-center justify-center transition-colors ${
                        isActive ? 'bg-[var(--color-nav-active)]' : ''
                      }`}
                    >
                      <Icon className="w-5 h-5" />
                    </span>
                    {short}
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <ChangePasswordModal isOpen={changePasswordOpen} onClose={() => setChangePasswordOpen(false)} />
    </div>
  );
};
