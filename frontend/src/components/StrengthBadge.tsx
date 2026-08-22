import React from 'react';
import type { SignalStrengthType } from '../api/types';

interface StrengthBadgeProps {
  strength: SignalStrengthType | string;
  size?: 'sm' | 'md' | 'lg';
}

export const StrengthBadge: React.FC<StrengthBadgeProps> = ({
  strength,
  size = 'md',
}) => {
  const normalized = (strength || 'NO_SIGNAL').toUpperCase();

  let colorClasses = 'bg-slate-800 text-slate-400 border-slate-700/60';
  let dotColor = 'bg-slate-500';
  let label = normalized.replace('_', ' ');

  if (normalized === 'VERY_STRONG') {
    colorClasses = 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 shadow-sm shadow-emerald-500/10';
    dotColor = 'bg-emerald-400';
    label = 'VERY STRONG';
  } else if (normalized === 'STRONG') {
    colorClasses = 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
    dotColor = 'bg-emerald-400';
    label = 'STRONG';
  } else if (normalized === 'MODERATE') {
    colorClasses = 'bg-amber-500/15 text-amber-300 border-amber-500/30';
    dotColor = 'bg-amber-400';
    label = 'MODERATE';
  } else if (normalized === 'WEAK') {
    colorClasses = 'bg-slate-800 text-slate-300 border-slate-700';
    dotColor = 'bg-slate-400';
    label = 'WEAK';
  } else {
    colorClasses = 'bg-slate-800/60 text-slate-400 border-slate-700/50';
    dotColor = 'bg-slate-500';
    label = 'NO SIGNAL';
  }

  const sizeClasses =
    size === 'sm'
      ? 'text-[10px] px-2 py-0.5'
      : size === 'lg'
      ? 'text-sm px-3.5 py-1.5'
      : 'text-xs px-2.5 py-1';

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-lg border font-mono font-bold uppercase tracking-wide ${sizeClasses} ${colorClasses}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${dotColor}`} />
      {label}
    </span>
  );
};
