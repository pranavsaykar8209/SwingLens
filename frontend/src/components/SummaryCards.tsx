import React from 'react';

interface SummaryCardsProps {
  evaluatedCount?: number;
  buyCount: number;
  strongCount?: number;
  watchlistCount?: number;
  watchCount?: number;
  holdCount?: number;
  skipCount?: number;
}

export const SummaryCards: React.FC<SummaryCardsProps> = ({
  evaluatedCount,
  buyCount,
  strongCount = 0,
  watchlistCount = 0,
  watchCount = 0,
  holdCount = 0,
  skipCount = 0,
}) => {
  const isRecommendationMode = evaluatedCount !== undefined;

  const recommendationCards = [
    {
      label: 'STOCKS EVALUATED',
      count: evaluatedCount ?? 0,
      color: 'border-slate-800 bg-slate-900/50 text-slate-100',
      badgeColor: 'bg-slate-800 text-slate-300 border-slate-700',
      subtext: 'NIFTY Next 50 Universe',
    },
    {
      label: 'BUY SETUPS',
      count: buyCount,
      color: 'border-emerald-500/30 bg-emerald-950/15 text-emerald-400',
      badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
      subtext: 'Passed >=1 Strategy Filter',
    },
    {
      label: 'HIGH AGREEMENT',
      count: strongCount,
      color: 'border-cyan-500/30 bg-cyan-950/15 text-cyan-400',
      badgeColor: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
      subtext: '>=3 Strategies Agree',
    },
    {
      label: 'ACTIVE WATCHLIST',
      count: watchlistCount,
      color: 'border-amber-500/30 bg-amber-950/15 text-amber-400',
      badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
      subtext: 'Monitored Setups',
    },
  ];

  const legacyCards = [
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

  const cards = isRecommendationMode ? recommendationCards : legacyCards;

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
      {cards.map((card) => (
        <div
          key={card.label}
          className={`p-4 rounded-xl border backdrop-blur-sm shadow-sm transition-all hover:border-slate-700 ${card.color}`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold tracking-wider text-slate-400 font-mono">
              {card.label}
            </span>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl sm:text-3xl font-bold font-mono tracking-tight text-white">{card.count}</span>
            <span className="text-[10px] text-slate-400 font-sans">{card.subtext}</span>
          </div>
        </div>
      ))}
    </div>
  );
};
