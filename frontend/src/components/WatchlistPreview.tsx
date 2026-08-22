import React from 'react';
import type { WatchlistSetup } from '../api/types';
import { useSafeNavigate } from '../utils/navigation';

interface WatchlistPreviewProps {
  setups: WatchlistSetup[];
  onOpenFullWatchlist?: () => void;
  onSelectStock?: (symbol: string) => void;
}

export const WatchlistPreview: React.FC<WatchlistPreviewProps> = ({
  setups,
  onOpenFullWatchlist,
  onSelectStock,
}) => {
  const navigate = useSafeNavigate();

  const handleStockClick = (symbol: string) => {
    if (onSelectStock) onSelectStock(symbol);
    navigate(`/stocks/${symbol}`);
  };

  const handleWatchlistClick = () => {
    if (onOpenFullWatchlist) onOpenFullWatchlist();
    navigate('/watchlist');
  };

  return (
    <section className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 sm:p-8 shadow-xl space-y-5">
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
        <div className="flex items-center gap-3">
          <h2 className="text-base font-bold text-white font-mono tracking-tight">
            Active Watchlist
          </h2>
          <span className="text-xs px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-300 border border-amber-500/30 font-mono font-medium">
            {setups.length} Monitored
          </span>
        </div>

        <button
          onClick={handleWatchlistClick}
          className="text-xs text-indigo-400 hover:text-indigo-300 font-mono font-semibold flex items-center gap-1.5 transition-colors cursor-pointer bg-slate-800/60 hover:bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-700/60"
        >
          <span>Full Watchlist</span>
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>

      {setups.length === 0 ? (
        <div className="py-8 text-center text-slate-400 text-xs font-mono bg-slate-950/40 border border-slate-800/50 rounded-xl p-4">
          No active setups currently saved in Watchlist. Save setups from scanner or recommendations to monitor execution outcomes.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-800/80">
          <table className="w-full text-left border-collapse text-xs font-mono">
            <thead>
              <tr className="bg-slate-800/50 border-b border-slate-700/60 text-slate-400 uppercase tracking-wider text-[11px]">
                <th className="py-3 px-4">Symbol</th>
                <th className="py-3 px-3 text-center">Score</th>
                <th className="py-3 px-3 text-right">Entry</th>
                <th className="py-3 px-3 text-right">Stop</th>
                <th className="py-3 px-3 text-right">Target</th>
                <th className="py-3 px-3 text-center">Outcome</th>
                <th className="py-3 px-3 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50 text-slate-200">
              {setups.slice(0, 5).map((s) => (
                <tr
                  key={s.id}
                  className="hover:bg-slate-800/40 transition-colors cursor-pointer"
                  onClick={() => handleStockClick(s.symbol)}
                >
                  <td className="py-3 px-4">
                    <span className="font-extrabold text-slate-100 font-mono hover:text-emerald-400">
                      {s.symbol}
                    </span>
                    <span className="block text-[10px] text-slate-500 truncate max-w-[120px]">
                      {s.strategy_name}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-center">
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 font-bold text-xs">
                      {s.score !== null && s.score !== undefined ? s.score : '-'}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-right text-emerald-400 font-bold">
                    ₹{s.entry_price.toFixed(2)}
                  </td>
                  <td className="py-3 px-3 text-right text-rose-400 font-bold">
                    ₹{s.stop_loss.toFixed(2)}
                  </td>
                  <td className="py-3 px-3 text-right text-teal-300 font-bold">
                    ₹{s.target_price.toFixed(2)}
                  </td>
                  <td className="py-3 px-3 text-center">
                    <span className="text-[10px] px-2 py-0.5 rounded border font-semibold bg-slate-800 text-slate-300 border-slate-700">
                      {s.outcome}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-center">
                    <span className="text-[10px] px-2 py-0.5 rounded-full border font-semibold bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
                      {s.status}
                    </span>
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
