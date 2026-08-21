import React from 'react';
import type { ScanResult } from '../api/scanner';

interface StockDetailModalProps {
  stock: ScanResult | null;
  onClose: () => void;
}

export const StockDetailModal: React.FC<StockDetailModalProps> = ({
  stock,
  onClose,
}) => {
  if (!stock) return null;

  const isBuy = stock.signal === 'BUY';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fade-in">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl">
        {/* Header */}
        <div className="p-6 border-b border-slate-800 flex items-start justify-between bg-slate-800/40">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-2xl font-bold text-white font-mono">{stock.symbol}</h2>
              <span
                className={`text-xs px-2.5 py-1 rounded-md font-bold border ${
                  isBuy
                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                    : stock.signal === 'WATCH'
                    ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                    : stock.signal === 'ERROR'
                    ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                    : 'bg-slate-700/40 text-slate-300 border-slate-600/40'
                }`}
              >
                {stock.signal}
              </span>
            </div>
            <p className="text-sm text-slate-300 mt-1">{stock.company_name || stock.symbol}</p>
          </div>

          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 p-2 rounded-xl border border-slate-700 transition-colors cursor-pointer"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Trade Parameters Grid */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
              Trade Execution Parameters
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3.5">
                <span className="text-[11px] text-slate-400 block">Entry Price</span>
                <span className="text-base font-bold font-mono text-emerald-400">
                  {stock.entry_price !== null && stock.entry_price !== undefined ? `₹${stock.entry_price.toFixed(2)}` : '-'}
                </span>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3.5">
                <span className="text-[11px] text-slate-400 block">Stop Loss</span>
                <span className="text-base font-bold font-mono text-rose-400">
                  {stock.stop_loss !== null && stock.stop_loss !== undefined ? `₹${stock.stop_loss.toFixed(2)}` : '-'}
                </span>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3.5">
                <span className="text-[11px] text-slate-400 block">Target Price</span>
                <span className="text-base font-bold font-mono text-teal-300">
                  {stock.target_price !== null && stock.target_price !== undefined ? `₹${stock.target_price.toFixed(2)}` : '-'}
                </span>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3.5">
                <span className="text-[11px] text-slate-400 block">Risk : Reward</span>
                <span className="text-base font-bold font-mono text-amber-300">
                  {stock.risk_reward !== null && stock.risk_reward !== undefined ? `${stock.risk_reward}:1` : '-'}
                </span>
              </div>
            </div>
          </div>

          {/* Strategy Setup Reason */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
              Strategy Setup Breakdown
            </h3>
            <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-4 text-xs text-slate-300 leading-relaxed font-mono">
              {stock.reason || 'No setup breakdown specified.'}
            </div>
          </div>

          {/* Technical Metadata */}
          {stock.metadata && Object.keys(stock.metadata).length > 0 && (
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                Calculated Indicators
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
                {Object.entries(stock.metadata).map(([key, val]) => (
                  <div key={key} className="bg-slate-800/40 border border-slate-700/40 rounded-lg p-2.5 flex justify-between">
                    <span className="text-slate-400 font-mono">{key}</span>
                    <span className="font-semibold text-slate-200 font-mono">{String(val)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Error Message if Present */}
          {stock.error && (
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-rose-400 mb-2">
                Data Error Details
              </h3>
              <div className="bg-rose-950/20 border border-rose-500/30 rounded-xl p-3.5 text-xs text-rose-300">
                {stock.error}
              </div>
            </div>
          )}

          {/* Strategy Disclaimer */}
          <div className="bg-slate-800/30 border border-slate-700/40 rounded-xl p-3.5 text-[11px] text-slate-400">
            <span className="font-bold text-slate-300 block mb-0.5">Strategy Signals Notice</span>
            Quantitative technical indicator setup match generated by {stock.strategy_name} v{stock.strategy_version}. These signals represent pattern filters for research purposes and are not financial recommendations.
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/90 flex justify-end">
          <button
            onClick={onClose}
            className="bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-xs px-5 py-2.5 rounded-xl border border-slate-700 transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
