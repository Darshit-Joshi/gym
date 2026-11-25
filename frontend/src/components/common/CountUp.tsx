import React, { useEffect, useRef, useState } from 'react';

interface CountUpProps {
  value: number;
  /** Animation length in ms. */
  duration?: number;
  /** Formats the number on screen, e.g. as money. Defaults to a whole number. */
  format?: (n: number) => string;
  className?: string;
}

const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

/** Counts up from the previous value to `value` with an ease-out curve. */
export const CountUp: React.FC<CountUpProps> = ({
  value,
  duration = 900,
  format = (n) => Math.round(n).toLocaleString(),
  className,
}) => {
  const [reduced] = useState(prefersReducedMotion);
  const [shown, setShown] = useState(0);
  const fromRef = useRef(0);

  useEffect(() => {
    if (reduced) return;
    const from = fromRef.current;
    const start = performance.now();
    let frame = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      const next = from + (value - from) * eased;
      fromRef.current = next;
      setShown(next);
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value, duration, reduced]);

  return (
    <span className={className} aria-label={format(value)}>
      <span aria-hidden="true">{format(reduced ? value : shown)}</span>
    </span>
  );
};
