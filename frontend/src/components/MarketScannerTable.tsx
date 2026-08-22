import React, { useState } from 'react';
import type { RankedSignal } from '../api/types';
import { useSafeNavigate } from '../utils/navigation';
import { StrengthBadge } from './StrengthBadge';

interface MarketScannerTableProps {
  signals: RankedSignal[];
  onSelectStock?: (stock: RankedSignal) => void;
}

export const MarketScannerTable: React.FC<MarketScannerTableProps> = ({
  signals,
  onSelectStock,
}) => {
  const navigate = useSafeNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [strengthFilter, setStrengthFilter] = useState('ALL');

  const handleStockClick = (sig: RankedSignal) => {
    if (onSelectStock) {
      onSelectStock(sig);
    }
    navigate(`/stocks/${sig.symbol}`);
  };

  const filtered = signals.filter((s) => {
    const matchesSearch =
      s.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (s.company_name && s.company_name.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesStrength =
      strengthFilter === 'ALL'
        ? true
        : strengthFilter === 'BUY_ONLY'
        ? s.buy_count > 0
        : s.strength.toUpperCase() === strengthFilter.toUpperCase();

    return matchesSearch && matchesStrength;
  });

  return (
    <section className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 sm:p-6 shadow-xl space-y-4">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/80 pb-4">
        <div>
          <h2 className="text-base font-bold text-white font-mono tracking-tight flex items-center gap-2">
            Market Scanner
            <span className="text-xs px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 border border-slate-700 font-medium">
              All {signals.length} Universe Constituents
            </span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Full universe signal agreement rankings and indicator ratings
          </p>
        </div>

        {/* Search & Strength Filters */}
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="relative">
            <input
              type="text"
              placeholder="Search symbol / company..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-slate-800/90 border border-slate-700 text-slate-100 text-xs font-mono rounded-lg pl-8 pr-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-emerald-500 w-48 sm:w-56"
            />
            <svg
              className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>

          <select
            value={strengthFilter}
            onChange={(e) => setStrengthFilter(e.target.value)}
            className="bg-slate-800/90 border border-slate-700 text-slate-100 text-xs font-mono rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-emerald-500 cursor-pointer"
          >
            <option value="ALL">All Strengths</option>
            <option value="BUY_ONLY">Actionable BUYs (Score &ge; 1)</option>
            <option value="STRONG">STRONG</option>
            <option value="MODERATE">MODERATE</option>
            <option value="WEAK">WEAK</option>
            <option value="NO_SIGNAL">NO SIGNAL</option>
          </select>
        </div>
      </div>

      {/* Table Container */}
      <div className="overflow-x-auto rounded-xl border border-slate-800/80 max-h-[420px] overflow-y-auto">
        <table className="w-full text-left border-collapse text-xs font-mono">
          <thead className="sticky top-0 z-10">
            <tr className="bg-slate-800 border-b border-slate-700 text-slate-300 uppercase tracking-wider font-semibold text-[11px]">
              <th className="py-2.5 px-3.5 w-12 text-center">Rank</th>
              <th className="py-2.5 px-4">Stock</th>
              <th className="py-2.5 px-3 text-center">Score</th>
              <th className="py-2.5 px-4">Strength</th>
              <th className="py-2.5 px-4">BUY Strategies</th>
              <th className="py-2.5 px-3 text-right">Target / SL</th>
              <th className="py-2.5 px-3.5 text-center">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50 text-slate-200">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-400 font-sans">
                  No stocks match the search query or filter.
                </td>
              </tr>
            ) : (
              filtered.map((sig) => {
                const hasBuy = sig.buy_count > 0;
                return (
                  <tr
                    key={sig.symbol}
                    className="hover:bg-slate-800/40 transition-colors group cursor-pointer"
                    onClick={() => handleStockClick(sig)}
                  >
                    <td className="py-2.5 px-3.5 text-center text-slate-400 font-bold text-[11px]">
                      {sig.rank}
                    </td>

                    <td className="py-2.5 px-4">
                      <div>
                        <span className="font-extrabold text-slate-100 text-xs group-hover:text-emerald-400 transition-colors">
                          {sig.symbol}
                        </span>
                        {sig.company_name && (
                          <span className="block text-[10px] text-slate-400 truncate max-w-[160px] font-sans">
                            {sig.company_name}
                          </span>
                        )}
                      </div>
                    </td>

                    <td className="py-2.5 px-3 text-center">
                      <span
                        className={`text-xs px-2 py-0.5 rounded font-bold border ${
                          sig.score >= 3
                            ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                            : sig.score >= 1
                            ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                            : 'bg-slate-800 text-slate-400 border-slate-700'
                        }`}
                      >
                        {sig.score}/{sig.strategies_evaluated || 5}
                      </span>
                    </td>

                    <td className="py-2.5 px-4">
                      <StrengthBadge strength={sig.strength} size="sm" />
                    </td>

                    <td className="py-2.5 px-4">
                      {sig.buy_strategies.length > 0 ? (
                        <div className="flex flex-wrap gap-1 max-w-xs">
                          {sig.buy_strategies.map((strat) => (
                            <span
                              key={strat}
                              className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 whitespace-nowrap font-medium"
                            >
                              {strat}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-slate-500 text-[11px] italic">None (5 Holds)</span>
                      )}
                    </td>

                    <td className="py-2.5 px-3 text-right">
                      {sig.best_target_price && sig.best_stop_loss ? (
                        <span className="text-slate-300">
                          ₹{sig.best_target_price.toFixed(1)} / <span className="text-rose-400">₹{sig.best_stop_loss.toFixed(1)}</span>
                        </span>
                      ) : (
                        <span className="text-slate-500">-</span>
                      )}
                    </td>

                    <td className="py-2.5 px-3.5 text-center">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleStockClick(sig);
                        }}
                        className={`text-[11px] px-2.5 py-1 rounded-lg border font-sans font-semibold transition-all cursor-pointer ${
                          hasBuy
                            ? 'bg-emerald-600/30 hover:bg-emerald-600 text-emerald-200 hover:text-white border-emerald-500/40 shadow-sm'
                            : 'bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border-slate-700'
                        }`}
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
};
