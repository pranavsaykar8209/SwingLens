import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  AVAILABLE_STRATEGIES,
  fetchAllStrategiesBacktest,
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

  // Backtest State: stores results keyed by strategy key (e.g. 'ema_pullback')
  const [loadingBacktest, setLoadingBacktest] = useState(false);
  const [allBacktestResults, setAllBacktestResults] = useState<Record<string, SingleStockBacktestResult>>({});
  const [activeStrategyKey, setActiveStrategyKey] = useState<string>('ALL');
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

  // Run backtests across all 5 strategies concurrently
  const handleRunAllBacktests = async () => {
    setLoadingBacktest(true);
    setBacktestError(null);
    try {
      const results = await fetchAllStrategiesBacktest(currentSymbol);
      setAllBacktestResults(results);
      if (activeStrategyKey !== 'ALL' && !results[activeStrategyKey]) {
        setActiveStrategyKey('ALL');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to run multi-strategy backtests.';
      setBacktestError(msg);
    } finally {
      setLoadingBacktest(false);
    }
  };

  // Run single strategy on demand if not already loaded
  const handleSelectStrategyTab = async (stratKey: string) => {
    setActiveStrategyKey(stratKey);
    if (stratKey !== 'ALL' && !allBacktestResults[stratKey]) {
      setLoadingBacktest(true);
      setBacktestError(null);
      try {
        const res = await fetchSingleStockBacktest(currentSymbol, stratKey);
        setAllBacktestResults((prev) => ({ ...prev, [stratKey]: res }));
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : `Failed to run backtest for ${stratKey}.`;
        setBacktestError(msg);
      } finally {
        setLoadingBacktest(false);
      }
    }
  };

  const handleBackClick = () => {
    if (onBack) {
      onBack();
    } else {
      navigate('/');
    }
  };

  // Active backtest result for charting and detailed panel
  const activeSingleResult =
    activeStrategyKey !== 'ALL'
      ? allBacktestResults[activeStrategyKey]
      : Object.values(allBacktestResults)[0] || null;

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
  const hasAnyBacktestResults = Object.keys(allBacktestResults).length > 0;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans antialiased pb-16">
      {/* 1. Global Consistent Header */}
      <Header scanDate={signalDate} onRefresh={() => {}} isRefreshing={false} />

      {/* Main Container */}
      <main className="w-full px-6 sm:px-10 pb-12 space-y-6">
        {/* Page-Specific Action Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <button
            onClick={handleBackClick}
            className="group flex items-center gap-2 text-xs font-semibold text-slate-300 hover:text-white bg-slate-900 hover:bg-slate-800 px-3.5 py-2 rounded-xl border border-slate-800 transition-all cursor-pointer shadow-sm w-fit"
          >
            <svg className="w-4 h-4 transition-transform group-hover:-translate-x-1 text-slate-400 group-hover:text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Recommendations
          </button>

          <button
            onClick={handleRunAllBacktests}
            disabled={loadingBacktest}
            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold text-xs px-4 py-2 rounded-xl border border-indigo-400/30 transition-all cursor-pointer flex items-center gap-2 shadow-md shadow-indigo-950 w-fit"
          >
            {loadingBacktest ? (
              <>
                <svg className="animate-spin h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Backtesting 5 Strategies...
              </>
            ) : (
              <>
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                {hasAnyBacktestResults ? '↻ Re-run All 5 Strategy Backtests' : 'Backtest All 5 Strategies'}
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

        {/* 2. Trade Execution Parameters */}
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
                <span className="text-xl sm:text-2xl font-extrabold font-mono text-indigo-300">
                  1 : {riskReward ? riskReward.toFixed(1) : '2.0'}
                </span>
              </div>
            </div>
          ) : (
            <div className="bg-slate-800/40 border border-slate-800 rounded-xl p-4 text-xs text-slate-400 font-mono">
              Setup conditions not met for actionable entry today. Monitoring stock for alignment.
            </div>
          )}
        </section>

        {/* 3. Multi-Strategy Breakdown Panel */}
        <section className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 sm:p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
            <h2 className="text-base font-bold text-white font-mono tracking-tight flex items-center gap-2">
              Multi-Strategy Signal Breakdown
              <span className="text-xs px-2 py-0.5 rounded-md bg-slate-800 text-slate-400 font-medium border border-slate-700">
                5 Frozen Strategies
              </span>
            </h2>
          </div>

          {loadingAggregator ? (
            <div className="py-6 text-center text-slate-400 text-xs font-mono">
              Loading multi-strategy evaluations...
            </div>
          ) : aggregatorError ? (
            <div className="bg-rose-950/30 border border-rose-500/40 rounded-xl p-4 text-xs text-rose-300 font-mono">
              {aggregatorError}
            </div>
          ) : aggregatedResult ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
              {aggregatedResult.votes.map((vote) => {
                const isBuy = vote.signal === 'BUY';
                return (
                  <div
                    key={vote.strategy_name}
                    className={`rounded-xl p-4 border transition-all ${
                      isBuy
                        ? 'bg-emerald-950/20 border-emerald-500/40 shadow-sm shadow-emerald-950/30'
                        : 'bg-slate-800/40 border-slate-800/80 opacity-75'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <span className="font-bold text-sm text-white font-mono">
                        {vote.strategy_name}
                      </span>
                      <span
                        className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border uppercase ${
                          isBuy
                            ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 font-extrabold'
                            : 'bg-slate-800 text-slate-400 border-slate-700'
                        }`}
                      >
                        {vote.signal}
                      </span>
                    </div>

                    <p className="text-xs text-slate-300 font-sans leading-relaxed mb-3">
                      {vote.reason || 'No specific signal rationale recorded.'}
                    </p>

                    {isBuy && vote.entry_price && (
                      <div className="grid grid-cols-3 gap-2 text-[11px] font-mono pt-2 border-t border-emerald-500/20 text-slate-300">
                        <div>
                          <span className="text-slate-400 text-[10px] block">ENTRY</span>
                          <span className="text-emerald-400 font-bold">₹{vote.entry_price.toFixed(2)}</span>
                        </div>
                        <div>
                          <span className="text-slate-400 text-[10px] block">STOP</span>
                          <span className="text-rose-400 font-bold">{vote.stop_loss ? `₹${vote.stop_loss.toFixed(2)}` : '-'}</span>
                        </div>
                        <div>
                          <span className="text-slate-400 text-[10px] block">TARGET</span>
                          <span className="text-teal-300 font-bold">{vote.target_price ? `₹${vote.target_price.toFixed(2)}` : '-'}</span>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : null}
        </section>

        {/* 4. Interactive Price History Chart */}
        <section className="space-y-2">
          <StockPriceChart
            stock={chartStockProp}
            backtestTrades={activeSingleResult?.trades || []}
          />
          {activeSingleResult && (
            <p className="text-[11px] text-slate-400 font-mono text-right pr-2">
              Chart trade markers displaying backtest simulation for: <span className="text-indigo-300 font-bold">{activeSingleResult.strategy_name}</span>
            </p>
          )}
        </section>

        {/* 5. Strategy Indicators & Metadata Panel */}
        {stock.metadata && Object.keys(stock.metadata).length > 0 && (
          <section className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 sm:p-6 shadow-xl space-y-3">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              Strategy Indicator Values
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              {Object.entries(stock.metadata).map(([key, val]) => (
                <div key={key} className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-3 flex justify-between items-center">
                  <span className="text-slate-400 font-mono">{key}</span>
                  <span className="font-bold text-slate-100 font-mono text-sm">{String(val)}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 6. Multi-Strategy Backtest Section */}
        {backtestError && (
          <div className="bg-rose-950/30 border border-rose-500/40 rounded-2xl p-5 text-xs text-rose-300 font-mono shadow-lg">
            <span className="font-bold block mb-1">Backtest Execution Error:</span>
            {backtestError}
          </div>
        )}

        <section className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 sm:p-6 space-y-5 shadow-xl">
          {/* Header & Strategy Selector Tabs */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
            <div>
              <h2 className="text-base font-bold text-white font-mono tracking-tight flex items-center gap-2">
                Historical Backtest Performance
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 font-medium">
                  {currentSymbol}
                </span>
              </h2>
              <p className="text-xs text-slate-400 font-mono mt-0.5">
                Simulated candle-by-candle backtesting with conservative OHLC ambiguity resolution
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleRunAllBacktests}
                disabled={loadingBacktest}
                className="text-xs px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white border border-slate-700 font-mono font-semibold transition-all cursor-pointer shadow-sm flex items-center gap-1.5"
              >
                ↻ Run All 5 Strategies
              </button>
            </div>
          </div>

          {/* Strategy Tabs Navigation */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-thin">
            <button
              onClick={() => setActiveStrategyKey('ALL')}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold font-mono transition-all cursor-pointer flex items-center gap-1.5 whitespace-nowrap ${
                activeStrategyKey === 'ALL'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-950 border border-indigo-400/40'
                  : 'bg-slate-800/70 text-slate-300 hover:text-white hover:bg-slate-800 border border-slate-700/60'
              }`}
            >
              ★ Compare All 5 Strategies
            </button>

            {AVAILABLE_STRATEGIES.map((strat) => {
              const isLoaded = Boolean(allBacktestResults[strat.key]);
              const isSelected = activeStrategyKey === strat.key;
              return (
                <button
                  key={strat.key}
                  onClick={() => handleSelectStrategyTab(strat.key)}
                  className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold font-mono transition-all cursor-pointer flex items-center gap-1.5 whitespace-nowrap ${
                    isSelected
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-950 border border-indigo-400/40'
                      : 'bg-slate-800/70 text-slate-300 hover:text-white hover:bg-slate-800 border border-slate-700/60'
                  }`}
                >
                  {strat.name}
                  {isLoaded && (
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" title="Backtest loaded" />
                  )}
                </button>
              );
            })}
          </div>

          {/* TAB 1: ALL STRATEGIES COMPARISON TABLE */}
          {activeStrategyKey === 'ALL' && (
            <div className="space-y-4">
              {!hasAnyBacktestResults && !loadingBacktest ? (
                <div className="bg-slate-800/30 border border-slate-800/80 rounded-xl p-8 text-center space-y-3">
                  <p className="text-sm font-semibold text-slate-300">
                    No backtests run yet for {currentSymbol}
                  </p>
                  <p className="text-xs text-slate-400 max-w-md mx-auto">
                    Click the button below to evaluate all 5 quantitative swing strategies over historical price history.
                  </p>
                  <button
                    onClick={handleRunAllBacktests}
                    className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2 rounded-xl border border-indigo-400/30 transition-all cursor-pointer inline-flex items-center gap-2 shadow-md shadow-indigo-950"
                  >
                    Run All 5 Strategy Backtests
                  </button>
                </div>
              ) : (
                <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/40">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-slate-800/80 text-slate-400 uppercase tracking-wider text-[10px] border-b border-slate-800">
                      <tr>
                        <th className="py-3 px-4">Strategy</th>
                        <th className="py-3 px-3 text-center">Trades</th>
                        <th className="py-3 px-3 text-center">Win / Loss</th>
                        <th className="py-3 px-3 text-center">Win Rate</th>
                        <th className="py-3 px-3 text-center">Profit Factor</th>
                        <th className="py-3 px-3 text-center">Avg Win / Loss</th>
                        <th className="py-3 px-3 text-center">Avg Trade %</th>
                        <th className="py-3 px-3 text-center">Max Drawdown</th>
                        <th className="py-3 px-3 text-center">Avg Hold</th>
                        <th className="py-3 px-4 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/50 text-slate-200">
                      {AVAILABLE_STRATEGIES.map((strat) => {
                        const res = allBacktestResults[strat.key];
                        if (!res) {
                          return (
                            <tr key={strat.key} className="hover:bg-slate-800/30 transition-colors">
                              <td className="py-3 px-4 font-bold text-white">
                                {strat.name} <span className="text-slate-500 text-[10px]">v{strat.version}</span>
                              </td>
                              <td colSpan={8} className="py-3 px-3 text-center text-slate-500 italic">
                                Not backtested yet
                              </td>
                              <td className="py-3 px-4 text-right">
                                <button
                                  onClick={() => handleSelectStrategyTab(strat.key)}
                                  className="text-xs px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white border border-slate-700 transition-all cursor-pointer font-semibold"
                                >
                                  Run Backtest
                                </button>
                              </td>
                            </tr>
                          );
                        }

                        const isProfitable = res.profit_factor >= 1.0;
                        return (
                          <tr key={strat.key} className="hover:bg-slate-800/40 transition-colors">
                            <td className="py-3 px-4 font-bold text-white">
                              <div>
                                {strat.name}
                                <span className="block text-[10px] text-slate-400 font-normal">
                                  {res.start_date} → {res.end_date}
                                </span>
                              </div>
                            </td>
                            <td className="py-3 px-3 text-center font-bold">{res.total_trades}</td>
                            <td className="py-3 px-3 text-center">
                              <span className="text-emerald-400 font-bold">{res.winning_trades}</span>
                              <span className="text-slate-500 mx-1">/</span>
                              <span className="text-rose-400 font-bold">{res.losing_trades}</span>
                            </td>
                            <td className="py-3 px-3 text-center">
                              <span
                                className={`px-2 py-0.5 rounded font-bold ${
                                  res.win_rate >= 50
                                    ? 'bg-emerald-500/20 text-emerald-300'
                                    : 'bg-slate-800 text-slate-300'
                                }`}
                              >
                                {res.win_rate.toFixed(1)}%
                              </span>
                            </td>
                            <td className="py-3 px-3 text-center">
                              <span
                                className={`font-bold ${
                                  isProfitable ? 'text-amber-300' : 'text-slate-400'
                                }`}
                              >
                                {res.profit_factor.toFixed(2)}
                              </span>
                            </td>
                            <td className="py-3 px-3 text-center">
                              <span className="text-emerald-400">+{res.average_win_percent.toFixed(1)}%</span>
                              <span className="text-slate-500 mx-1">/</span>
                              <span className="text-rose-400">{res.average_loss_percent.toFixed(1)}%</span>
                            </td>
                            <td className="py-3 px-3 text-center">
                              <span className={`font-bold ${res.average_trade_percent >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                {res.average_trade_percent >= 0 ? '+' : ''}{res.average_trade_percent.toFixed(2)}%
                              </span>
                            </td>
                            <td className="py-3 px-3 text-center text-rose-400 font-medium">
                              {res.max_drawdown_percent.toFixed(1)}%
                            </td>
                            <td className="py-3 px-3 text-center text-slate-300">
                              {res.average_holding_days.toFixed(1)}d
                            </td>
                            <td className="py-3 px-4 text-right">
                              <button
                                onClick={() => setActiveStrategyKey(strat.key)}
                                className="text-xs px-2.5 py-1 rounded-lg bg-indigo-600/30 hover:bg-indigo-600 text-indigo-200 hover:text-white border border-indigo-500/40 transition-all cursor-pointer font-semibold"
                              >
                                View Trades & Chart →
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: INDIVIDUAL STRATEGY DETAIL VIEW */}
          {activeStrategyKey !== 'ALL' && (
            <div className="space-y-5 animate-fade-in">
              {activeSingleResult ? (
                <>
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-800/50 border border-slate-700/60 rounded-xl p-4">
                    <div>
                      <div className="flex items-center gap-3">
                        <h3 className="text-base font-bold text-white font-mono">
                          {activeSingleResult.symbol} — {activeSingleResult.strategy_name} Performance
                        </h3>
                        <span className="text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-2.5 py-0.5 rounded-md">
                          v{activeSingleResult.strategy_version}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mt-1 font-mono">
                        Period: <span className="text-slate-200">{activeSingleResult.start_date}</span> → <span className="text-slate-200">{activeSingleResult.end_date}</span>
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
                      <span className="text-lg font-bold font-mono text-white">{activeSingleResult.total_trades}</span>
                    </div>
                    <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5">
                      <span className="text-slate-400 block text-[11px] font-medium">Winning / Losing</span>
                      <span className="text-lg font-bold font-mono text-emerald-400">
                        {activeSingleResult.winning_trades} <span className="text-slate-500">/</span> <span className="text-rose-400">{activeSingleResult.losing_trades}</span>
                      </span>
                    </div>
                    <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5">
                      <span className="text-slate-400 block text-[11px] font-medium">Win Rate</span>
                      <span className="text-lg font-bold font-mono text-indigo-300">{activeSingleResult.win_rate.toFixed(1)}%</span>
                    </div>
                    <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5">
                      <span className="text-slate-400 block text-[11px] font-medium">Profit Factor</span>
                      <span className="text-lg font-bold font-mono text-amber-300">{activeSingleResult.profit_factor.toFixed(2)}</span>
                    </div>
                    <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5">
                      <span className="text-slate-400 block text-[11px] font-medium">Average Win</span>
                      <span className="text-base font-bold font-mono text-emerald-400">+{activeSingleResult.average_win_percent.toFixed(2)}%</span>
                    </div>
                    <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5">
                      <span className="text-slate-400 block text-[11px] font-medium">Average Loss</span>
                      <span className="text-base font-bold font-mono text-rose-400">{activeSingleResult.average_loss_percent.toFixed(2)}%</span>
                    </div>
                    <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5">
                      <span className="text-slate-400 block text-[11px] font-medium">Average Trade</span>
                      <span className={`text-base font-bold font-mono ${activeSingleResult.average_trade_percent >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {activeSingleResult.average_trade_percent >= 0 ? '+' : ''}{activeSingleResult.average_trade_percent.toFixed(2)}%
                      </span>
                    </div>
                    <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5">
                      <span className="text-slate-400 block text-[11px] font-medium">Max Drawdown</span>
                      <span className="text-base font-bold font-mono text-rose-400">{activeSingleResult.max_drawdown_percent.toFixed(2)}%</span>
                    </div>
                    <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5">
                      <span className="text-slate-400 block text-[11px] font-medium">Avg Holding</span>
                      <span className="text-base font-bold font-mono text-slate-200">{activeSingleResult.average_holding_days.toFixed(1)} days</span>
                    </div>
                    <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5">
                      <span className="text-slate-400 block text-[11px] font-medium">Max Holding</span>
                      <span className="text-base font-bold font-mono text-slate-200">{activeSingleResult.maximum_holding_days} days</span>
                    </div>
                  </div>

                  {/* Simulated Trade Execution Log Table */}
                  {activeSingleResult.trades && activeSingleResult.trades.length > 0 && (
                    <div className="space-y-3 pt-2">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
                        Simulated Historical Trades ({activeSingleResult.trades.length})
                      </h4>
                      <div className="overflow-x-auto rounded-xl border border-slate-800 max-h-72 overflow-y-auto">
                        <table className="w-full text-left text-xs font-mono">
                          <thead className="bg-slate-800/80 text-slate-400 uppercase tracking-wider text-[10px] sticky top-0 border-b border-slate-800">
                            <tr>
                              <th className="py-2.5 px-3">#</th>
                              <th className="py-2.5 px-3">Entry Date</th>
                              <th className="py-2.5 px-3">Entry Price</th>
                              <th className="py-2.5 px-3">Exit Date</th>
                              <th className="py-2.5 px-3">Exit Price</th>
                              <th className="py-2.5 px-3 text-center">Holding</th>
                              <th className="py-2.5 px-3">Exit Reason</th>
                              <th className="py-2.5 px-3 text-right">Return %</th>
                              <th className="py-2.5 px-3 text-right">Realized R</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800/50 text-slate-200">
                            {activeSingleResult.trades.map((t, idx) => {
                              const isWin = (t.pnl_percent || 0) >= 0;
                              return (
                                <tr key={idx} className="hover:bg-slate-800/40 transition-colors">
                                  <td className="py-2 px-3 text-slate-500">{idx + 1}</td>
                                  <td className="py-2 px-3">{t.entry_date}</td>
                                  <td className="py-2 px-3">₹{t.entry_price.toFixed(2)}</td>
                                  <td className="py-2 px-3">{t.exit_date}</td>
                                  <td className="py-2 px-3">₹{t.exit_price.toFixed(2)}</td>
                                  <td className="py-2 px-3 text-center">{t.holding_days}d</td>
                                  <td className="py-2 px-3">
                                    <span className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                                      t.exit_reason === 'TARGET'
                                        ? 'bg-emerald-500/20 text-emerald-300'
                                        : t.exit_reason === 'STOP_LOSS'
                                        ? 'bg-rose-500/20 text-rose-300'
                                        : 'bg-slate-800 text-slate-300'
                                    }`}>
                                      {t.exit_reason}
                                    </span>
                                  </td>
                                  <td className={`py-2 px-3 text-right font-bold ${isWin ? 'text-emerald-400' : 'text-rose-400'}`}>
                                    {isWin ? '+' : ''}{t.pnl_percent.toFixed(2)}%
                                  </td>
                                  <td className={`py-2 px-3 text-right font-bold ${isWin ? 'text-emerald-400' : 'text-rose-400'}`}>
                                    {t.r_multiple !== undefined && t.r_multiple !== null
                                      ? `${t.r_multiple >= 0 ? '+' : ''}${t.r_multiple.toFixed(2)}R`
                                      : '-'}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="py-8 text-center text-slate-400 text-xs font-mono">
                  Loading strategy backtest...
                </div>
              )}
            </div>
          )}
        </section>
      </main>
    </div>
  );
};
