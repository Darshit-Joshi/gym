import React from 'react';
import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';

interface ThemeToggleProps {
  className?: string;
  size?: 'sm' | 'md';
}

export const ThemeToggle: React.FC<ThemeToggleProps> = ({ className = '', size = 'md' }) => {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className={`group relative inline-flex items-center justify-center rounded-lg overflow-hidden cursor-pointer transition-all duration-300 bg-[var(--color-surface-elevated)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] hover:border-[rgba(var(--color-primary-rgb),0.45)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] ${
        size === 'sm' ? 'w-8 h-8' : 'w-9 h-9'
      } ${className}`}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {/* Both icons stay mounted so they can rotate in and out */}
      <Sun
        className={`absolute w-4 h-4 transition-all duration-500 ${
          isDark ? 'opacity-100 rotate-0 scale-100' : 'opacity-0 -rotate-90 scale-50'
        } group-hover:rotate-45`}
      />
      <Moon
        className={`absolute w-4 h-4 transition-all duration-500 ${
          isDark ? 'opacity-0 rotate-90 scale-50' : 'opacity-100 rotate-0 scale-100'
        } group-hover:-rotate-12`}
      />
    </button>
  );
};
