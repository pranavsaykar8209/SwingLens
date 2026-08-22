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

  // Format date cleanly e.g. "2026-08-20" -> "Aug 20, 2026"
  const formattedDate = React.useMemo(() => {
    if (!scanDate || scanDate === 'Latest') return scanDate || 'Latest';
    try {
      const d = new Date(scanDate + 'T00:00:00');
      if (isNaN(d.getTime())) return scanDate;
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
      return scanDate;
    }
  }, [scanDate]);

  const navLinks = [
    { to: '/', label: 'Recommendations' },
    { to: '/watchlist', label: 'Watchlist' },
    { to: '/analytics', label: 'Strategy Analytics' },
  ];

  return (
    <>
      <div className="sticky top-5 z-40 w-full px-6 sm:px-10 pointer-events-none mb-8 sm:mb-10">
        <header className="pointer-events-auto w-full bg-slate-900/90 backdrop-blur-xl border border-slate-800/90 rounded-2xl px-6 sm:px-8 py-3.5 shadow-2xl shadow-slate-950/90 transition-all">
          <div className="w-full flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            {/* Brand + Clean Text Navigation */}
            <div className="flex items-center gap-7 sm:gap-9">
              <SafeLink to="/" className="flex items-center gap-3 group">
                <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-emerald-500 via-teal-400 to-cyan-400 flex items-center justify-center font-bold text-slate-950 text-sm shadow-md shadow-emerald-500/20 group-hover:scale-105 transition-transform">
                  SL
                </div>
                <span className="text-xl font-extrabold text-white tracking-tight font-sans hidden sm:inline">
                  SwingLens
                </span>
              </SafeLink>

              {/* Clean, Frameless Navigation Tabs */}
              <nav className="flex items-center gap-6 sm:gap-7">
                {navLinks.map((link) => {
                  const isActive =
                    link.to === '/'
                      ? location.pathname === '/' || location.pathname.startsWith('/stocks')
                      : location.pathname.startsWith(link.to);

                  return (
                    <SafeLink
                      key={link.to}
                      to={link.to}
                      className={`text-xs sm:text-sm font-sans font-medium transition-colors py-1 relative ${
                        isActive
                          ? 'text-emerald-400 font-semibold after:content-[""] after:absolute after:-bottom-1 after:left-0 after:w-full after:h-0.5 after:bg-emerald-400 after:rounded-full'
                          : 'text-slate-400 hover:text-slate-100'
                      }`}
                    >
                      {link.label}
                    </SafeLink>
                  );
                })}
              </nav>
            </div>

            {/* Compact Status Badges & Refresh Action */}
            <div className="flex items-center gap-3 text-xs font-mono text-slate-300">
              <div className="hidden sm:flex items-center gap-2 bg-slate-800/60 border border-slate-700/50 rounded-xl px-3.5 py-2">
                <span className="text-slate-400">{universe}</span>
                <span className="text-slate-600">•</span>
                <span className="text-slate-200 font-semibold">{formattedDate}</span>
              </div>

              <div className="flex items-center gap-2 bg-slate-800/60 border border-slate-700/50 rounded-xl px-3.5 py-2">
                <span
                  className={`inline-flex items-center gap-1.5 font-semibold ${
                    isCompleted ? 'text-emerald-400' : isRefreshing ? 'text-cyan-400 animate-pulse' : 'text-amber-400'
                  }`}
                >
                  <span className={`h-2 w-2 rounded-full ${isCompleted ? 'bg-emerald-400' : isRefreshing ? 'bg-cyan-400' : 'bg-amber-400'}`} />
                  {isRefreshing ? 'Scanning...' : isCompleted ? 'Scan Complete' : 'Ready'}
                </span>
              </div>

              {onRefresh && (
                <button
                  onClick={handleButtonClick}
                  disabled={isRefreshing}
                  title="Run / Refresh Today's Market Scan"
                  className="h-9 px-4 bg-slate-800 hover:bg-slate-700 active:bg-slate-800 disabled:opacity-50 text-slate-200 hover:text-white rounded-xl border border-slate-700/80 transition-all cursor-pointer flex items-center gap-2 shadow-sm"
                >
                  <svg
                    className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-emerald-400' : 'text-slate-300'}`}
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
                  <span className="text-xs font-sans font-semibold hidden md:inline">↻ Scan</span>
                </button>
              )}
            </div>
          </div>
        </header>
      </div>

      {/* Manual Override Confirmation Dialog */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fade-in">
          <div className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-amber-400">
              <div className="p-2 bg-amber-500/10 rounded-xl border border-amber-500/20">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h3 className="text-base font-bold text-white">Run Today's Scan Again?</h3>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Today's scan has already been completed. Run it again and refresh today's market candles?
            </p>

            <div className="flex justify-end gap-2.5 pt-2">
              <button
                onClick={() => setShowConfirmModal(false)}
                className="px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmRunAgain}
                className="px-3.5 py-2 rounded-xl text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 transition-all cursor-pointer border border-emerald-400/30 shadow-md shadow-emerald-950"
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
