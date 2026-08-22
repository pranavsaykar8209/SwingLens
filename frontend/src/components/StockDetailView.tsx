import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  fetchAggregatedSignals,
  fetchSingleStockBacktest,
  type AggregatedSignalResult,
  type ScanResult,
  type SingleStockBacktestResult,
} from '../api/scanner';
import { useSafeNavigate } from '../utils/navigation';
import { Header } from './Header';
import { StockPriceChart } from './StockPriceChart';
import { StrengthBadge } from './StrengthBadge';

export interface StockDetailItem {
  symbol: string;
  company_name?: string | null;
  signal?: string;
  signal_date?: string | null;
  entry_price?: number | null;
  stop_loss?: number | null;
  target_price?: number | null;
  risk_reward?: number | null;
  score?: number | null;
  strength?: string | null;
  strategy_name?: string | null;
  strategy_version?: string | null;
  best_strategy_name?: string | null;
  buy_strategies?: string[];
  reason?: string | null;
  metadata?: Record<string, unknown>;
}

interface StockDetailViewProps {
  stock?: StockDetailItem | ScanResult;
  onBack?: () => void;
}

export const StockDetailView: React.FC<StockDetailViewProps> = ({
  stock: passedStock,
  onBack,
}) => {
  let routeSymbol: string | undefined;
  try {
    const params = useParams<{ symbol: string }>();
    routeSymbol = params?.symbol;
  } catch {
    routeSymbol = undefined;
  }

  const navigate = useSafeNavigate();

  const currentSymbol = passedStock?.symbol || routeSymbol || 'BANKBARODA';
  const stock: StockDetailItem = passedStock || { symbol: currentSymbol };

  const [loadingBacktest, setLoadingBacktest] = useState(false);
  const [backtestResult, setBacktestResult] = useState<SingleStockBacktestResult | null>(null);
  const [backtestError, setBacktestError] = useState<string | null>(null);

  const [loadingAggregator, setLoadingAggregator] = useState(false);
  const [aggregatedResult, setAggregatedResult] = useState<AggregatedSignalResult | null>(null);
  const [aggregatorError, setAggregatorError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    async function loadAggregator() {
      setLoadingAggregator(true);
      setAggregatorError(null);
      try {
        const agg = await fetchAggregatedSignals(currentSymbol);
        if (isMounted) {
          setAggregatedResult(agg);
        }
      } catch (err: unknown) {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : 'Failed to load strategy votes.';
          setAggregatorError(msg);
        }
      } finally {
        if (isMounted) {
          setLoadingAggregator(false);
        }
      }
    }
    loadAggregator();
    return () => {
      isMounted = false;
    };
  }, [currentSymbol]);

  const entryPrice = stock.entry_price ?? aggregatedResult?.best_entry_price;
  const stopLoss = stock.stop_loss ?? aggregatedResult?.best_stop_loss;
  const targetPrice = stock.target_price ?? aggregatedResult?.best_target_price;
  const riskReward = stock.risk_reward ?? aggregatedResult?.best_risk_reward;
  const strengthVal =
    ('strength' in stock ? stock.strength : undefined) ?? aggregatedResult?.strength ?? 'NO_SIGNAL';
  const scoreVal = stock.score ?? aggregatedResult?.score ?? 0;
  const strategyName =
    ('best_strategy_name' in stock ? stock.best_strategy_name : undefined) ||
    stock.strategy_name ||
    aggregatedResult?.best_strategy_name ||
    'Multi-Strategy';

  const hasActionableBuy = scoreVal > 0 && entryPrice !== null && entryPrice !== undefined;

  const handleRunBacktest = async () => {
    setLoadingBacktest(true);
    setBacktestError(null);
    try {
      const stratKey = (stock.strategy_name || 'ema_pullback').toLowerCase().replace(/ /g, '_');
      const res = await fetchSingleStockBacktest(currentSymbol, stratKey);
      setBacktestResult(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to run single-stock backtest.';
      setBacktestError(msg);
    } finally {
      setLoadingBacktest(false);
    }
  };

  const handleBackClick = () => {
    if (onBack) {
      onBack();
    } else {
      navigate('/');
    }
  };

  const chartStockProp: ScanResult = {
    symbol: currentSymbol,
    company_name: stock.company_name,
    signal: (stock.signal as any) || (hasActionableBuy ? 'BUY' : 'HOLD'),
    signal_date: stock.signal_date || aggregatedResult?.signal_date,
    entry_price: entryPrice,
    stop_loss: stopLoss,
    target_price: targetPrice,
    risk_reward: riskReward,
    strategy_name: strategyName,
    strategy_version: stock.strategy_version || '1.0',
    metadata: stock.metadata,
    status: 'SUCCESS',
  };

  const signalDate = stock.signal_date || aggregatedResult?.signal_date || undefined;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans antialiased pb-16">
      {/* 1. Global Consistent Header */}
      <Header scanDate={signalDate} onRefresh={() => {}} isRefreshing={false} />

      {/* Main Container */}
      <main className="w-full px-6 sm:px-10 pb-12 space-y-6">
        {/* Page-Specific Action Bar */}
        <div className="flex items-center justify-between">
          <button
            onClick={handleBackClick}
            className="group flex items-center gap-2 text-xs font-semibold text-slate-300 hover:text-white bg-slate-900 hover:bg-slate-800 px-3.5 py-2 rounded-xl border border-slate-800 transition-all cursor-pointer shadow-sm"
          >
            <svg className="w-4 h-4 transition-transform group-hover:-translate-x-1 text-slate-400 group-hover:text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Recommendations
          </button>

          <button
            onClick={handleRunBacktest}
            disabled={loadingBacktest}
            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold text-xs px-4 py-2 rounded-xl border border-indigo-400/30 transition-all cursor-pointer flex items-center gap-2 shadow-md shadow-indigo-950"
          >
            {loadingBacktest ? (
              <>
                <svg className="animate-spin h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Running Backtest...
              </>
            ) : (
              <>
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Backtest Historical Performance
              </>
            )}
          </button>
        </div>

        {/* Stock Title Banner Header */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xl">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl sm:text-3xl font-extrabold text-white font-mono tracking-tight">
                {currentSymbol}
              </h1>
              <span
                className={`text-[11px] px-2.5 py-0.5 rounded-md font-mono font-bold uppercase border ${
                  hasActionableBuy
                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                    : 'bg-slate-800 text-slate-400 border-slate-700'
                }`}
              >
                {hasActionableBuy ? 'ACTIONABLE BUY' : 'NO ACTION'}
              </span>
              <StrengthBadge strength={strengthVal} size="sm" />
            </div>
            <p className="text-xs sm:text-sm text-slate-300 font-medium mt-1">
              {stock.company_name || currentSymbol}
            </p>
          </div>

          <div className="text-xs text-slate-400 font-mono bg-slate-800/60 border border-slate-700/60 rounded-xl px-4 py-2.5 flex items-center gap-5 shadow-inner">
            <div>
              <span className="text-slate-500 block text-[10px] tracking-wider uppercase font-semibold">SIGNAL DATE</span>
              <span className="text-slate-100 font-bold">{signalDate || 'Latest'}</span>
            </div>
            <div className="h-6 w-px bg-slate-700/60" />
            <div>
              <span className="text-slate-500 block text-[10px] tracking-wider uppercase font-semibold">STRATEGY AGREEMENT</span>
              <span className={scoreVal > 0 ? 'text-emerald-400 font-bold' : 'text-slate-400 font-bold'}>
                {scoreVal}/5 BUYs
              </span>
            </div>
          </div>
        </div>

        {/* 2. Trade Execution Parameters (Only show prominent parameters when actionable) */}
        <section className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 sm:p-6 shadow-xl space-y-3">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
            Trade Execution Parameters
          </h2>

          {hasActionableBuy ? (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5 sm:p-4 shadow-sm">
                <span className="text-xs text-slate-400 block mb-0.5 font-medium">Entry Price</span>
                <span className="text-xl sm:text-2xl font-extrabold font-mono text-emerald-400">
                  ₹{entryPrice!.toFixed(2)}
                </span>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5 sm:p-4 shadow-sm">
                <span className="text-xs text-slate-400 block mb-0.5 font-medium">Stop Loss</span>
                <span className="text-xl sm:text-2xl font-extrabold font-mono text-rose-400">
                  {stopLoss ? `₹${stopLoss.toFixed(2)}` : '-'}
                </span>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5 sm:p-4 shadow-sm">
                <span className="text-xs text-slate-400 block mb-0.5 font-medium">Target Price</span>
                <span className="text-xl sm:text-2xl font-extrabold font-mono text-teal-300">
                  {targetPrice ? `₹${targetPrice.toFixed(2)}` : '-'}
                </span>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5 sm:p-4 shadow-sm">
                <span className="text-xs text-slate-400 block mb-0.5 font-medium">Risk : Reward</span>
                <span className="text-xl sm:text-2xl font-extrabold font-mono text-amber-300">
                  {riskReward ? `${riskReward}:1` : '-'}
                </span>
              </div>
            </div>
          ) : (
            <div className="bg-slate-950/40 border border-slate-800/60 rounded-xl p-4 text-xs font-mono text-slate-400 space-y-1">
              <span className="font-semibold text-slate-300 block">No actionable setup today.</span>
              <p>
                Overall strategy agreement is {scoreVal}/5. All quantitative strategies currently recommend HOLD for this stock.
              </p>
            </div>
          )}
        </section>

        {/* 3. Full-Width Historical Price Chart */}
        <section className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 sm:p-6 shadow-xl">
          <StockPriceChart stock={chartStockProp} backtestTrades={backtestResult?.trades || []} />
        </section>

        {/* 4. Multi-Strategy Individual Votes (5 Strategies) */}
        <section className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 sm:p-6 shadow-xl space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
                Individual Strategy Votes (5 Strategies)
              </h2>
              <p className="text-xs text-slate-500 font-sans mt-0.5">
                Evaluated independently on completed daily candles
              </p>
            </div>
            {loadingAggregator && (
              <span className="text-xs text-slate-400 font-mono animate-pulse">Loading votes...</span>
            )}
          </div>

          {aggregatorError && (
            <div className="p-4 bg-rose-950/20 border border-rose-500/30 rounded-xl text-xs text-rose-300 font-mono">
              {aggregatorError}
            </div>
          )}

          {aggregatedResult && (
            <div className="overflow-x-auto rounded-xl border border-slate-800/80">
              <table className="w-full text-left border-collapse text-xs font-mono">
                <thead>
                  <tr className="bg-slate-800/50 border-b border-slate-700/60 text-slate-400 uppercase tracking-wider text-[11px]">
                    <th className="py-2.5 px-4">Strategy</th>
                    <th className="py-2.5 px-3 text-center">Vote</th>
                    <th className="py-2.5 px-3 text-right">Entry</th>
                    <th className="py-2.5 px-3 text-right">Stop Loss</th>
                    <th className="py-2.5 px-3 text-right">Target</th>
                    <th className="py-2.5 px-3 text-center">R:R</th>
                    <th className="py-2.5 px-4">Setup Reasoning</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50 text-slate-200">
                  {aggregatedResult.votes.map((vote) => {
                    const isVoteBuy = vote.signal === 'BUY';
                    return (
                      <tr
                        key={vote.strategy_name}
                        className={`transition-colors ${
                          isVoteBuy ? 'bg-emerald-950/15 hover:bg-emerald-950/25' : 'hover:bg-slate-800/30'
                        }`}
                      >
                        <td className="py-2.5 px-4">
                          <span className={`font-extrabold ${isVoteBuy ? 'text-emerald-300' : 'text-slate-200'}`}>
                            {vote.strategy_name}
                          </span>
                          <span className="text-[10px] text-slate-500 ml-1.5">v{vote.strategy_version}</span>
                        </td>
                        <td className="py-2.5 px-3 text-center">
                          <span
                            className={`text-[10px] px-2.5 py-0.5 rounded font-extrabold border ${
                              isVoteBuy
                                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                                : 'bg-slate-800 text-slate-400 border-slate-700'
                            }`}
                          >
                            {isVoteBuy ? 'BUY ✓' : 'HOLD'}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right font-medium">
                          {vote.entry_price ? `₹${vote.entry_price.toFixed(2)}` : '-'}
                        </td>
                        <td className="py-2.5 px-3 text-right font-medium">
                          {vote.stop_loss ? `₹${vote.stop_loss.toFixed(2)}` : '-'}
                        </td>
                        <td className="py-2.5 px-3 text-right font-medium">
                          {vote.target_price ? `₹${vote.target_price.toFixed(2)}` : '-'}
                        </td>
                        <td className="py-2.5 px-3 text-center">
                          {vote.risk_reward ? `${vote.risk_reward}:1` : '-'}
                        </td>
                        <td className="py-2.5 px-4 text-slate-300 text-[11px] font-sans">
                          {vote.reason || vote.error || 'No setup breakdown specified.'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* 5. Calculated Indicators */}
        {stock.metadata && Object.keys(stock.metadata).length > 0 && (
          <section className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 sm:p-6 shadow-xl">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 font-mono">
              Calculated Technical Indicators
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 text-xs">
              {Object.entries(stock.metadata).map(([key, val]) => (
                <div key={key} className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-3 flex justify-between items-center">
                  <span className="text-slate-400 font-mono">{key}</span>
                  <span className="font-bold text-slate-100 font-mono text-sm">{String(val)}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 6. Backtest Results Section */}
        {backtestError && (
          <div className="bg-rose-950/30 border border-rose-500/40 rounded-2xl p-5 text-xs text-rose-300 font-mono shadow-lg">
            <span className="font-bold block mb-1">Backtest Execution Error:</span>
            {backtestError}
          </div>
        )}

        {backtestResult && (
          <section className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 sm:p-6 space-y-5 animate-fade-in shadow-xl">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-800/50 border border-slate-700/60 rounded-xl p-4">
              <div>
                <div className="flex items-center gap-3">
                  <h3 className="text-base font-bold text-white font-mono">
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
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 text-xs">
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5">
                <span className="text-slate-400 block text-[11px] font-medium">Total Trades</span>
                <span className="text-lg font-bold font-mono text-white">{backtestResult.total_trades}</span>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5">
                <span className="text-slate-400 block text-[11px] font-medium">Winning / Losing</span>
                <span className="text-lg font-bold font-mono text-emerald-400">
                  {backtestResult.winning_trades} <span className="text-slate-500">/</span> <span className="text-rose-400">{backtestResult.losing_trades}</span>
                </span>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5">
                <span className="text-slate-400 block text-[11px] font-medium">Win Rate</span>
                <span className="text-lg font-bold font-mono text-indigo-300">{backtestResult.win_rate.toFixed(1)}%</span>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5">
                <span className="text-slate-400 block text-[11px] font-medium">Profit Factor</span>
                <span className="text-lg font-bold font-mono text-amber-300">{backtestResult.profit_factor.toFixed(2)}</span>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5">
                <span className="text-slate-400 block text-[11px] font-medium">Average Win</span>
                <span className="text-base font-bold font-mono text-emerald-400">+{backtestResult.average_win_percent.toFixed(2)}%</span>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5">
                <span className="text-slate-400 block text-[11px] font-medium">Average Loss</span>
                <span className="text-base font-bold font-mono text-rose-400">{backtestResult.average_loss_percent.toFixed(2)}%</span>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5">
                <span className="text-slate-400 block text-[11px] font-medium">Average Trade</span>
                <span className={`text-base font-bold font-mono ${backtestResult.average_trade_percent >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {backtestResult.average_trade_percent >= 0 ? '+' : ''}{backtestResult.average_trade_percent.toFixed(2)}%
                </span>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5">
                <span className="text-slate-400 block text-[11px] font-medium">Max Drawdown</span>
                <span className="text-base font-bold font-mono text-rose-400">{backtestResult.max_drawdown_percent.toFixed(2)}%</span>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5">
                <span className="text-slate-400 block text-[11px] font-medium">Avg Holding</span>
                <span className="text-base font-bold font-mono text-slate-200">{backtestResult.average_holding_days.toFixed(1)} days</span>
              </div>
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5">
                <span className="text-slate-400 block text-[11px] font-medium">Max Holding</span>
                <span className="text-base font-bold font-mono text-slate-200">{backtestResult.maximum_holding_days} days</span>
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  );
};
