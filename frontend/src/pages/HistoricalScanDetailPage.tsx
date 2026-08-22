import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import * as scannerApi from '../api/scanner';
import type { DailySignalRanking } from '../api/scanner';
import { Header } from '../components/Header';
import { MarketScannerTable } from '../components/MarketScannerTable';
import { SummaryCards } from '../components/SummaryCards';
import { TopSetupsTable } from '../components/TopSetupsTable';

interface HistoricalScanDetailPageProps {
  scanDate?: string;
}

export const HistoricalScanDetailPage: React.FC<HistoricalScanDetailPageProps> = ({
  scanDate: scanDateProp,
}) => {
  const params = useParams<{ scanDate: string }>();
  const scanDate = scanDateProp || params.scanDate;
  const navigate = useNavigate();

  const [ranking, setRanking] = useState<DailySignalRanking | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedStrategyFilter, setSelectedStrategyFilter] = useState<string>('ALL');

  useEffect(() => {
    async function loadSnapshot() {
      if (!scanDate) return;
      setLoading(true);
      setError(null);
      try {
        const data = await scannerApi.fetchHistoricalDailySignals(scanDate);
        setRanking(data);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : `Failed to load historical scan for date ${scanDate}.`;
        setError(msg);
      } finally {
        setLoading(false);
      }
    }
    loadSnapshot();
  }, [scanDate]);

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'Unknown Date';
    try {
      const d = new Date(dateStr + 'T00:00:00');
      if (isNaN(d.getTime())) return dateStr;
      return d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
    } catch {
      return dateStr;
    }
  };

  const buyCount = ranking?.buy_signal_count ?? 0;
  const strongCount =
    ranking?.results.filter(
      (r) => r.strength === 'VERY_STRONG' || r.strength === 'STRONG'
    ).length ?? 0;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans antialiased pb-16">
      <Header scanDate={scanDate} onRefresh={() => {}} isRefreshing={false} />

      <main className="w-full px-6 sm:px-10 space-y-6">
        {/* Navigation back bar */}
        <div className="flex items-center justify-between">
          <button
            onClick={() => navigate('/scan-history')}
            className="group flex items-center gap-2 text-xs font-semibold text-slate-300 hover:text-white bg-slate-900 hover:bg-slate-800 px-3.5 py-2 rounded-xl border border-slate-800 transition-all cursor-pointer shadow-sm"
          >
            <svg className="w-4 h-4 transition-transform group-hover:-translate-x-1 text-slate-400 group-hover:text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Scan History
          </button>

          <span className="text-xs px-3 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700 font-mono font-semibold">
            Immutable Historical Snapshot
          </span>
        </div>

        {/* Title Header */}
        <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 sm:p-8 shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white font-mono tracking-tight flex items-center gap-3">
              Daily Scan — {formatDate(scanDate)}
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 font-mono font-medium">
                {ranking?.universe || 'NIFTY NEXT 50'}
              </span>
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Exact quantitative recommendations and multi-strategy agreement ratings recorded on {scanDate}
            </p>
          </div>
        </div>

        {loading && (
          <div className="flex flex-col items-center justify-center py-24 text-center bg-slate-900/40 border border-slate-800/80 rounded-2xl space-y-3 shadow-xl">
            <div className="w-10 h-10 border-4 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin mb-2" />
            <h3 className="text-base font-semibold text-slate-200 font-mono">Loading Historical Snapshot...</h3>
          </div>
        )}

        {error && (
          <div className="p-6 bg-rose-950/20 border border-rose-500/30 rounded-2xl text-xs text-rose-300 font-mono text-center">
            {error}
          </div>
        )}

        {!loading && !error && ranking && (
          <div className="space-y-6">
            {/* 1. Summary Cards */}
            <SummaryCards
              evaluatedCount={ranking.evaluated_count}
              buyCount={buyCount}
              strongCount={strongCount}
              watchlistCount={0}
            />

            {/* 2. Today's Recommendations (Filtered to Actionable BUY Setups on that Date) */}
            <TopSetupsTable
              signals={ranking.results}
              selectedStrategyFilter={selectedStrategyFilter}
              onSelectStrategyFilter={setSelectedStrategyFilter}
              onSelectStock={(sig) => navigate(`/stocks/${sig.symbol}`)}
            />

            {/* 3. Market Scanner (All Universe Stocks for that Date) */}
            <MarketScannerTable
              signals={ranking.results}
              onSelectStock={(sig) => navigate(`/stocks/${sig.symbol}`)}
            />
          </div>
        )}
      </main>
    </div>
  );
};
