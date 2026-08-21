import React from 'react';

interface SummaryCardsProps {
  buyCount: number;
  watchCount: number;
  holdCount: number;
  skipCount: number;
}

export const SummaryCards: React.FC<SummaryCardsProps> = ({
  buyCount,
  watchCount,
  holdCount,
  skipCount,
}) => {
  const cards = [
    {
      label: 'BUY SIGNALS',
      count: buyCount,
      color: 'border-emerald-500/40 bg-emerald-950/20 text-emerald-400',
      badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
      subtext: 'Passed setup filters',
    },
    {
      label: 'WATCH',
      count: watchCount,
      color: 'border-amber-500/30 bg-amber-950/20 text-amber-400',
      badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
      subtext: 'Near setup threshold',
    },
    {
      label: 'HOLD',
      count: holdCount,
      color: 'border-slate-700/60 bg-slate-800/40 text-slate-300',
      badgeColor: 'bg-slate-700/40 text-slate-300 border-slate-600/40',
      subtext: 'No active setup',
    },
    {
      label: 'SKIPPED',
      count: skipCount,
      color: 'border-rose-500/30 bg-rose-950/20 text-rose-400',
      badgeColor: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
      subtext: 'Insufficient data (<200 candles)',
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 my-6">
      {cards.map((card) => (
        <div
          key={card.label}
          className={`p-5 rounded-xl border backdrop-blur-sm shadow-md transition-all hover:translate-y-[-2px] ${card.color}`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold tracking-wider text-slate-400">
              {card.label}
            </span>
            <span
              className={`text-xs px-2 py-0.5 rounded-full border font-mono font-medium ${card.badgeColor}`}
            >
              Count
            </span>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-3xl font-bold font-mono tracking-tight">{card.count}</span>
            <span className="text-[11px] text-slate-400">{card.subtext}</span>
          </div>
        </div>
      ))}
    </div>
  );
};
