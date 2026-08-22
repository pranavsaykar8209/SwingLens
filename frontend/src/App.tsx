import { useCallback, useEffect, useState } from 'react';
import {
  fetchDailyScanStatus,
  fetchLatestScan,
  runDailyScanWorkflow,
  type DailyScanStatusResponse,
  type ScanResult,
  type ScanSummary,
} from './api/scanner';
import { AllStocksTable } from './components/AllStocksTable';
import { BuySignalsTable } from './components/BuySignalsTable';
import { Header } from './components/Header';
import { StockDetailView } from './components/StockDetailView';
import { SummaryCards } from './components/SummaryCards';

export function App() {
  const [data, setData] = useState<ScanSummary | null>(null);
  const [statusData, setStatusData] = useState<DailyScanStatusResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [progressStep, setProgressStep] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedStock, setSelectedStock] = useState<ScanResult | null>(null);

  const executeWorkflow = useCallback(async (force: boolean = false) => {
    setIsRefreshing(true);
    setError(null);

    try {
      setProgressStep("Checking market data...");
      await new Promise((r) => setTimeout(r, 150));

      setProgressStep("Updating Nifty Next 50 market data...");
      await new Promise((r) => setTimeout(r, 150));

      setProgressStep("Validating market candles...");
      await new Promise((r) => setTimeout(r, 150));

      setProgressStep("Running EMA Pullback scanner...");
      const summary = await runDailyScanWorkflow(force);
      setData(summary);

      const statusRes = await fetchDailyScanStatus();
      setStatusData(statusRes);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Today's scan could not be completed.";
      setError(msg);
    } finally {
      setIsRefreshing(false);
      setProgressStep(null);
    }
  }, []);

  const initializeApp = useCallback(async () => {
    setLoading(true);
    setError(null);
    setProgressStep("Checking today's daily scan status...");

    try {
      const statusRes = await fetchDailyScanStatus();
      setStatusData(statusRes);

      if (statusRes.already_completed) {
        // Today's scan already available -> immediately load existing scan results
        setProgressStep("Today's scan already available. Loading existing results...");
        const summary = await fetchLatestScan();
        setData(summary);
      } else {
        // Automatically start the daily workflow
        await executeWorkflow(false);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to initialize daily scan status.";
      setError(msg);
    } finally {
      setLoading(false);
      setProgressStep(null);
    }
  }, [executeWorkflow]);

  useEffect(() => {
    initializeApp();
  }, [initializeApp]);

  const buyResults = data?.results.filter((r) => r.signal === 'BUY') || [];

  // Render standalone Stock Detail view when a stock is selected
  if (selectedStock) {
    return (
      <StockDetailView
        stock={selectedStock}
        onBack={() => setSelectedStock(null)}
      />
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans antialiased selection:bg-emerald-500/30 selection:text-emerald-200">
      {/* Header */}
      <Header
        scanDate={data?.scan_date || statusData?.scan_date}
        universe={data?.universe}
        strategy={data?.strategy}
        strategyVersion={data?.strategy_version}
        onRefresh={(force) => executeWorkflow(force)}
        isAlreadyCompleted={statusData?.already_completed || false}
        isRefreshing={isRefreshing}
      />

      {/* Progress / Status Overlay Banner during scanning */}
      {isRefreshing && progressStep && (
        <div className="bg-gradient-to-r from-indigo-950/80 via-slate-900 to-indigo-950/80 border-b border-indigo-500/30 px-6 sm:px-10 py-3 text-center text-xs font-mono text-indigo-200 flex items-center justify-center gap-3 shadow-md">
          <svg className="animate-spin h-4 w-4 text-indigo-400" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span>{progressStep}</span>
        </div>
      )}

      {/* Full-Width Main Content Area */}
      <main className="w-full px-6 sm:px-10 py-8 space-y-8">
        {/* Startup Loading State */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-28 text-center my-8 bg-slate-900/40 border border-slate-800/80 rounded-2xl space-y-3 shadow-xl">
            <div className="w-12 h-12 border-4 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin mb-2" />
            <h3 className="text-xl font-semibold text-slate-200">{progressStep || "Preparing today's market scan..."}</h3>
            <p className="text-xs text-slate-400 max-w-md">
              Checking SQLite database status for today's completed daily scan run
            </p>
          </div>
        )}

        {/* Failure / Retry State */}
        {!loading && error && (
          <div className="bg-rose-950/20 border border-rose-500/30 rounded-2xl p-8 text-center my-8 max-w-xl mx-auto space-y-4 shadow-xl">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-rose-500/10 text-rose-400">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-bold text-rose-200">Today's scan could not be completed.</h3>
              <p className="text-xs text-rose-300/80 mt-1 font-mono">{error}</p>
            </div>
            <button
              onClick={() => executeWorkflow(true)}
              className="bg-rose-600 hover:bg-rose-500 text-white font-medium text-xs px-6 py-2.5 rounded-xl transition-all cursor-pointer shadow-lg shadow-rose-900/20 border border-rose-400/30"
            >
              Retry Scan
            </button>
          </div>
        )}

        {/* Dashboard Loaded Data */}
        {!loading && !error && data && (
          <div className="space-y-8">
            {/* Summary Cards */}
            <SummaryCards
              buyCount={data.buy_count}
              watchCount={data.watch_count}
              holdCount={data.hold_count}
              skipCount={data.skip_count}
            />

            {/* BUY Signals Table */}
            <BuySignalsTable
              buyResults={buyResults}
              onSelectStock={setSelectedStock}
            />

            {/* All Scanned Stocks Table */}
            <AllStocksTable
              results={data.results}
              onSelectStock={setSelectedStock}
            />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
