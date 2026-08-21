import React from 'react';
import type { ScanResult } from '../api/scanner';

interface BuySignalsTableProps {
  buyResults: ScanResult[];
  onSelectStock: (stock: ScanResult) => void;
}

export const BuySignalsTable: React.FC<BuySignalsTableProps> = ({
  buyResults,
  onSelectStock,
}) => {
  if (buyResults.length === 0) {
    return (
      <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-8 text-center my-6">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-slate-700/50 text-slate-400 mb-3">
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h3 className="text-base font-semibold text-slate-200">No BUY setups found today.</h3>
        <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
          The EMA Pullback strategy strictly enforces 8 trend, pullback, and volume setup filters. No stocks met all long entry conditions on the latest completed daily candle.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-slate-800/50 border border-emerald-500/30 rounded-xl overflow-hidden shadow-xl my-6 backdrop-blur-sm">
      <div className="px-6 py-4 border-b border-slate-700/60 bg-emerald-950/20 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            BUY Signals
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-mono font-bold border border-emerald-500/30">
              {buyResults.length}
            </span>
          </h2>
        </div>
        <span className="text-xs text-slate-400">Click a row to inspect trade parameters & setup reasons</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-900/60 text-slate-400 text-xs uppercase font-semibold border-b border-slate-700/60">
            <tr>
              <th className="px-6 py-3.5">Signal</th>
              <th className="px-6 py-3.5">Symbol</th>
              <th className="px-6 py-3.5">Company</th>
              <th className="px-6 py-3.5 text-right">Close</th>
              <th className="px-6 py-3.5 text-right">Entry</th>
              <th className="px-6 py-3.5 text-right">Stop Loss</th>
              <th className="px-6 py-3.5 text-right">Target</th>
              <th className="px-6 py-3.5 text-center">R:R</th>
              <th className="px-6 py-3.5 text-right">Signal Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/40 text-slate-200">
            {buyResults.map((stock) => (
              <tr
                key={stock.symbol}
                data-testid={`buy-row-${stock.symbol}`}
                onClick={() => onSelectStock(stock)}
                className="hover:bg-emerald-950/20 transition-colors cursor-pointer group"
              >
                <td className="px-6 py-4 whitespace-nowrap" onClick={() => onSelectStock(stock)}>
                  <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 group-hover:border-emerald-400">
                    BUY
                  </span>
                </td>
                <td
                  data-testid={`buy-symbol-${stock.symbol}`}
                  onClick={() => onSelectStock(stock)}
                  className="px-6 py-4 whitespace-nowrap font-bold text-white font-mono group-hover:text-emerald-300"
                >
                  {stock.symbol}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-slate-300 text-xs" onClick={() => onSelectStock(stock)}>
                  {stock.company_name || stock.symbol}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right font-mono font-medium" onClick={() => onSelectStock(stock)}>
                  {stock.close !== null && stock.close !== undefined ? `₹${stock.close.toFixed(2)}` : '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right font-mono font-medium text-emerald-400" onClick={() => onSelectStock(stock)}>
                  {stock.entry_price !== null && stock.entry_price !== undefined ? `₹${stock.entry_price.toFixed(2)}` : '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right font-mono font-medium text-rose-400" onClick={() => onSelectStock(stock)}>
                  {stock.stop_loss !== null && stock.stop_loss !== undefined ? `₹${stock.stop_loss.toFixed(2)}` : '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right font-mono font-medium text-teal-300" onClick={() => onSelectStock(stock)}>
                  {stock.target_price !== null && stock.target_price !== undefined ? `₹${stock.target_price.toFixed(2)}` : '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-center font-mono font-bold text-amber-300" onClick={() => onSelectStock(stock)}>
                  {stock.risk_reward !== null && stock.risk_reward !== undefined ? `${stock.risk_reward}:1` : '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-xs text-slate-400 font-mono" onClick={() => onSelectStock(stock)}>
                  {stock.signal_date || '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
