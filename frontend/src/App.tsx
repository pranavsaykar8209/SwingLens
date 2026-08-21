import { useCallback, useEffect, useState } from 'react';
import { fetchLatestScan, type ScanResult, type ScanSummary } from './api/scanner';
import { AllStocksTable } from './components/AllStocksTable';
import { BuySignalsTable } from './components/BuySignalsTable';
import { Header } from './components/Header';
import { StockDetailModal } from './components/StockDetailModal';
import { SummaryCards } from './components/SummaryCards';

export function App() {
  const [data, setData] = useState<ScanSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedStock, setSelectedStock] = useState<ScanResult | null>(null);

  const loadScan = useCallback(async (isManualRefresh: boolean = false) => {
    if (isManualRefresh) {
      setIsRefreshing(true);
    } else {
      setLoading(true);
    }
    setError(null);

    try {
      const summary = await fetchLatestScan('ema_pullback', 'NIFTY_NEXT_50');
      setData(summary);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unable to load today's scan.";
      setError(msg);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadScan();
  }, [loadScan]);

  const buyResults = data?.results.filter((r) => r.signal === 'BUY') || [];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans antialiased selection:bg-emerald-500/30 selection:text-emerald-200">
      {/* Header */}
      <Header
        scanDate={data?.scan_date}
        universe={data?.universe}
        strategy={data?.strategy}
        strategyVersion={data?.strategy_version}
        onRefresh={() => loadScan(true)}
        isRefreshing={isRefreshing}
      />

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-4 sm:px-8 py-6">
        {/* Loading State */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-24 text-center my-8 bg-slate-900/40 border border-slate-800/80 rounded-2xl">
            <div className="w-10 h-10 border-4 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin mb-4" />
            <h3 className="text-lg font-semibold text-slate-200">Loading today's scan...</h3>
            <p className="text-xs text-slate-400 mt-1">Executing EMA Pullback v1.0 strategy against Nifty Next 50 database candles</p>
          </div>
        )}

        {/* Error State */}
        {!loading && error && (
          <div className="bg-rose-950/20 border border-rose-500/30 rounded-2xl p-8 text-center my-8 max-w-xl mx-auto">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-rose-500/10 text-rose-400 mb-3">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h3 className="text-lg font-bold text-rose-200">Unable to load today's scan.</h3>
            <p className="text-xs text-rose-300/80 mt-1 mb-5">{error}</p>
            <button
              onClick={() => loadScan(false)}
              className="bg-rose-600 hover:bg-rose-500 text-white font-medium text-xs px-5 py-2.5 rounded-xl transition-all cursor-pointer shadow-lg shadow-rose-900/20"
            >
              Retry
            </button>
          </div>
        )}

        {/* Dashboard Loaded Data */}
        {!loading && !error && data && (
          <div>
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

      {/* Stock Detail Modal */}
      <StockDetailModal
        stock={selectedStock}
        onClose={() => setSelectedStock(null)}
      />
    </div>
  );
}

export default App;
