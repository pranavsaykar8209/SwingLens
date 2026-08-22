import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchActiveWatchlist, type WatchlistSetup } from '../api/scanner';
import { Header } from '../components/Header';

export const WatchlistPage: React.FC = () => {
  const navigate = useNavigate();
  const [setups, setSetups] = useState<WatchlistSetup[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  useEffect(() => {
    async function loadWatchlist() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchActiveWatchlist();
        setSetups(data);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to load watchlist setups.';
        setError(msg);
      } finally {
        setLoading(false);
      }
    }
    loadWatchlist();
  }, []);

  const filteredSetups =
    statusFilter === 'ALL'
      ? setups
      : setups.filter((s) => s.status.toUpperCase() === statusFilter.toUpperCase());

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans antialiased">
      <Header onRefresh={() => {}} isRefreshing={false} />

      <main className="w-full px-6 sm:px-10 py-8 space-y-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 sm:p-8 shadow-xl">
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white font-mono tracking-tight flex items-center gap-3">
              Watchlist & Outcome Tracking
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 font-mono font-medium">
                {setups.length} Setups
              </span>
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Monitored trading setups with automated daily candle entry/stop/target resolution and R-multiple tracking
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <label htmlFor="watchlist-status-filter" className="text-xs text-slate-400 font-mono font-medium whitespace-nowrap">
              Filter Status:
            </label>
            <select
              id="watchlist-status-filter"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-800/90 border border-slate-700 text-slate-100 text-xs font-mono rounded-xl px-3.5 py-2 focus:outline-none focus:ring-2 focus:ring-amber-500/40 cursor-pointer shadow-sm"
            >
              <option value="ALL">All Statuses</option>
              <option value="ACTIVE">ACTIVE</option>
              <option value="TRIGGERED">TRIGGERED</option>
              <option value="EXPIRED">EXPIRED</option>
              <option value="CANCELLED">CANCELLED</option>
            </select>
          </div>
        </div>

        {loading && (
          <div className="flex flex-col items-center justify-center py-24 text-center bg-slate-900/40 border border-slate-800/80 rounded-2xl space-y-3 shadow-xl">
            <div className="w-10 h-10 border-4 border-amber-500/30 border-t-amber-500 rounded-full animate-spin mb-2" />
            <h3 className="text-base font-semibold text-slate-200 font-mono">Loading Watchlist Setups...</h3>
          </div>
        )}

        {error && (
          <div className="p-6 bg-rose-950/20 border border-rose-500/30 rounded-2xl text-xs text-rose-300 font-mono text-center">
            {error}
          </div>
        )}

        {!loading && !error && (
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 sm:p-8 shadow-xl">
            <div className="overflow-x-auto rounded-xl border border-slate-800/80">
              <table className="w-full text-left border-collapse text-xs font-mono">
                <thead>
                  <tr className="bg-slate-800/50 border-b border-slate-700/60 text-slate-400 uppercase tracking-wider text-[11px]">
                    <th className="py-3.5 px-4">Symbol</th>
                    <th className="py-3.5 px-4">Strategy</th>
                    <th className="py-3.5 px-3 text-center">Score</th>
                    <th className="py-3.5 px-3 text-right">Entry</th>
                    <th className="py-3.5 px-3 text-right">Stop Loss</th>
                    <th className="py-3.5 px-3 text-right">Target</th>
                    <th className="py-3.5 px-3 text-center">R:R</th>
                    <th className="py-3.5 px-3 text-center">Outcome</th>
                    <th className="py-3.5 px-3 text-center">Realized R</th>
                    <th className="py-3.5 px-3 text-center">Status</th>
                    <th className="py-3.5 px-4 text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50 text-slate-200">
                  {filteredSetups.length === 0 ? (
                    <tr>
                      <td colSpan={11} className="py-12 text-center text-slate-400 font-sans">
                        No setups found in watchlist.
                      </td>
                    </tr>
                  ) : (
                    filteredSetups.map((s) => (
                      <tr
                        key={s.id}
                        className="hover:bg-slate-800/40 transition-colors cursor-pointer"
                        onClick={() => navigate(`/stocks/${s.symbol}`)}
                      >
                        <td className="py-3.5 px-4">
                          <span className="font-extrabold text-slate-100 text-sm hover:text-emerald-400 transition-colors">
                            {s.symbol}
                          </span>
                          {s.company_name && (
                            <span className="block text-[11px] text-slate-400 font-sans truncate max-w-[140px]">
                              {s.company_name}
                            </span>
                          )}
                        </td>
                        <td className="py-3.5 px-4">
                          <span className="text-slate-300 font-medium">{s.strategy_name}</span>
                          <span className="text-[10px] text-slate-500 ml-1">v{s.strategy_version}</span>
                        </td>
                        <td className="py-3.5 px-3 text-center">
                          <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 font-bold">
                            {s.score !== null && s.score !== undefined ? s.score : '-'}
                          </span>
                        </td>
                        <td className="py-3.5 px-3 text-right text-emerald-400 font-bold">
                          ₹{s.entry_price.toFixed(2)}
                        </td>
                        <td className="py-3.5 px-3 text-right text-rose-400 font-bold">
                          ₹{s.stop_loss.toFixed(2)}
                        </td>
                        <td className="py-3.5 px-3 text-right text-teal-300 font-bold">
                          ₹{s.target_price.toFixed(2)}
                        </td>
                        <td className="py-3.5 px-3 text-center text-amber-300 font-bold">
                          {s.risk_reward.toFixed(1)}:1
                        </td>
                        <td className="py-3.5 px-3 text-center">
                          <span
                            className={`text-[10px] px-2 py-0.5 rounded border font-semibold ${
                              s.outcome === 'TARGET_HIT'
                                ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                                : s.outcome === 'STOP_HIT'
                                ? 'bg-rose-500/15 text-rose-300 border-rose-500/30'
                                : 'bg-slate-800 text-slate-300 border-slate-700'
                            }`}
                          >
                            {s.outcome}
                          </span>
                        </td>
                        <td className="py-3.5 px-3 text-center">
                          {s.realized_r !== null && s.realized_r !== undefined ? (
                            <span
                              className={`font-bold ${
                                s.realized_r > 0
                                  ? 'text-emerald-400'
                                  : s.realized_r < 0
                                  ? 'text-rose-400'
                                  : 'text-slate-400'
                              }`}
                            >
                              {s.realized_r > 0 ? '+' : ''}
                              {s.realized_r.toFixed(2)}R
                            </span>
                          ) : (
                            <span className="text-slate-500">-</span>
                          )}
                        </td>
                        <td className="py-3.5 px-3 text-center">
                          <span className="text-[10px] px-2.5 py-0.5 rounded-full border font-semibold bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
                            {s.status}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/stocks/${s.symbol}`);
                            }}
                            className="text-xs px-3 py-1.5 rounded-lg border bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white border-slate-700 font-semibold cursor-pointer transition-all"
                          >
                            Chart
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};
