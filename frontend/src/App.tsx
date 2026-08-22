import { useCallback, useEffect, useState } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import {
  fetchActiveWatchlist,
  fetchDailyScanStatus,
  fetchDailySignals,
  fetchStrategyAnalytics,
  runDailyScanWorkflow,
  type DailyScanStatusResponse,
  type DailySignalRanking,
  type RankedSignal,
  type ScanSummary,
  type StrategyAnalyticsResponse,
  type WatchlistSetup,
} from './api/scanner';
import { Header } from './components/Header';
import { MarketScannerTable } from './components/MarketScannerTable';
import { StockDetailView } from './components/StockDetailView';
import { StrategyPerformancePreview } from './components/StrategyPerformancePreview';
import { SummaryCards } from './components/SummaryCards';
import { TopSetupsTable } from './components/TopSetupsTable';
import { WatchlistPreview } from './components/WatchlistPreview';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { WatchlistPage } from './pages/WatchlistPage';

function DashboardView() {
  const navigate = useNavigate();
  const [dailyRanking, setDailyRanking] = useState<DailySignalRanking | null>(null);
  const [legacyScan, setLegacyScan] = useState<ScanSummary | null>(null);
  const [statusData, setStatusData] = useState<DailyScanStatusResponse | null>(null);
  const [watchlistSetups, setWatchlistSetups] = useState<WatchlistSetup[]>([]);
  const [strategyAnalytics, setStrategyAnalytics] = useState<StrategyAnalyticsResponse | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [progressStep, setProgressStep] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [selectedStrategyFilter, setSelectedStrategyFilter] = useState<string>('ALL');

  const loadDashboardData = useCallback(async () => {
    const [statusRes, rankingRes, watchlistRes, analyticsRes] = await Promise.all([
      fetchDailyScanStatus().catch((err) => {
        throw err;
      }),
      fetchDailySignals(50).catch(() => null),
      fetchActiveWatchlist().catch(() => []),
      fetchStrategyAnalytics().catch(() => null),
    ]);

    if (statusRes) setStatusData(statusRes);
    if (rankingRes) setDailyRanking(rankingRes);
    if (watchlistRes) setWatchlistSetups(watchlistRes);
    if (analyticsRes) setStrategyAnalytics(analyticsRes);
  }, []);

  const executeWorkflow = useCallback(
    async (force: boolean = false) => {
      setIsRefreshing(true);
      setError(null);

      try {
        setProgressStep('Checking market data...');
        await new Promise((r) => setTimeout(r, 100));

        setProgressStep('Running daily multi-strategy scan workflow...');
        const scanRes = await runDailyScanWorkflow(force);
        if (scanRes) setLegacyScan(scanRes);

        setProgressStep('Aggregating rankings and strategy performance...');
        await loadDashboardData();
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Today's scan could not be completed.";
        setError(msg);
      } finally {
        setIsRefreshing(false);
        setProgressStep(null);
      }
    },
    [loadDashboardData]
  );

  const initializeApp = useCallback(async () => {
    setLoading(true);
    setError(null);
    setProgressStep("Checking today's daily scan status...");

    try {
      await loadDashboardData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Today's scan could not be completed.";
      setError(msg);
    } finally {
      setLoading(false);
      setProgressStep(null);
    }
  }, [loadDashboardData]);

  useEffect(() => {
    initializeApp();
  }, [initializeApp]);

  // Derived counts for summary cards
  const evaluatedCount = dailyRanking?.evaluated_count ?? (legacyScan?.stocks_scanned ?? (statusData ? 49 : 0));
  const buyCount = dailyRanking?.buy_signal_count ?? (legacyScan?.buy_count ?? 0);
  const strongCount =
    dailyRanking?.results.filter(
      (r) => r.strength === 'VERY_STRONG' || r.strength === 'STRONG'
    ).length ?? 0;
  const watchlistCount = watchlistSetups.length;

  const allSignals: RankedSignal[] = dailyRanking?.results?.length
    ? dailyRanking.results
    : (legacyScan?.results || []).map((r, idx) => ({
        rank: idx + 1,
        symbol: r.symbol,
        company_name: r.company_name,
        signal_date: r.signal_date,
        score: r.signal === 'BUY' ? 1 : 0,
        strength: r.signal === 'BUY' ? 'STRONG' : 'NO_SIGNAL',
        tier: r.signal === 'BUY' ? 'STRONG_OPPORTUNITY' : 'WEAK_OR_NO_SIGNAL',
        buy_count: r.signal === 'BUY' ? 1 : 0,
        strategies_evaluated: 1,
        strategies_total: 5,
        buy_strategies: r.signal === 'BUY' ? [r.strategy_name] : [],
        hold_strategies: r.signal === 'HOLD' ? [r.strategy_name] : [],
        error_strategies: r.signal === 'ERROR' ? [r.strategy_name] : [],
        best_strategy_name: r.strategy_name,
        best_entry_price: r.entry_price,
        best_stop_loss: r.stop_loss,
        best_target_price: r.target_price,
        best_risk_reward: r.risk_reward,
      }));

  const scanDate = dailyRanking?.signal_date || legacyScan?.scan_date || statusData?.scan_date || 'Latest';
  const scanStatus = statusData?.status || (dailyRanking || legacyScan ? 'COMPLETED' : undefined);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans antialiased selection:bg-emerald-500/30 selection:text-emerald-200">
      {/* Header */}
      <Header
        scanDate={scanDate}
        universe={dailyRanking?.universe || legacyScan?.universe || 'NIFTY NEXT 50'}
        scanStatus={scanStatus}
        onRefresh={(force) => executeWorkflow(force)}
        isAlreadyCompleted={statusData?.already_completed || Boolean(dailyRanking || legacyScan)}
        isRefreshing={isRefreshing}
      />

      {/* Progress / Status Overlay Banner during scanning */}
      {isRefreshing && progressStep && (
        <div className="bg-gradient-to-r from-indigo-950/80 via-slate-900 to-indigo-950/80 border-b border-indigo-500/30 px-4 sm:px-8 py-2.5 text-center text-xs font-mono text-indigo-200 flex items-center justify-center gap-3 shadow-md">
          <svg className="animate-spin h-3.5 w-3.5 text-indigo-400" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span>{progressStep}</span>
        </div>
      )}

      {/* Main Dashboard Content */}
      <main className="w-full px-6 sm:px-10 pb-10 space-y-6">
        {/* Startup Loading State */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-24 text-center my-6 bg-slate-900/40 border border-slate-800 rounded-2xl space-y-3 shadow-xl">
            <div className="w-10 h-10 border-4 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin mb-2" />
            <h3 className="text-lg font-semibold text-slate-200">{progressStep || "Checking today's daily scan status..."}</h3>
            <p className="text-xs text-slate-400 max-w-md font-mono">
              Checking database status for today's completed daily scan run
            </p>
          </div>
        )}

        {/* Failure / Retry State */}
        {!loading && error && (
          <div className="bg-rose-950/20 border border-rose-500/30 rounded-2xl p-6 text-center my-6 max-w-lg mx-auto space-y-3 shadow-xl">
            <div className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-rose-500/10 text-rose-400">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div>
              <h3 className="text-base font-bold text-rose-200">Today's scan could not be completed.</h3>
              <p className="text-xs text-rose-300/80 mt-1 font-mono">{error}</p>
            </div>
            <button
              onClick={() => executeWorkflow(true)}
              className="bg-rose-600 hover:bg-rose-500 text-white font-medium text-xs px-5 py-2 rounded-xl transition-all cursor-pointer shadow-md shadow-rose-950 border border-rose-400/30"
            >
              Retry Scan
            </button>
          </div>
        )}

        {/* Dashboard Loaded Data */}
        {!loading && !error && (
          <div className="space-y-6">
            {/* 1. Summary Cards */}
            <SummaryCards
              evaluatedCount={evaluatedCount}
              buyCount={buyCount}
              strongCount={strongCount}
              watchlistCount={watchlistCount}
              watchCount={legacyScan?.watch_count ?? 0}
              holdCount={legacyScan?.hold_count ?? 0}
              skipCount={legacyScan?.skip_count ?? 0}
            />

            {/* 2. Today's Recommendations (Only Actionable BUY Setups) */}
            <TopSetupsTable
              signals={allSignals}
              selectedStrategyFilter={selectedStrategyFilter}
              onSelectStrategyFilter={setSelectedStrategyFilter}
              onSelectStock={(sig) => navigate(`/stocks/${sig.symbol}`)}
            />

            {/* 3. Market Scanner (All Universe Stocks) */}
            <MarketScannerTable
              signals={allSignals}
              onSelectStock={(sig) => navigate(`/stocks/${sig.symbol}`)}
            />

            {/* 4. Bottom Grid: Active Watchlist + Strategy Health */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <WatchlistPreview
                setups={watchlistSetups}
                onSelectStock={(sym) => navigate(`/stocks/${sym}`)}
                onOpenFullWatchlist={() => navigate('/watchlist')}
              />
              <StrategyPerformancePreview
                strategies={strategyAnalytics?.strategies || []}
              />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DashboardView />} />
        <Route path="/stocks/:symbol" element={<StockDetailView />} />
        <Route path="/watchlist" element={<WatchlistPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
