import React, { useEffect, useMemo, useState } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
  Legend,
} from 'recharts';
import {
  fetchStockHistory,
  type StockHistoryCandle,
  type ScanResult,
  type BacktestTrade,
} from '../api/scanner';

export type TimeframeRange = '3M' | '6M' | '1Y' | '3Y' | '5Y' | 'ALL';

interface StockPriceChartProps {
  stock: ScanResult;
  backtestTrades?: BacktestTrade[];
}

export const StockPriceChart: React.FC<StockPriceChartProps> = ({
  stock,
  backtestTrades = [],
}) => {
  const [candles, setCandles] = useState<StockHistoryCandle[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [range, setRange] = useState<TimeframeRange>('1Y');

  useEffect(() => {
    let isMounted = true;
    const loadHistory = async () => {
      setLoading(true);
      setError(null);
      try {
        // Fetch full history once so timeframe switching works instantly offline
        const res = await fetchStockHistory(stock.symbol);
        if (isMounted) {
          setCandles(res.data || []);
        }
      } catch (err: unknown) {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : 'Failed to load stock history.';
          setError(msg);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    loadHistory();
    return () => {
      isMounted = false;
    };
  }, [stock.symbol]);

  // Filter candles based on selected timeframe range
  const filteredData = useMemo(() => {
    if (!candles || candles.length === 0) return [];
    
    let sliceDays = 250; // Default ~1Y
    if (range === '3M') sliceDays = 65;
    else if (range === '6M') sliceDays = 125;
    else if (range === '1Y') sliceDays = 250;
    else if (range === '3Y') sliceDays = 750;
    else if (range === '5Y') sliceDays = 1250;
    else if (range === 'ALL') return candles;

    return candles.slice(-sliceDays);
  }, [candles, range]);

  // Calculate domain min & max with padding for clear price visualization
  const yDomain = useMemo(() => {
    if (filteredData.length === 0) return ['auto', 'auto'];
    let minP = Infinity;
    let maxP = -Infinity;

    filteredData.forEach((c) => {
      if (c.low < minP) minP = c.low;
      if (c.high > maxP) maxP = c.high;
      if (c.ema20 && c.ema20 < minP) minP = c.ema20;
      if (c.ema20 && c.ema20 > maxP) maxP = c.ema20;
      if (c.ema50 && c.ema50 < minP) minP = c.ema50;
      if (c.ema50 && c.ema50 > maxP) maxP = c.ema50;
      if (c.ema200 && c.ema200 < minP) minP = c.ema200;
      if (c.ema200 && c.ema200 > maxP) maxP = c.ema200;
    });

    if (stock.stop_loss && stock.stop_loss < minP) minP = stock.stop_loss;
    if (stock.target_price && stock.target_price > maxP) maxP = stock.target_price;

    const pad = (maxP - minP) * 0.05;
    return [Math.floor(minP - pad), Math.ceil(maxP + pad)];
  }, [filteredData, stock.stop_loss, stock.target_price]);

  if (loading) {
    return (
      <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-8 flex flex-col items-center justify-center min-h-[300px]">
        <svg className="animate-spin h-7 w-7 text-indigo-400 mb-3" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <span className="text-xs text-slate-400 font-mono">Loading historical price chart for {stock.symbol}...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-rose-950/20 border border-rose-500/30 rounded-xl p-4 text-xs text-rose-300 font-mono">
        <span className="font-bold block mb-1">Chart Data Error:</span>
        {error}
      </div>
    );
  }

  if (filteredData.length === 0) {
    return (
      <div className="bg-slate-800/30 border border-slate-700/40 rounded-xl p-6 text-xs text-slate-400 font-mono text-center">
        No historical daily price data available for {stock.symbol}.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Timeframe selector header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Historical Price & Indicator Chart
          </h3>
          <span className="text-[10px] text-slate-500 font-mono">
            ({filteredData.length} candles)
          </span>
        </div>

        <div className="flex items-center gap-1 bg-slate-800/80 border border-slate-700/60 rounded-lg p-1">
          {(['3M', '6M', '1Y', '3Y', '5Y', 'ALL'] as TimeframeRange[]).map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`px-2.5 py-1 text-[11px] font-mono font-semibold rounded-md transition-all cursor-pointer ${
                range === r
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {/* Chart Canvas Container */}
      <div className="bg-slate-950/70 border border-slate-800/80 rounded-xl p-4 sm:p-6 shadow-inner">
        <ResponsiveContainer width="100%" height={420}>
          <ComposedChart data={filteredData} margin={{ top: 15, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
            <XAxis
              dataKey="date"
              stroke="#64748b"
              fontSize={10}
              tickLine={false}
              minTickGap={30}
              fontFamily="monospace"
            />
            <YAxis
              domain={yDomain as [number, number]}
              stroke="#64748b"
              fontSize={10}
              tickLine={false}
              orientation="right"
              fontFamily="monospace"
              tickFormatter={(v: number) => `₹${v}`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#0f172a',
                borderColor: '#334155',
                borderRadius: '0.75rem',
                fontSize: '11px',
                fontFamily: 'monospace',
                color: '#f8fafc',
                boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)',
              }}
              formatter={(val: any) => {
                if (typeof val === 'number') {
                  return `₹${val.toFixed(2)}`;
                }
                return String(val);
              }}
            />
            <Legend
              verticalAlign="top"
              height={30}
              wrapperStyle={{ fontSize: '11px', fontFamily: 'monospace' }}
            />

            {/* Price Line */}
            <Line
              type="monotone"
              dataKey="close"
              name="Close Price"
              stroke="#f8fafc"
              strokeWidth={1.5}
              dot={false}
              activeDot={{ r: 4, stroke: '#38bdf8', strokeWidth: 2 }}
            />

            {/* EMA Lines */}
            <Line
              type="monotone"
              dataKey="ema20"
              name="EMA20"
              stroke="#10b981"
              strokeWidth={1.8}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="ema50"
              name="EMA50"
              stroke="#3b82f6"
              strokeWidth={1.8}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="ema200"
              name="EMA200"
              stroke="#a855f7"
              strokeWidth={1.8}
              dot={false}
            />

            {/* Current Signal Horizontal Levels */}
            {stock.entry_price && (
              <ReferenceLine
                y={stock.entry_price}
                stroke="#34d399"
                strokeDasharray="4 4"
                label={{
                  value: `Entry ₹${stock.entry_price.toFixed(2)}`,
                  fill: '#34d399',
                  fontSize: 10,
                  position: 'left',
                  fontFamily: 'monospace',
                }}
              />
            )}
            {stock.stop_loss && (
              <ReferenceLine
                y={stock.stop_loss}
                stroke="#f87171"
                strokeDasharray="4 4"
                label={{
                  value: `SL ₹${stock.stop_loss.toFixed(2)}`,
                  fill: '#f87171',
                  fontSize: 10,
                  position: 'left',
                  fontFamily: 'monospace',
                }}
              />
            )}
            {stock.target_price && (
              <ReferenceLine
                y={stock.target_price}
                stroke="#2dd4bf"
                strokeDasharray="4 4"
                label={{
                  value: `Target ₹${stock.target_price.toFixed(2)}`,
                  fill: '#2dd4bf',
                  fontSize: 10,
                  position: 'left',
                  fontFamily: 'monospace',
                }}
              />
            )}

            {/* Current Signal Date Marker */}
            {stock.signal_date && (
              <ReferenceLine
                x={stock.signal_date}
                stroke="#6366f1"
                strokeDasharray="3 3"
                label={{
                  value: `Signal (${stock.signal})`,
                  fill: '#818cf8',
                  fontSize: 10,
                  position: 'top',
                  fontFamily: 'monospace',
                }}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Legend & Indicator Quick Reference */}
      <div className="flex flex-wrap items-center justify-between text-[11px] text-slate-400 font-mono px-1">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block"></span>
            EMA20
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-500 inline-block"></span>
            EMA50
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-500 inline-block"></span>
            EMA200
          </span>
        </div>

        {backtestTrades.length > 0 && (
          <div className="text-slate-400">
            Historical Backtest Trades: <span className="text-indigo-300 font-bold">{backtestTrades.length}</span>
          </div>
        )}
      </div>
    </div>
  );
};
