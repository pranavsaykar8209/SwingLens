import React from 'react';
import type { StrategyQualityMetrics } from '../api/types';
import { SafeLink } from '../utils/navigation';

interface StrategyPerformancePreviewProps {
  strategies: StrategyQualityMetrics[];
}

export const StrategyPerformancePreview: React.FC<StrategyPerformancePreviewProps> = ({
  strategies,
}) => {
  const activeStrategies = strategies.filter(
    (s) => s.strategy_name.toLowerCase() !== 'passthrough hold strategy'
  );

  return (
    <section className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 sm:p-6 shadow-xl space-y-4 flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <div className="flex items-center gap-2.5">
            <h2 className="text-base font-bold text-white font-mono tracking-tight">
              Strategy Health
            </h2>
            <span className="text-xs px-2 py-0.5 rounded-md bg-indigo-500/10 text-indigo-300 border border-indigo-500/30 font-mono font-medium">
              5 Strategies
            </span>
          </div>

          <SafeLink
            to="/analytics"
            className="text-xs text-indigo-400 hover:text-indigo-300 font-mono font-semibold flex items-center gap-1 transition-colors cursor-pointer bg-slate-800/60 hover:bg-slate-800 px-2.5 py-1 rounded-lg border border-slate-700/60"
          >
            <span>View Analytics</span>
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </SafeLink>
        </div>

        {activeStrategies.length === 0 ? (
          <div className="py-8 text-center text-slate-400 text-xs font-mono">
            Loading strategy performance metrics...
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-800/80 mt-4">
            <table className="w-full text-left border-collapse text-xs font-mono">
              <thead>
                <tr className="bg-slate-800/50 border-b border-slate-700/60 text-slate-400 uppercase tracking-wider text-[10px]">
                  <th className="py-2.5 px-3">Strategy</th>
                  <th className="py-2.5 px-2 text-right">Win Rate</th>
                  <th className="py-2.5 px-2 text-right">Avg R</th>
                  <th className="py-2.5 px-2 text-center">Health</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50 text-slate-200">
                {activeStrategies.map((strat) => {
                  const isPositive = strat.classification === 'POSITIVE';
                  const isNegative = strat.classification === 'NEGATIVE';

                  return (
                    <tr key={strat.strategy_name} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-2.5 px-3 font-semibold text-slate-200">
                        {strat.strategy_name}
                      </td>
                      <td className="py-2.5 px-2 text-right text-indigo-300 font-medium">
                        {strat.win_rate.toFixed(1)}%
                      </td>
                      <td className="py-2.5 px-2 text-right">
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
                          {strat.average_r.toFixed(2)}R
                        </span>
                      </td>
                      <td className="py-2.5 px-2 text-center">
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded-full border font-bold uppercase ${
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
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
};
