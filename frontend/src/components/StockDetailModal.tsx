import React, { useState } from 'react';
import { fetchSingleStockBacktest, type ScanResult, type SingleStockBacktestResult } from '../api/scanner';

interface StockDetailModalProps {
  stock: ScanResult | null;
  onClose: () => void;
}

export const StockDetailModal: React.FC<StockDetailModalProps> = ({
  stock,
  onClose,
}) => {
  const [loadingBacktest, setLoadingBacktest] = useState(false);
  const [backtestResult, setBacktestResult] = useState<SingleStockBacktestResult | null>(null);
  const [backtestError, setBacktestError] = useState<string | null>(null);

  if (!stock) return null;

  const isBuy = stock.signal === 'BUY';

  const handleRunBacktest = async () => {
    setLoadingBacktest(true);
    setBacktestError(null);
    try {
      const res = await fetchSingleStockBacktest(stock.symbol, stock.strategy_name || 'ema_pullback');
      setBacktestResult(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to run single-stock backtest.';
      setBacktestError(msg);
    } finally {
      setLoadingBacktest(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fade-in">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto shadow-2xl flex flex-col">
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

          <div className="flex items-center gap-3">
            <button
              onClick={handleRunBacktest}
              disabled={loadingBacktest}
              className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-xs px-4 py-2.5 rounded-xl border border-indigo-400/30 transition-all cursor-pointer flex items-center gap-2 shadow-lg shadow-indigo-600/20"
            >
              {loadingBacktest ? (
                <>
                  <svg className="animate-spin -ml-1 mr-1 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Running Backtest...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Backtest This Stock
                </>
              )}
            </button>

            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 p-2 rounded-xl border border-slate-700 transition-colors cursor-pointer"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6 flex-1">
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

          {/* Single-Stock Backtest Section */}
          {backtestError && (
            <div className="bg-rose-950/30 border border-rose-500/40 rounded-xl p-4 text-xs text-rose-300">
              <span className="font-bold block mb-1">Backtest Error:</span>
              {backtestError}
            </div>
          )}

          {backtestResult && (
            <div className="space-y-6 pt-4 border-t border-slate-800 animate-fade-in">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-slate-800/40 border border-slate-700/60 rounded-xl p-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-bold text-white font-mono">
                      {backtestResult.symbol} Historical Backtest
                    </h3>
                    <span className="text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-2 py-0.5 rounded">
                      {backtestResult.strategy_name} v{backtestResult.strategy_version}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1 font-mono">
                    Period: <span className="text-slate-200">{backtestResult.start_date}</span> → <span className="text-slate-200">{backtestResult.end_date}</span>
                  </p>
                </div>
                <div className="text-xs text-slate-400 italic">
                  Deterministic Policy: Conservative OHLC ambiguity resolution
                </div>
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3">
                  <span className="text-slate-400 block text-[11px]">Total Trades</span>
                  <span className="text-lg font-bold font-mono text-white">{backtestResult.total_trades}</span>
                </div>
                <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3">
                  <span className="text-slate-400 block text-[11px]">Win / Loss</span>
                  <span className="text-lg font-bold font-mono text-emerald-400">
                    {backtestResult.winning_trades} <span className="text-slate-500">/</span> <span className="text-rose-400">{backtestResult.losing_trades}</span>
                  </span>
                </div>
                <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3">
                  <span className="text-slate-400 block text-[11px]">Win Rate</span>
                  <span className="text-lg font-bold font-mono text-indigo-300">{backtestResult.win_rate.toFixed(1)}%</span>
                </div>
                <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3">
                  <span className="text-slate-400 block text-[11px]">Profit Factor</span>
                  <span className="text-lg font-bold font-mono text-amber-300">{backtestResult.profit_factor.toFixed(2)}</span>
                </div>
                <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3">
                  <span className="text-slate-400 block text-[11px]">Average Win</span>
                  <span className="text-base font-bold font-mono text-emerald-400">+{backtestResult.average_win_percent.toFixed(2)}%</span>
                </div>
                <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3">
                  <span className="text-slate-400 block text-[11px]">Average Loss</span>
                  <span className="text-base font-bold font-mono text-rose-400">{backtestResult.average_loss_percent.toFixed(2)}%</span>
                </div>
                <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3">
                  <span className="text-slate-400 block text-[11px]">Average Trade</span>
                  <span className={`text-base font-bold font-mono ${backtestResult.average_trade_percent >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {backtestResult.average_trade_percent >= 0 ? '+' : ''}{backtestResult.average_trade_percent.toFixed(2)}%
                  </span>
                </div>
                <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3">
                  <span className="text-slate-400 block text-[11px]">Max Drawdown</span>
                  <span className="text-base font-bold font-mono text-rose-400">{backtestResult.max_drawdown_percent.toFixed(2)}%</span>
                </div>
                <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3">
                  <span className="text-slate-400 block text-[11px]">Avg Holding</span>
                  <span className="text-base font-bold font-mono text-slate-200">{backtestResult.average_holding_days.toFixed(1)} days</span>
                </div>
                <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3">
                  <span className="text-slate-400 block text-[11px]">Max Holding</span>
                  <span className="text-base font-bold font-mono text-slate-200">{backtestResult.maximum_holding_days} days</span>
                </div>
                <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3">
                  <span className="text-slate-400 block text-[11px]">Average R</span>
                  <span className="text-base font-bold font-mono text-amber-300">{backtestResult.average_r_multiple.toFixed(2)}</span>
                </div>
                <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3">
                  <span className="text-slate-400 block text-[11px]">Total R</span>
                  <span className={`text-base font-bold font-mono ${backtestResult.total_r >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {backtestResult.total_r >= 0 ? '+' : ''}{backtestResult.total_r.toFixed(2)}
                  </span>
                </div>
              </div>

              {/* Trades Log Table */}
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
                  Historical Trades ({backtestResult.trades.length})
                </h4>
                {backtestResult.trades.length === 0 ? (
                  <div className="bg-slate-800/30 border border-slate-700/40 rounded-xl p-4 text-xs text-slate-400 text-center italic">
                    No completed trades generated by strategy for this stock.
                  </div>
                ) : (
                  <div className="overflow-x-auto rounded-xl border border-slate-800">
                    <table className="w-full text-left text-xs font-mono">
                      <thead className="bg-slate-800/80 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-700/60">
                        <tr>
                          <th className="py-2.5 px-3">Signal</th>
                          <th className="py-2.5 px-3">Entry</th>
                          <th className="py-2.5 px-3">Entry Price</th>
                          <th className="py-2.5 px-3">Stop Loss</th>
                          <th className="py-2.5 px-3">Target</th>
                          <th className="py-2.5 px-3">Exit</th>
                          <th className="py-2.5 px-3">Exit Price</th>
                          <th className="py-2.5 px-3">Result</th>
                          <th className="py-2.5 px-3 text-right">P&L %</th>
                          <th className="py-2.5 px-3 text-right">R-Mult</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 bg-slate-900/60">
                        {backtestResult.trades.map((t, idx) => {
                          const isWin = t.pnl_percent > 0;
                          return (
                            <tr key={t.trade_id || idx} className="hover:bg-slate-800/40 transition-colors">
                              <td className="py-2 px-3 text-slate-400">{t.signal_date || t.entry_date}</td>
                              <td className="py-2 px-3 text-slate-300">{t.entry_date}</td>
                              <td className="py-2 px-3 text-emerald-400">₹{t.entry_price.toFixed(2)}</td>
                              <td className="py-2 px-3 text-rose-400">{t.stop_loss ? `₹${t.stop_loss.toFixed(2)}` : '-'}</td>
                              <td className="py-2 px-3 text-teal-300">{t.target_price ? `₹${t.target_price.toFixed(2)}` : '-'}</td>
                              <td className="py-2 px-3 text-slate-300">{t.exit_date}</td>
                              <td className="py-2 px-3 text-slate-200">₹{t.exit_price.toFixed(2)}</td>
                              <td className="py-2 px-3">
                                <span
                                  className={`text-[10px] px-2 py-0.5 rounded font-bold border ${
                                    t.exit_reason === 'TARGET'
                                      ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                                      : t.exit_reason === 'STOP_LOSS'
                                      ? 'bg-rose-500/20 text-rose-300 border-rose-500/30'
                                      : 'bg-slate-700/40 text-slate-300 border-slate-600/40'
                                  }`}
                                >
                                  {t.exit_reason}
                                </span>
                              </td>
                              <td className={`py-2 px-3 text-right font-bold ${isWin ? 'text-emerald-400' : 'text-rose-400'}`}>
                                {isWin ? '+' : ''}{t.pnl_percent.toFixed(2)}%
                              </td>
                              <td className={`py-2 px-3 text-right font-bold ${t.r_multiple && t.r_multiple > 0 ? 'text-emerald-400' : t.r_multiple && t.r_multiple < 0 ? 'text-rose-400' : 'text-slate-400'}`}>
                                {t.r_multiple !== null && t.r_multiple !== undefined ? `${t.r_multiple > 0 ? '+' : ''}${t.r_multiple.toFixed(2)}` : '-'}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
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

