import React, { useState } from 'react';
import { SafeLink, useSafeLocation } from '../utils/navigation';

interface HeaderProps {
  scanDate?: string;
  universe?: string;
  strategy?: string;
  strategyVersion?: string;
  scanStatus?: string;
  onRefresh?: (force?: boolean) => void;
  isAlreadyCompleted?: boolean;
  isRefreshing?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  scanDate,
  universe = 'NIFTY NEXT 50',
  strategy,
  strategyVersion,
  scanStatus,
  onRefresh,
  isAlreadyCompleted = false,
  isRefreshing = false,
}) => {
  const [showConfirmModal, setShowConfirmModal] = useState<boolean>(false);
  const location = useSafeLocation();

  const handleButtonClick = () => {
    if (!onRefresh) return;
    if (isAlreadyCompleted) {
      setShowConfirmModal(true);
    } else {
      onRefresh(false);
    }
  };

  const handleConfirmRunAgain = () => {
    setShowConfirmModal(false);
    if (onRefresh) onRefresh(true);
  };

  const isCompleted = isAlreadyCompleted || scanStatus === 'COMPLETED';

  const navLinks = [
    { to: '/', label: 'Recommendations' },
    { to: '/watchlist', label: 'Watchlist' },
    { to: '/analytics', label: 'Strategy Analytics' },
  ];

  return (
    <>
      <header className="bg-slate-900/90 border-b border-slate-800/80 backdrop-blur-xl sticky top-0 z-30 w-full px-6 sm:px-10 py-3.5 shadow-xl">
        <div className="w-full flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          {/* Branding & Navigation Links */}
          <div className="flex flex-wrap items-center gap-6">
            <SafeLink to="/" className="flex items-center gap-3.5 group">
              <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-emerald-500 via-teal-400 to-cyan-400 flex items-center justify-center font-bold text-slate-950 text-xl shadow-lg shadow-emerald-500/25 group-hover:scale-105 transition-transform">
                SL
              </div>
              <div>
                <h1 className="text-2xl font-extrabold text-white tracking-tight flex items-center gap-2.5">
                  SwingLens
                  <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 uppercase tracking-wide">
                    Trading Research
                  </span>
                </h1>
                <p className="text-xs text-slate-400 font-medium">Quantitative Swing Trading Strategy & Market Analytics</p>
              </div>
            </SafeLink>

            {/* Navigation Tabs */}
            <nav className="flex items-center gap-1.5 bg-slate-950/60 p-1 rounded-xl border border-slate-800">
              {navLinks.map((link) => {
                const isActive =
                  link.to === '/'
                    ? location.pathname === '/' || location.pathname.startsWith('/stocks')
                    : location.pathname.startsWith(link.to);

                return (
                  <SafeLink
                    key={link.to}
                    to={link.to}
                    className={`px-3.5 py-1.5 rounded-lg text-xs font-mono font-semibold transition-all ${
                      isActive
                        ? 'bg-slate-800 text-emerald-400 shadow-sm border border-slate-700/80'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                    }`}
                  >
                    {link.label}
                  </SafeLink>
                );
              })}
            </nav>
          </div>

          {/* Scan Meta Badges & Action Button */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2 text-xs bg-slate-800/90 border border-slate-700/60 rounded-xl px-3.5 py-2 text-slate-300 font-mono shadow-sm">
              <span className="text-slate-400">Date:</span>
              <span className="font-bold text-slate-100">{scanDate || 'Latest'}</span>
            </div>

            <div className="flex items-center gap-2 text-xs bg-slate-800/90 border border-slate-700/60 rounded-xl px-3.5 py-2 text-slate-300 font-mono shadow-sm">
              <span className="text-slate-400">Universe:</span>
              <span className="font-bold text-slate-100">{universe}</span>
            </div>

            {strategy ? (
              <div className="flex items-center gap-2 text-xs bg-slate-800/90 border border-slate-700/60 rounded-xl px-3.5 py-2 text-slate-300 font-mono shadow-sm">
                <span className="text-slate-400">Strategy:</span>
                <span className="font-bold text-emerald-400">{strategy} {strategyVersion ? `v${strategyVersion}` : ''}</span>
              </div>
            ) : null}

            <div className="flex items-center gap-2 text-xs bg-slate-800/90 border border-slate-700/60 rounded-xl px-3.5 py-2 text-slate-300 font-mono shadow-sm">
              <span className="text-slate-400">Status:</span>
              <span
                className={`font-bold inline-flex items-center gap-1.5 ${
                  isCompleted ? 'text-emerald-400' : isRefreshing ? 'text-cyan-400 animate-pulse' : 'text-amber-400'
                }`}
              >
                <span className={`h-1.5 w-1.5 rounded-full ${isCompleted ? 'bg-emerald-400' : isRefreshing ? 'bg-cyan-400' : 'bg-amber-400'}`} />
                {isRefreshing ? 'RUNNING' : scanStatus || (isCompleted ? 'COMPLETED' : 'READY')}
              </span>
            </div>

            {onRefresh && (
              <button
                onClick={handleButtonClick}
                disabled={isRefreshing}
                className="flex items-center gap-2 bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 active:from-emerald-700 active:to-teal-600 disabled:opacity-50 text-white font-semibold text-xs px-4 py-2.5 rounded-xl transition-all shadow-lg shadow-emerald-900/30 cursor-pointer border border-emerald-400/30"
              >
                <svg
                  className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
                {isRefreshing ? "Running Today's Scan..." : "↻ Run Today's Scan"}
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Manual Override Confirmation Dialog */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fade-in">
          <div className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-amber-400">
              <div className="p-2.5 bg-amber-500/10 rounded-xl border border-amber-500/20">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h3 className="text-lg font-bold text-white">Run Today's Scan Again?</h3>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Today's scan has already been completed. Run it again and refresh today's market data?
            </p>

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setShowConfirmModal(false)}
                className="px-4 py-2.5 rounded-xl text-xs font-semibold text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmRunAgain}
                className="px-4 py-2.5 rounded-xl text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-900/30 transition-all cursor-pointer border border-emerald-400/30"
              >
                Run Again
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
