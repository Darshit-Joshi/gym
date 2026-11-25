import React from 'react';
import { Loader2 } from 'lucide-react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const SIZES = {
  sm: 'text-xs px-3 h-9 gap-1.5 rounded-lg',
  md: 'text-sm px-4 h-11 gap-2 rounded-xl',
  lg: 'text-base px-5 h-12 gap-2.5 rounded-xl',
};

const VARIANTS = {
  primary:
    'fx-btn-primary bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-[var(--color-primary-text)] font-semibold',
  secondary:
    'bg-[var(--color-surface-elevated)] hover:bg-[var(--color-hover)] text-[var(--color-text)] border border-[var(--color-border)] hover:border-[var(--color-border-strong)] font-semibold',
  danger: 'bg-rose-600 hover:bg-rose-500 text-white font-semibold',
  outline:
    'border border-[var(--color-border-strong)] hover:border-[rgba(var(--color-primary-rgb),0.6)] text-[var(--color-text)] hover:bg-[var(--color-hover)] bg-transparent font-medium',
  ghost: 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)] hover:bg-[var(--color-hover)] bg-transparent font-medium',
};

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  leftIcon,
  rightIcon,
  disabled,
  className = '',
  type = 'button',
  ...props
}) => (
  <button
    type={type}
    className={`inline-flex items-center justify-center whitespace-nowrap transition-all duration-150 active:scale-[0.97] disabled:opacity-45 disabled:cursor-not-allowed disabled:active:scale-100 select-none cursor-pointer ${SIZES[size]} ${VARIANTS[variant]} ${className}`}
    disabled={disabled || isLoading}
    {...props}
  >
    {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : leftIcon}
    {children}
    {!isLoading && rightIcon}
  </button>
);
