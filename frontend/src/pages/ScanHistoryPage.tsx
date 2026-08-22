import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import * as scannerApi from '../api/scanner';
import type { HistoricalScanSummary } from '../api/scanner';
import { Header } from '../components/Header';

export const ScanHistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const [history, setHistory] = useState<HistoricalScanSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadHistory() {
      setLoading(true);
      setError(null);
      try {
        const data = await scannerApi.fetchDailyScanHistory();
        setHistory(data);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to load scan history.';
        setError(msg);
      } finally {
        setLoading(false);
      }
    }
    loadHistory();
  }, []);

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr + 'T00:00:00');
      if (isNaN(d.getTime())) return dateStr;
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans antialiased pb-16">
      <Header onRefresh={() => {}} isRefreshing={false} />

      <main className="w-full px-6 sm:px-10 space-y-6">
        {/* Title Header */}
        <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 sm:p-8 shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white font-mono tracking-tight flex items-center gap-3">
              Scan History
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 font-mono font-medium">
                {history.length} Saved Scans
              </span>
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Review immutable historical daily market scans and recommendations without re-running strategies
            </p>
          </div>
        </div>

        {loading && (
          <div className="flex flex-col items-center justify-center py-24 text-center bg-slate-900/40 border border-slate-800/80 rounded-2xl space-y-3 shadow-xl">
            <div className="w-10 h-10 border-4 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin mb-2" />
            <h3 className="text-base font-semibold text-slate-200 font-mono">Loading Historical Scans...</h3>
          </div>
        )}

        {error && (
          <div className="p-6 bg-rose-950/20 border border-rose-500/30 rounded-2xl text-xs text-rose-300 font-mono text-center">
            {error}
          </div>
        )}

        {!loading && !error && (
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 sm:p-8 shadow-xl">
            <div className="overflow-x-auto rounded-xl border border-slate-800/80">
              <table className="w-full text-left border-collapse text-xs font-mono">
                <thead>
                  <tr className="bg-slate-800/50 border-b border-slate-700/60 text-slate-400 uppercase tracking-wider text-[11px]">
                    <th className="py-3.5 px-4">Scan Date</th>
                    <th className="py-3.5 px-3 text-center">Status</th>
                    <th className="py-3.5 px-3 text-center">Stocks Evaluated</th>
                    <th className="py-3.5 px-3 text-center">BUY Setups</th>
                    <th className="py-3.5 px-3 text-center">High Agreement</th>
                    <th className="py-3.5 px-4 text-center">Completed Time</th>
                    <th className="py-3.5 px-4 text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50 text-slate-200">
                  {history.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-12 text-center text-slate-400 font-sans">
                        No historical daily scans found in database. Run today's scan on the dashboard to create a persisted record.
                      </td>
                    </tr>
                  ) : (
                    history.map((scan) => (
                      <tr
                        key={scan.scan_date}
                        className="hover:bg-slate-800/40 transition-colors cursor-pointer"
                        onClick={() => navigate(`/scan-history/${scan.scan_date}`)}
                      >
                        <td className="py-3.5 px-4">
                          <span className="font-extrabold text-slate-100 text-sm hover:text-emerald-400 transition-colors">
                            {formatDate(scan.scan_date)}
                          </span>
                          <span className="block text-[10px] text-slate-500 font-mono">
                            {scan.scan_date}
                          </span>
                        </td>
                        <td className="py-3.5 px-3 text-center">
                          <span className="text-[10px] px-2.5 py-0.5 rounded-full border font-bold uppercase bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
                            {scan.status}
                          </span>
                        </td>
                        <td className="py-3.5 px-3 text-center font-bold text-slate-200">
                          {scan.stocks_evaluated}
                        </td>
                        <td className="py-3.5 px-3 text-center">
                          <span
                            className={`font-bold px-2 py-0.5 rounded border text-xs ${
                              scan.buy_setups > 0
                                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                                : 'bg-slate-800 text-slate-400 border-slate-700'
                            }`}
                          >
                            {scan.buy_setups}
                          </span>
                        </td>
                        <td className="py-3.5 px-3 text-center">
                          <span
                            className={`font-bold px-2 py-0.5 rounded border text-xs ${
                              scan.strong_signals > 0
                                ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30'
                                : 'bg-slate-800 text-slate-400 border-slate-700'
                            }`}
                          >
                            {scan.strong_signals}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-center text-slate-400 text-[11px]">
                          {scan.completed_at || '-'}
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/scan-history/${scan.scan_date}`);
                            }}
                            className="text-xs px-3.5 py-1.5 rounded-lg border bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white border-slate-700 font-semibold cursor-pointer transition-all shadow-sm"
                          >
                            View Scan
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};
