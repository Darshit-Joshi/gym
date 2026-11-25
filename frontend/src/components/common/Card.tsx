import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
  /** The lime-tinted surface for the most important block on a page. */
  hero?: boolean;
}

export const Card: React.FC<CardProps> = ({ children, className = '', onClick, hero = false }) => {
  const interactive = onClick ? 'fx-card-interactive cursor-pointer' : '';
  return (
    <div
      onClick={onClick}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick();
              }
            }
          : undefined
      }
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      className={`${hero ? 'panel-hero' : 'panel'} text-[var(--color-text)] p-5 ${interactive} ${className}`}
    >
      {children}
    </div>
  );
};
