import React from 'react';

interface HeaderProps {
  scanDate?: string;
  universe?: string;
  strategy?: string;
  strategyVersion?: string;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  scanDate,
  universe = 'NIFTY NEXT 50',
  strategy = 'EMA Pullback',
  strategyVersion = '1.0',
  onRefresh,
  isRefreshing,
}) => {
  return (
    <header className="bg-slate-900/80 border-b border-slate-800 backdrop-blur-md sticky top-0 z-20 px-4 sm:px-8 py-5">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        {/* Branding */}
        <div>
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center font-bold text-slate-950 text-xl shadow-lg shadow-emerald-500/20">
              SL
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-100 tracking-tight flex items-center gap-2">
                SwingLens
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                  Daily Scanner
                </span>
              </h1>
              <p className="text-xs text-slate-400">Daily Swing Trading Strategy Scanner</p>
            </div>
          </div>
        </div>

        {/* Scan Meta & Refresh Button */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 text-xs bg-slate-800/80 border border-slate-700/60 rounded-lg px-3 py-2 text-slate-300">
            <span className="text-slate-500">Date:</span>
            <span className="font-semibold text-slate-100">{scanDate || 'Latest'}</span>
          </div>

          <div className="flex items-center gap-2 text-xs bg-slate-800/80 border border-slate-700/60 rounded-lg px-3 py-2 text-slate-300">
            <span className="text-slate-500">Universe:</span>
            <span className="font-semibold text-slate-100">{universe}</span>
          </div>

          <div className="flex items-center gap-2 text-xs bg-slate-800/80 border border-slate-700/60 rounded-lg px-3 py-2 text-slate-300">
            <span className="text-slate-500">Strategy:</span>
            <span className="font-semibold text-emerald-400">{strategy} v{strategyVersion}</span>
          </div>

          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 disabled:opacity-50 text-white font-medium text-xs px-4 py-2 rounded-lg transition-all shadow-md shadow-emerald-900/20 cursor-pointer"
          >
            <svg
              className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`}
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
            {isRefreshing ? 'Scanning...' : 'Refresh Scan'}
          </button>
        </div>
      </div>
    </header>
  );
};
