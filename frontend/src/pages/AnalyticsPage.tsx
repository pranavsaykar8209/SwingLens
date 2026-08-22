import React, { useEffect, useState } from 'react';
import { fetchStrategyAnalytics, type StrategyQualityMetrics } from '../api/scanner';
import { Header } from '../components/Header';

export const AnalyticsPage: React.FC = () => {
  const [strategies, setStrategies] = useState<StrategyQualityMetrics[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadAnalytics() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetchStrategyAnalytics();
        setStrategies(res.strategies || []);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to load strategy quality analytics.';
        setError(msg);
      } finally {
        setLoading(false);
      }
    }
    loadAnalytics();
  }, []);

  const activeStrategies = strategies.filter(
    (s) => s.strategy_name.toLowerCase() !== 'passthrough hold strategy'
  );

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans antialiased">
      <Header onRefresh={() => {}} isRefreshing={false} />

      <main className="w-full px-6 sm:px-10 py-8 space-y-8">
        <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 sm:p-8 shadow-xl">
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white font-mono tracking-tight flex items-center gap-3">
            Strategy Historical Quality Analytics
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 font-mono font-medium">
              5 Strategies
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Empirical historical performance metrics and deterministic quality classifications across representative NIFTY Next 50 stock sample
          </p>
        </div>

        {loading && (
          <div className="flex flex-col items-center justify-center py-24 text-center bg-slate-900/40 border border-slate-800/80 rounded-2xl space-y-3 shadow-xl">
            <div className="w-10 h-10 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin mb-2" />
            <h3 className="text-base font-semibold text-slate-200 font-mono">Calculating Strategy Performance...</h3>
          </div>
        )}

        {error && (
          <div className="p-6 bg-rose-950/20 border border-rose-500/30 rounded-2xl text-xs text-rose-300 font-mono text-center">
            {error}
          </div>
        )}

        {!loading && !error && (
          <div className="space-y-6">
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 sm:p-8 shadow-xl space-y-4">
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 font-mono">
                Comparative Performance Summary
              </h2>

              <div className="overflow-x-auto rounded-xl border border-slate-800/80">
                <table className="w-full text-left border-collapse text-xs font-mono">
                  <thead>
                    <tr className="bg-slate-800/50 border-b border-slate-700/60 text-slate-400 uppercase tracking-wider text-[11px]">
                      <th className="py-3.5 px-4">Strategy</th>
                      <th className="py-3.5 px-3 text-center">Trades</th>
                      <th className="py-3.5 px-3 text-right">Win Rate</th>
                      <th className="py-3.5 px-3 text-right">Avg R</th>
                      <th className="py-3.5 px-3 text-right">Total R</th>
                      <th className="py-3.5 px-3 text-right">Profit Factor</th>
                      <th className="py-3.5 px-3 text-right">Max DD</th>
                      <th className="py-3.5 px-3 text-right">Avg Holding</th>
                      <th className="py-3.5 px-3 text-right">Target Rate</th>
                      <th className="py-3.5 px-3 text-right">Stop Rate</th>
                      <th className="py-3.5 px-3 text-center">Classification</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/50 text-slate-200">
                    {activeStrategies.map((strat) => {
                      const isPositive = strat.classification === 'POSITIVE';
                      const isNegative = strat.classification === 'NEGATIVE';

                      return (
                        <tr key={strat.strategy_name} className="hover:bg-slate-800/40 transition-colors">
                          <td className="py-3.5 px-4">
                            <span className="font-extrabold text-slate-100 text-sm">{strat.strategy_name}</span>
                            <span className="text-[10px] text-slate-500 ml-1.5">v{strat.strategy_version}</span>
                          </td>
                          <td className="py-3.5 px-3 text-center font-bold text-white">{strat.trades}</td>
                          <td className="py-3.5 px-3 text-right font-bold text-indigo-300">
                            {strat.win_rate.toFixed(1)}%
                          </td>
                          <td className="py-3.5 px-3 text-right">
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
                          <td className="py-3.5 px-3 text-right">
                            <span
                              className={`font-bold ${
                                strat.total_r > 0
                                  ? 'text-emerald-400'
                                  : strat.total_r < 0
                                  ? 'text-rose-400'
                                  : 'text-slate-400'
                              }`}
                            >
                              {strat.total_r > 0 ? '+' : ''}
                              {strat.total_r.toFixed(2)}R
                            </span>
                          </td>
                          <td className="py-3.5 px-3 text-right font-bold">
                            <span className={strat.profit_factor >= 1.0 ? 'text-emerald-400' : 'text-rose-400'}>
                              {strat.profit_factor.toFixed(2)}
                            </span>
                          </td>
                          <td className="py-3.5 px-3 text-right text-rose-400 font-bold">
                            {strat.max_drawdown.toFixed(1)}%
                          </td>
                          <td className="py-3.5 px-3 text-right text-slate-200">
                            {strat.average_holding_days.toFixed(1)}d
                          </td>
                          <td className="py-3.5 px-3 text-right text-teal-300">
                            {strat.target_hit_rate.toFixed(1)}%
                          </td>
                          <td className="py-3.5 px-3 text-right text-rose-400">
                            {strat.stop_hit_rate.toFixed(1)}%
                          </td>
                          <td className="py-3.5 px-3 text-center">
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
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Classification Rules Reference Card */}
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 shadow-xl space-y-3 font-mono text-xs">
              <h3 className="text-slate-300 font-bold uppercase tracking-wider text-[11px]">
                Deterministic Classification Rules
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-slate-400">
                <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-700/50">
                  <span className="text-emerald-400 font-bold block mb-1">POSITIVE</span>
                  <span>Trades &ge; 10, Total R &gt; 0, Profit Factor &ge; 1.0, Avg R &gt; 0</span>
                </div>
                <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-700/50">
                  <span className="text-rose-400 font-bold block mb-1">NEGATIVE</span>
                  <span>Trades &ge; 10, Total R &lt; 0, Profit Factor &lt; 1.0, Avg R &lt; 0</span>
                </div>
                <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-700/50">
                  <span className="text-slate-300 font-bold block mb-1">NEUTRAL</span>
                  <span>Trades &ge; 10, mixed historical performance metrics</span>
                </div>
                <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-700/50">
                  <span className="text-amber-400 font-bold block mb-1">INSUFFICIENT_DATA</span>
                  <span>Trades &lt; 10 (sample size too small)</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};
