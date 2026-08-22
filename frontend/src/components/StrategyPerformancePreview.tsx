import React from 'react';
import type { StrategyQualityMetrics } from '../api/types';

interface StrategyPerformancePreviewProps {
  strategies: StrategyQualityMetrics[];
}

export const StrategyPerformancePreview: React.FC<StrategyPerformancePreviewProps> = ({
  strategies,
}) => {
  // Filter out example passthrough strategy if present
  const activeStrategies = strategies.filter(
    (s) => s.strategy_name.toLowerCase() !== 'passthrough hold strategy'
  );

  return (
    <section className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 sm:p-8 shadow-xl space-y-5">
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
        <div>
          <h2 className="text-base font-bold text-white font-mono tracking-tight">
            Strategy Performance
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Empirical historical validation metrics across representative stock universe
          </p>
        </div>
        <span className="text-xs px-2.5 py-0.5 rounded-md bg-indigo-500/10 text-indigo-300 border border-indigo-500/30 font-mono font-medium">
          5 Frozen Strategies
        </span>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-800/80">
        <table className="w-full text-left border-collapse text-xs font-mono">
          <thead>
            <tr className="bg-slate-800/50 border-b border-slate-700/60 text-slate-400 uppercase tracking-wider text-[11px]">
              <th className="py-3 px-4">Strategy</th>
              <th className="py-3 px-3 text-center">Trades</th>
              <th className="py-3 px-3 text-right">Win Rate</th>
              <th className="py-3 px-3 text-right">Avg R</th>
              <th className="py-3 px-3 text-right">Profit Factor</th>
              <th className="py-3 px-3 text-center">Classification</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50 text-slate-200">
            {activeStrategies.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-6 text-center text-slate-500 font-sans">
                  No strategy performance data loaded.
                </td>
              </tr>
            ) : (
              activeStrategies.map((strat) => {
                const isPositive = strat.classification === 'POSITIVE';
                const isNegative = strat.classification === 'NEGATIVE';

                return (
                  <tr key={strat.strategy_name} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-4">
                      <span className="font-extrabold text-slate-100 font-mono">
                        {strat.strategy_name}
                      </span>
                      <span className="text-[10px] text-slate-500 ml-1.5">v{strat.strategy_version}</span>
                    </td>
                    <td className="py-3 px-3 text-center font-bold text-white">
                      {strat.trades}
                    </td>
                    <td className="py-3 px-3 text-right">
                      <span className="font-bold text-indigo-300">{strat.win_rate.toFixed(1)}%</span>
                    </td>
                    <td className="py-3 px-3 text-right">
                      <span
                        className={`font-bold ${
                          strat.average_r > 0
                            ? 'text-emerald-400'
                            : strat.average_r < 0
                            ? 'text-rose-400'
                            : 'text-slate-400'
                        }`}
                      >
                        {strat.average_r > 0 ? '+' : ''}
                        {strat.average_r.toFixed(2)}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-right">
                      <span
                        className={`font-bold ${
                          strat.profit_factor >= 1.0 ? 'text-emerald-400' : 'text-rose-400'
                        }`}
                      >
                        {strat.profit_factor.toFixed(2)}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-center">
                      <span
                        className={`text-[10px] px-2.5 py-0.5 rounded-full border font-bold uppercase ${
                          isPositive
                            ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                            : isNegative
                            ? 'bg-rose-500/15 text-rose-300 border-rose-500/30'
                            : 'bg-slate-800 text-slate-400 border-slate-700'
                        }`}
                      >
                        {strat.classification}
                      </span>
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
