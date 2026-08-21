import React, { useState } from 'react';
import type { ScanResult, ScanSignalType } from '../api/scanner';

interface AllStocksTableProps {
  results: ScanResult[];
  onSelectStock: (stock: ScanResult) => void;
}

export const AllStocksTable: React.FC<AllStocksTableProps> = ({
  results,
  onSelectStock,
}) => {
  const [filter, setFilter] = useState<'ALL' | ScanSignalType | 'SKIPPED'>('ALL');
  const [isExpanded, setIsExpanded] = useState(true);

  const filteredResults = results.filter((stock) => {
    if (filter === 'ALL') return true;
    if (filter === 'SKIPPED') return stock.signal === 'ERROR';
    return stock.signal === filter;
  });

  const getSignalBadge = (signal: ScanSignalType) => {
    switch (signal) {
      case 'BUY':
        return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40';
      case 'WATCH':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/40';
      case 'HOLD':
        return 'bg-slate-700/40 text-slate-300 border-slate-600/40';
      case 'ERROR':
        return 'bg-rose-500/20 text-rose-300 border-rose-500/40';
      default:
        return 'bg-slate-700/40 text-slate-300 border-slate-600/40';
    }
  };

  return (
    <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl overflow-hidden shadow-lg my-8 backdrop-blur-sm">
      {/* Table Header & Collapsible Toggle */}
      <div className="px-6 py-4 border-b border-slate-700/60 bg-slate-900/40 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-slate-400 hover:text-white transition-colors cursor-pointer"
          >
            <svg
              className={`w-5 h-5 transform transition-transform ${isExpanded ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            All Scanned Stocks
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-700/50 text-slate-300 font-mono font-medium">
              {results.length}
            </span>
          </h2>
        </div>

        {/* Filter Buttons */}
        {isExpanded && (
          <div className="flex flex-wrap items-center gap-1.5 bg-slate-900/60 p-1 rounded-lg border border-slate-700/50">
            {(['ALL', 'BUY', 'WATCH', 'HOLD', 'SKIPPED'] as const).map((type) => (
              <button
                key={type}
                onClick={() => setFilter(type)}
                className={`text-xs px-3 py-1 rounded-md font-medium transition-all cursor-pointer ${
                  filter === type
                    ? 'bg-slate-700 text-white shadow-sm font-bold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                {type}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Table Body */}
      {isExpanded && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-900/60 text-slate-400 text-xs uppercase font-semibold border-b border-slate-700/60">
              <tr>
                <th className="px-6 py-3">Symbol</th>
                <th className="px-6 py-3">Company</th>
                <th className="px-6 py-3">Signal</th>
                <th className="px-6 py-3 text-right">Close</th>
                <th className="px-6 py-3">Status / Reason</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/30 text-slate-300 text-xs">
              {filteredResults.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-slate-400">
                    No stocks match the selected filter ({filter}).
                  </td>
                </tr>
              ) : (
                filteredResults.map((stock) => (
                  <tr
                    key={stock.symbol}
                    onClick={() => onSelectStock(stock)}
                    className="hover:bg-slate-700/30 transition-colors cursor-pointer"
                  >
                    <td className="px-6 py-3.5 whitespace-nowrap font-bold text-white font-mono">
                      {stock.symbol}
                    </td>
                    <td className="px-6 py-3.5 whitespace-nowrap text-slate-300">
                      {stock.company_name || stock.symbol}
                    </td>
                    <td className="px-6 py-3.5 whitespace-nowrap">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold border ${getSignalBadge(stock.signal)}`}>
                        {stock.signal === 'ERROR' ? 'SKIPPED' : stock.signal}
                      </span>
                    </td>
                    <td className="px-6 py-3.5 whitespace-nowrap text-right font-mono font-medium">
                      {stock.close !== null && stock.close !== undefined ? `₹${stock.close.toFixed(2)}` : '-'}
                    </td>
                    <td className="px-6 py-3.5 text-slate-400 truncate max-w-xs font-mono">
                      {stock.error || stock.reason || '-'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
