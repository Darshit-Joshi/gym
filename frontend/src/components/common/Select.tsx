import React, { useId } from 'react';
import { ChevronDown } from 'lucide-react';
import { FIELD_CLASSES } from './Input';

interface SelectOption {
  value: string | number;
  label: string;
}

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options: SelectOption[];
  placeholder?: string;
}

export const Select: React.FC<SelectProps> = ({ label, error, options, placeholder, id, required, className = '', ...props }) => {
  const autoId = useId();
  const selectId = id || autoId;

  return (
    <div className="w-full space-y-1.5">
      {label && (
        <label htmlFor={selectId} className="block text-[13px] font-medium text-[var(--color-text-secondary)]">
          {label} {required && <span className="text-rose-500">*</span>}
        </label>
      )}
      <div className="relative">
        <select
          id={selectId}
          required={required}
          className={`${FIELD_CLASSES} h-11 pr-9 appearance-none cursor-pointer ${
            error ? 'border-rose-500' : 'border-[var(--color-input-border)] hover:border-[var(--color-border-strong)]'
          } ${className}`}
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((opt) => (
            <option key={opt.value} value={opt.value} className="bg-[var(--color-surface)] text-[var(--color-text)]">
              {opt.label}
            </option>
          ))}
        </select>
        <ChevronDown className="w-4 h-4 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-[var(--color-text-muted)]" />
      </div>
      {error && <p className="text-xs text-rose-500 font-medium">{error}</p>}
    </div>
  );
};
