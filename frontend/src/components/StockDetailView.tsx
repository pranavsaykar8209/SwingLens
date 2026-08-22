import React, { useState } from 'react';
import { fetchSingleStockBacktest, type ScanResult, type SingleStockBacktestResult } from '../api/scanner';
import { StockPriceChart } from './StockPriceChart';

interface StockDetailViewProps {
  stock: ScanResult;
  onBack: () => void;
}

export const StockDetailView: React.FC<StockDetailViewProps> = ({
  stock,
  onBack,
}) => {
  const [loadingBacktest, setLoadingBacktest] = useState(false);
  const [backtestResult, setBacktestResult] = useState<SingleStockBacktestResult | null>(null);
  const [backtestError, setBacktestError] = useState<string | null>(null);

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
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans antialiased pb-16">
      {/* Top Navigation Bar - Full Width */}
      <div className="bg-slate-900/90 border-b border-slate-800/80 backdrop-blur-xl sticky top-0 z-40 w-full px-6 sm:px-10 py-4 shadow-xl">
        <div className="w-full flex items-center justify-between">
          <button
            onClick={onBack}
            className="group flex items-center gap-2.5 text-xs font-semibold text-slate-300 hover:text-white bg-slate-800/90 hover:bg-slate-800 px-4 py-2.5 rounded-xl border border-slate-700/70 transition-all cursor-pointer shadow-sm"
          >
            <svg className="w-4 h-4 transition-transform group-hover:-translate-x-1 text-slate-400 group-hover:text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Scanner Dashboard
          </button>

          <button
            onClick={handleRunBacktest}
            disabled={loadingBacktest}
            className="bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 disabled:opacity-50 text-white font-semibold text-xs px-5 py-2.5 rounded-xl border border-indigo-400/30 transition-all cursor-pointer flex items-center gap-2.5 shadow-lg shadow-indigo-600/25"
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
        </div>
      </div>

      {/* Main Stock Detail Page Container - Full Width */}
      <main className="w-full px-6 sm:px-10 py-8 space-y-8">
        {/* Title Banner Header */}
        <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 sm:p-8 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xl">
          <div>
            <div className="flex items-center gap-3.5">
              <h1 className="text-3xl sm:text-4xl font-extrabold text-white font-mono tracking-tight">{stock.symbol}</h1>
              <span
                className={`text-xs px-3.5 py-1 rounded-md font-extrabold border ${
                  isBuy
                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 shadow-sm shadow-emerald-500/10'
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
            <p className="text-sm sm:text-base text-slate-300 font-medium mt-1.5">{stock.company_name || stock.symbol}</p>
          </div>

          <div className="text-xs text-slate-400 font-mono bg-slate-800/60 border border-slate-700/60 rounded-xl px-5 py-3 flex items-center gap-6 shadow-inner">
            <div>
              <span className="text-slate-500 block text-[10px] tracking-wider uppercase font-semibold">SCANNER DATE</span>
              <span className="text-slate-100 font-bold text-sm">{stock.signal_date || 'Latest'}</span>
            </div>
            <div className="h-7 w-px bg-slate-700/60" />
            <div>
              <span className="text-slate-500 block text-[10px] tracking-wider uppercase font-semibold">STRATEGY</span>
              <span className="text-emerald-400 font-bold text-sm">{stock.strategy_name} v{stock.strategy_version}</span>
            </div>
          </div>
        </div>

        {/* 1. Trade Execution Parameters */}
        <section className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 sm:p-8 shadow-xl">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4 font-mono">
            Trade Execution Parameters
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4 sm:p-5 shadow-sm">
              <span className="text-xs text-slate-400 block mb-1 font-medium">Entry Price</span>
              <span className="text-2xl font-extrabold font-mono text-emerald-400">
                {stock.entry_price !== null && stock.entry_price !== undefined ? `₹${stock.entry_price.toFixed(2)}` : '-'}
              </span>
            </div>
            <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4 sm:p-5 shadow-sm">
              <span className="text-xs text-slate-400 block mb-1 font-medium">Stop Loss</span>
              <span className="text-2xl font-extrabold font-mono text-rose-400">
                {stock.stop_loss !== null && stock.stop_loss !== undefined ? `₹${stock.stop_loss.toFixed(2)}` : '-'}
              </span>
            </div>
            <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4 sm:p-5 shadow-sm">
              <span className="text-xs text-slate-400 block mb-1 font-medium">Target Price</span>
              <span className="text-2xl font-extrabold font-mono text-teal-300">
                {stock.target_price !== null && stock.target_price !== undefined ? `₹${stock.target_price.toFixed(2)}` : '-'}
              </span>
            </div>
            <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4 sm:p-5 shadow-sm">
              <span className="text-xs text-slate-400 block mb-1 font-medium">Risk : Reward</span>
              <span className="text-2xl font-extrabold font-mono text-amber-300">
                {stock.risk_reward !== null && stock.risk_reward !== undefined ? `${stock.risk_reward}:1` : '-'}
              </span>
            </div>
          </div>
        </section>

        {/* 2. Full-Width Historical Price Chart */}
        <section className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 sm:p-8 shadow-xl">
          <StockPriceChart stock={stock} backtestTrades={backtestResult?.trades || []} />
        </section>

        {/* 3. Strategy Setup Breakdown */}
        <section className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 sm:p-8 shadow-xl">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 font-mono">
            Strategy Setup Breakdown
          </h2>
          <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-5 text-xs sm:text-sm text-slate-200 leading-relaxed font-mono">
            {stock.reason || 'No setup breakdown specified.'}
          </div>
        </section>

        {/* 4. Calculated Indicators */}
        {stock.metadata && Object.keys(stock.metadata).length > 0 && (
          <section className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 sm:p-8 shadow-xl">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 font-mono">
              Calculated Technical Indicators
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 text-xs">
              {Object.entries(stock.metadata).map(([key, val]) => (
                <div key={key} className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-3.5 flex justify-between items-center">
                  <span className="text-slate-400 font-mono">{key}</span>
                  <span className="font-bold text-slate-100 font-mono text-sm">{String(val)}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 5. Backtest Results Section */}
        {backtestError && (
          <div className="bg-rose-950/30 border border-rose-500/40 rounded-2xl p-5 text-xs text-rose-300 font-mono shadow-lg">
            <span className="font-bold block mb-1">Backtest Execution Error:</span>
            {backtestError}
          </div>
        )}

        {backtestResult && (
          <section className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 sm:p-8 space-y-6 animate-fade-in shadow-xl">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-800/50 border border-slate-700/60 rounded-xl p-5">
              <div>
                <div className="flex items-center gap-3">
                  <h3 className="text-lg font-bold text-white font-mono">
                    {backtestResult.symbol} Historical Backtest Performance
                  </h3>
                  <span className="text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-2.5 py-0.5 rounded-md">
                    {backtestResult.strategy_name} v{backtestResult.strategy_version}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-1 font-mono">
                  Historical Period: <span className="text-slate-200">{backtestResult.start_date}</span> → <span className="text-slate-200">{backtestResult.end_date}</span>
                </p>
              </div>
              <div className="text-xs text-slate-400 italic font-mono">
                Policy: Conservative OHLC Ambiguity Resolution
              </div>
            </div>

            {/* Performance Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3.5 text-xs">
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
                <span className="text-slate-400 block text-[11px] font-medium">Total Trades</span>
                <span className="text-xl font-bold font-mono text-white">{backtestResult.total_trades}</span>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
                <span className="text-slate-400 block text-[11px] font-medium">Winning / Losing</span>
                <span className="text-xl font-bold font-mono text-emerald-400">
                  {backtestResult.winning_trades} <span className="text-slate-500">/</span> <span className="text-rose-400">{backtestResult.losing_trades}</span>
                </span>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
                <span className="text-slate-400 block text-[11px] font-medium">Win Rate</span>
                <span className="text-xl font-bold font-mono text-indigo-300">{backtestResult.win_rate.toFixed(1)}%</span>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
                <span className="text-slate-400 block text-[11px] font-medium">Profit Factor</span>
                <span className="text-xl font-bold font-mono text-amber-300">{backtestResult.profit_factor.toFixed(2)}</span>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
                <span className="text-slate-400 block text-[11px] font-medium">Average Win</span>
                <span className="text-base font-bold font-mono text-emerald-400">+{backtestResult.average_win_percent.toFixed(2)}%</span>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
                <span className="text-slate-400 block text-[11px] font-medium">Average Loss</span>
                <span className="text-base font-bold font-mono text-rose-400">{backtestResult.average_loss_percent.toFixed(2)}%</span>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
                <span className="text-slate-400 block text-[11px] font-medium">Average Trade</span>
                <span className={`text-base font-bold font-mono ${backtestResult.average_trade_percent >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {backtestResult.average_trade_percent >= 0 ? '+' : ''}{backtestResult.average_trade_percent.toFixed(2)}%
                </span>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
                <span className="text-slate-400 block text-[11px] font-medium">Max Drawdown</span>
                <span className="text-base font-bold font-mono text-rose-400">{backtestResult.max_drawdown_percent.toFixed(2)}%</span>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
                <span className="text-slate-400 block text-[11px] font-medium">Avg Holding</span>
                <span className="text-base font-bold font-mono text-slate-200">{backtestResult.average_holding_days.toFixed(1)} days</span>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
                <span className="text-slate-400 block text-[11px] font-medium">Max Holding</span>
                <span className="text-base font-bold font-mono text-slate-200">{backtestResult.maximum_holding_days} days</span>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
                <span className="text-slate-400 block text-[11px] font-medium">Average R</span>
                <span className="text-base font-bold font-mono text-amber-300">{backtestResult.average_r_multiple.toFixed(2)}</span>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
                <span className="text-slate-400 block text-[11px] font-medium">Total R</span>
                <span className={`text-base font-bold font-mono ${backtestResult.total_r >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {backtestResult.total_r >= 0 ? '+' : ''}{backtestResult.total_r.toFixed(2)}
                </span>
              </div>
            </div>

            {/* Historical Trades Table */}
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 font-mono">
                Historical Trades Log ({backtestResult.trades.length})
              </h4>
              {backtestResult.trades.length === 0 ? (
                <div className="bg-slate-950/40 border border-slate-800 rounded-xl p-4 text-xs text-slate-400 font-mono text-center italic">
                  No completed trades generated by strategy for this stock.
                </div>
              ) : (
                <div className="overflow-x-auto rounded-xl border border-slate-800">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-slate-800/80 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-700/60">
                      <tr>
                        <th className="py-3 px-4">Signal</th>
                        <th className="py-3 px-4">Entry</th>
                        <th className="py-3 px-4">Entry Price</th>
                        <th className="py-3 px-4">Stop Loss</th>
                        <th className="py-3 px-4">Target</th>
                        <th className="py-3 px-4">Exit</th>
                        <th className="py-3 px-4">Exit Price</th>
                        <th className="py-3 px-4">Result</th>
                        <th className="py-3 px-4 text-right">P&L %</th>
                        <th className="py-3 px-4 text-right">R-Mult</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 bg-slate-900/60">
                      {backtestResult.trades.map((t, idx) => {
                        const isWin = t.pnl_percent > 0;
                        return (
                          <tr key={t.trade_id || idx} className="hover:bg-slate-800/40 transition-colors">
                            <td className="py-3 px-4 text-slate-400">{t.signal_date || t.entry_date}</td>
                            <td className="py-3 px-4 text-slate-300">{t.entry_date}</td>
                            <td className="py-3 px-4 text-emerald-400 font-bold">₹{t.entry_price.toFixed(2)}</td>
                            <td className="py-3 px-4 text-rose-400">{t.stop_loss ? `₹${t.stop_loss.toFixed(2)}` : '-'}</td>
                            <td className="py-3 px-4 text-teal-300">{t.target_price ? `₹${t.target_price.toFixed(2)}` : '-'}</td>
                            <td className="py-3 px-4 text-slate-300">{t.exit_date}</td>
                            <td className="py-3 px-4 text-slate-200 font-bold">₹{t.exit_price.toFixed(2)}</td>
                            <td className="py-3 px-4">
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
                            <td className={`py-3 px-4 text-right font-bold ${isWin ? 'text-emerald-400' : 'text-rose-400'}`}>
                              {isWin ? '+' : ''}{t.pnl_percent.toFixed(2)}%
                            </td>
                            <td className={`py-3 px-4 text-right font-bold ${t.r_multiple && t.r_multiple > 0 ? 'text-emerald-400' : t.r_multiple && t.r_multiple < 0 ? 'text-rose-400' : 'text-slate-400'}`}>
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
          </section>
        )}

        {/* Strategy Notice Disclaimer */}
        <div className="bg-slate-900/40 border border-slate-800/80 rounded-xl p-4 text-[11px] text-slate-400">
          <span className="font-bold text-slate-300 block mb-0.5">Strategy Signals Disclaimer</span>
          Quantitative setup generated by {stock.strategy_name} v{stock.strategy_version}. These signals represent technical pattern filters for analytical research purposes and are not financial advice.
        </div>
      </main>
    </div>
  );
};
