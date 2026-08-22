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
    <section className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 sm:p-6 shadow-xl space-y-4 flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <div className="flex items-center gap-2.5">
            <h2 className="text-base font-bold text-white font-mono tracking-tight">
              Active Watchlist
            </h2>
            <span className="text-xs px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-300 border border-amber-500/30 font-mono font-medium">
              {setups.length} Monitored
            </span>
          </div>

          <button
            onClick={handleWatchlistClick}
            className="text-xs text-indigo-400 hover:text-indigo-300 font-mono font-semibold flex items-center gap-1 transition-colors cursor-pointer bg-slate-800/60 hover:bg-slate-800 px-2.5 py-1 rounded-lg border border-slate-700/60"
          >
            <span>View Watchlist</span>
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>

        {setups.length === 0 ? (
          <div className="py-6 px-4 text-center bg-slate-950/40 border border-slate-800/50 rounded-xl space-y-2 mt-4">
            <p className="text-sm font-semibold text-slate-200 font-mono">No setups are being monitored.</p>
            <p className="text-xs text-slate-400 max-w-sm mx-auto font-sans leading-relaxed">
              Save a daily recommendation to automatically track execution:
              <br />
              <span className="font-mono text-emerald-400 font-medium">Entry</span> →{' '}
              <span className="font-mono text-teal-300 font-medium">Target</span> →{' '}
              <span className="font-mono text-rose-400 font-medium">Stop</span> →{' '}
              <span className="font-mono text-indigo-300 font-medium">Realized R</span>
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-800/80 mt-4">
            <table className="w-full text-left border-collapse text-xs font-mono">
              <thead>
                <tr className="bg-slate-800/50 border-b border-slate-700/60 text-slate-400 uppercase tracking-wider text-[10px]">
                  <th className="py-2.5 px-3">Symbol</th>
                  <th className="py-2.5 px-2 text-center">Score</th>
                  <th className="py-2.5 px-2 text-right">Entry</th>
                  <th className="py-2.5 px-2 text-right">Stop</th>
                  <th className="py-2.5 px-2 text-right">Target</th>
                  <th className="py-2.5 px-2 text-center">Outcome</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50 text-slate-200">
                {setups.slice(0, 5).map((s) => (
                  <tr
                    key={s.id}
                    className="hover:bg-slate-800/40 transition-colors cursor-pointer"
                    onClick={() => handleStockClick(s.symbol)}
                  >
                    <td className="py-2.5 px-3">
                      <span className="font-extrabold text-slate-100 hover:text-emerald-400">
                        {s.symbol}
                      </span>
                    </td>
                    <td className="py-2.5 px-2 text-center font-bold">
                      {s.score ?? '-'}
                    </td>
                    <td className="py-2.5 px-2 text-right text-emerald-400 font-bold">
                      ₹{s.entry_price.toFixed(1)}
                    </td>
                    <td className="py-2.5 px-2 text-right text-rose-400 font-bold">
                      ₹{s.stop_loss.toFixed(1)}
                    </td>
                    <td className="py-2.5 px-2 text-right text-teal-300 font-bold">
                      ₹{s.target_price.toFixed(1)}
                    </td>
                    <td className="py-2.5 px-2 text-center">
                      <span className="text-[10px] px-1.5 py-0.5 rounded border bg-slate-800 text-slate-300 border-slate-700">
                        {s.outcome}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
};
