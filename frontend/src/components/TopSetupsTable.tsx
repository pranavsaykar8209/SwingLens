import React from 'react';
import type { RankedSignal } from '../api/types';
import { useSafeNavigate } from '../utils/navigation';
import { StrengthBadge } from './StrengthBadge';

interface TopSetupsTableProps {
  signals: RankedSignal[];
  selectedStrategyFilter: string;
  onSelectStrategyFilter: (strategy: string) => void;
  onSelectStock?: (stock: RankedSignal) => void;
}

export const STRATEGY_FILTER_OPTIONS = [
  { id: 'ALL', label: 'All Strategies' },
  { id: 'EMA Pullback', label: 'EMA Pullback' },
  { id: 'MA Trend Breakout', label: 'MA Trend Breakout' },
  { id: 'RSI Mean-Reversion', label: 'RSI Mean Reversion' },
  { id: 'MACD Momentum', label: 'MACD Momentum' },
  { id: 'Bollinger Squeeze', label: 'Bollinger Squeeze' },
];

export const TopSetupsTable: React.FC<TopSetupsTableProps> = ({
  signals,
  selectedStrategyFilter,
  onSelectStrategyFilter,
  onSelectStock,
}) => {
  const navigate = useSafeNavigate();

  const handleStockClick = (sig: RankedSignal) => {
    if (onSelectStock) {
      onSelectStock(sig);
    }
    navigate(`/stocks/${sig.symbol}`);
  };

  // Only consider stocks with >=1 strategy BUY as actionable recommendations
  const actionableSignals = signals.filter((s) => s.buy_count > 0);

  // Filter recommendations by selected strategy if not "ALL"
  const filteredRecommendations =
    selectedStrategyFilter === 'ALL'
      ? actionableSignals
      : actionableSignals.filter(
          (s) =>
            s.buy_strategies.some(
              (strat) => strat.toLowerCase() === selectedStrategyFilter.toLowerCase()
            ) || s.best_strategy_name?.toLowerCase() === selectedStrategyFilter.toLowerCase()
        );

  return (
    <section className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 sm:p-6 shadow-xl space-y-4">
      {/* Header & Filter Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/80 pb-4">
        <div className="flex items-center gap-3">
          <h2 className="text-base font-bold text-white font-mono tracking-tight flex items-center gap-2">
            Today's Recommendations
            <span className="text-xs px-2 py-0.5 rounded-md bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 font-medium">
              {filteredRecommendations.length} Actionable Setups
            </span>
          </h2>
        </div>

        {/* Strategy Selector Dropdown */}
        <div className="flex items-center gap-2">
          <label htmlFor="strategy-filter" className="text-xs text-slate-400 font-mono font-medium">
            Strategy:
          </label>
          <select
            id="strategy-filter"
            value={selectedStrategyFilter}
            onChange={(e) => onSelectStrategyFilter(e.target.value)}
            className="bg-slate-800/90 border border-slate-700 text-slate-100 text-xs font-mono rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-emerald-500 cursor-pointer"
          >
            {STRATEGY_FILTER_OPTIONS.map((opt) => (
              <option key={opt.id} value={opt.id} className="bg-slate-900 text-slate-100">
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Table Container */}
      {filteredRecommendations.length === 0 ? (
        <div className="py-10 px-4 text-center bg-slate-950/40 border border-slate-800/50 rounded-xl space-y-1.5">
          <p className="text-sm font-semibold text-slate-300 font-mono">No Actionable Recommendations Today</p>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            {selectedStrategyFilter === 'ALL'
              ? 'None of the 49 universe constituents met the quantitative BUY setup criteria today. See the Market Scanner below for all stock evaluations.'
              : `No stocks currently have an active BUY signal under the ${selectedStrategyFilter} strategy.`}
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-800/80">
          <table className="w-full text-left border-collapse text-xs font-mono">
            <thead>
              <tr className="bg-slate-800/50 border-b border-slate-700/60 text-slate-400 uppercase tracking-wider font-semibold text-[11px]">
                <th className="py-3 px-3.5 w-12 text-center">#</th>
                <th className="py-3 px-4">Stock</th>
                <th className="py-3 px-3 text-center">Score</th>
                <th className="py-3 px-4">Strength</th>
                <th className="py-3 px-4">BUY Strategies</th>
                <th className="py-3 px-3 text-right">Entry</th>
                <th className="py-3 px-3 text-right">Stop Loss</th>
                <th className="py-3 px-3 text-right">Target</th>
                <th className="py-3 px-3 text-center">R:R</th>
                <th className="py-3 px-3.5 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50 text-slate-200">
              {filteredRecommendations.map((sig, idx) => (
                <tr
                  key={sig.symbol}
                  className="hover:bg-slate-800/40 transition-colors group cursor-pointer"
                  onClick={() => handleStockClick(sig)}
                >
                  {/* Rank */}
                  <td className="py-3 px-3.5 text-center">
                    <span className="inline-flex items-center justify-center h-5 w-5 rounded-full bg-slate-800 text-slate-300 font-bold text-[10px] border border-slate-700">
                      {idx + 1}
                    </span>
                  </td>

                  {/* Symbol & Company Name */}
                  <td className="py-3 px-4">
                    <div>
                      <span className="font-extrabold text-slate-100 text-sm group-hover:text-emerald-400 transition-colors">
                        {sig.symbol}
                      </span>
                      {sig.company_name && (
                        <span className="block text-[10px] text-slate-400 truncate max-w-[150px] font-sans">
                          {sig.company_name}
                        </span>
                      )}
                    </div>
                  </td>

                  {/* Score */}
                  <td className="py-3 px-3 text-center">
                    <span
                      className={`font-bold text-xs px-2 py-0.5 rounded border ${
                        sig.score >= 3
                          ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 font-extrabold'
                          : sig.score === 2
                          ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                          : 'bg-slate-800 text-slate-300 border-slate-700'
                      }`}
                    >
                      {sig.score}/{sig.strategies_evaluated || 5}
                    </span>
                  </td>

                  {/* Strength */}
                  <td className="py-3 px-4">
                    <StrengthBadge strength={sig.strength} size="sm" />
                  </td>

                  {/* BUY Strategies */}
                  <td className="py-3 px-4">
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
                  </td>

                  {/* Entry Price */}
                  <td className="py-3 px-3 text-right font-medium">
                    {sig.best_entry_price !== null && sig.best_entry_price !== undefined ? (
                      <span className="text-emerald-400 font-bold">₹{sig.best_entry_price.toFixed(2)}</span>
                    ) : (
                      <span className="text-slate-500">-</span>
                    )}
                  </td>

                  {/* Stop Loss */}
                  <td className="py-3 px-3 text-right font-medium">
                    {sig.best_stop_loss !== null && sig.best_stop_loss !== undefined ? (
                      <span className="text-rose-400 font-bold">₹{sig.best_stop_loss.toFixed(2)}</span>
                    ) : (
                      <span className="text-slate-500">-</span>
                    )}
                  </td>

                  {/* Target */}
                  <td className="py-3 px-3 text-right font-medium">
                    {sig.best_target_price !== null && sig.best_target_price !== undefined ? (
                      <span className="text-teal-300 font-bold">₹{sig.best_target_price.toFixed(2)}</span>
                    ) : (
                      <span className="text-slate-500">-</span>
                    )}
                  </td>

                  {/* Risk:Reward */}
                  <td className="py-3 px-3 text-center">
                    {sig.best_risk_reward !== null && sig.best_risk_reward !== undefined ? (
                      <span className="text-amber-300 font-bold">{sig.best_risk_reward.toFixed(1)}:1</span>
                    ) : (
                      <span className="text-slate-500">-</span>
                    )}
                  </td>

                  {/* Action Button */}
                  <td className="py-3 px-3.5 text-center">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleStockClick(sig);
                      }}
                      className="text-xs px-2.5 py-1 rounded-lg border bg-emerald-600/30 hover:bg-emerald-600 text-emerald-200 hover:text-white border-emerald-500/40 font-sans font-semibold transition-all cursor-pointer shadow-sm"
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
};
