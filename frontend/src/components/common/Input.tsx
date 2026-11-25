import React, { useId, useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';

export const FIELD_CLASSES =
  'w-full rounded-xl bg-[var(--color-input)] border px-3.5 text-sm text-[var(--color-text)] placeholder-[var(--color-text-muted)] transition-colors focus:outline-none focus:border-[var(--color-input-focus)] focus:ring-2 focus:ring-[rgba(var(--color-primary-rgb),0.18)] disabled:opacity-50';

const borderFor = (error?: string) =>
  error ? 'border-rose-500' : 'border-[var(--color-input-border)] hover:border-[var(--color-border-strong)]';

const Label: React.FC<{ htmlFor?: string; required?: boolean; children: React.ReactNode }> = ({ htmlFor, required, children }) => (
  <label htmlFor={htmlFor} className="block text-[13px] font-medium text-[var(--color-text-secondary)]">
    {children} {required && <span className="text-rose-500">*</span>}
  </label>
);

const Hint: React.FC<{ error?: string; helperText?: string }> = ({ error, helperText }) =>
  error ? (
    <p className="text-xs text-rose-500 font-medium">{error}</p>
  ) : helperText ? (
    <p className="text-xs text-[var(--color-text-muted)]">{helperText}</p>
  ) : null;

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  isPassword?: boolean;
}

export const Input: React.FC<InputProps> = ({
  label,
  error,
  helperText,
  isPassword = false,
  type = 'text',
  id,
  className = '',
  required,
  ...props
}) => {
  const [showPassword, setShowPassword] = useState(false);
  const autoId = useId();
  const inputId = id || autoId;
  const inputType = isPassword ? (showPassword ? 'text' : 'password') : type;

  return (
    <div className="w-full space-y-1.5">
      {label && (
        <Label htmlFor={inputId} required={required}>
          {label}
        </Label>
      )}
      <div className="relative">
        <input
          id={inputId}
          type={inputType}
          required={required}
          aria-invalid={!!error || undefined}
          className={`${FIELD_CLASSES} h-11 ${borderFor(error)} ${isPassword ? 'pr-11' : ''} ${className}`}
          {...props}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute inset-y-0 right-0 flex items-center px-3.5 text-[var(--color-text-muted)] hover:text-[var(--color-text)] cursor-pointer"
            aria-label={showPassword ? 'Hide password' : 'Show password'}
          >
            {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        )}
      </div>
      <Hint error={error} helperText={helperText} />
    </div>
  );
};

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Textarea: React.FC<TextareaProps> = ({ label, error, helperText, id, className = '', required, rows = 3, ...props }) => {
  const autoId = useId();
  const inputId = id || autoId;
  return (
    <div className="w-full space-y-1.5">
      {label && (
        <Label htmlFor={inputId} required={required}>
          {label}
        </Label>
      )}
      <textarea
        id={inputId}
        rows={rows}
        required={required}
        className={`${FIELD_CLASSES} py-2.5 resize-y ${borderFor(error)} ${className}`}
        {...props}
      />
      <Hint error={error} helperText={helperText} />
    </div>
  );
};
