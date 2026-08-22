/**
 * API Service layer for SwingLens frontend.
 * Includes in-flight request deduplication to prevent duplicate HTTP calls during React StrictMode / mounts.
 */
import type {
  AggregatedSignalResult,
  DailyScanStatusResponse,
  DailySignalRanking,
  HistoricalScanSummary,
  ScanSummary,
  SingleStockBacktestResult,
  StockHistoryResponse,
  StrategyAnalyticsResponse,
  WatchlistSetup,
} from './types';

export * from './types';

// In-flight promise map for deduplication of concurrent identical GET requests
const inFlightRequests = new Map<string, Promise<any>>();

export function resetApiCache(): void {
  inFlightRequests.clear();
}

async function apiGet<T>(url: string): Promise<T> {
  if (inFlightRequests.has(url)) {
    return inFlightRequests.get(url)!;
  }

  const promise = (async () => {
    try {
      const response = await fetch(url, {
        headers: {
          Accept: 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `API request to ${url} failed with HTTP ${response.status}`);
      }

      return await response.json();
    } finally {
      inFlightRequests.delete(url);
    }
  })();

  inFlightRequests.set(url, promise);
  return promise;
}

/**
 * Fetches daily scan status metadata (whether scan completed today).
 */
export async function fetchDailyScanStatus(
  universe: string = 'NIFTY_NEXT_50',
  strategy: string = 'ema_pullback'
): Promise<DailyScanStatusResponse> {
  const url = `/api/daily-scan/status?universe=${encodeURIComponent(universe)}&strategy=${encodeURIComponent(strategy)}`;
  return apiGet<DailyScanStatusResponse>(url);
}

/**
 * Executes the daily scan workflow (force=false for idempotent startup check, force=true for manual override).
 */
export async function runDailyScanWorkflow(
  force: boolean = false,
  universe: string = 'NIFTY_NEXT_50',
  strategy: string = 'ema_pullback'
): Promise<ScanSummary> {
  const url = `/api/daily-scan/run?force=${force}&universe=${encodeURIComponent(universe)}&strategy=${encodeURIComponent(strategy)}`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Daily scan workflow API returned HTTP ${response.status}`);
  }

  return await response.json();
}

/**
 * Fetches the latest daily market scan results for a single strategy.
 */
export async function fetchLatestScan(
  strategy: string = 'ema_pullback',
  index: string = 'NIFTY_NEXT_50'
): Promise<ScanSummary> {
  const url = `/api/scanner/latest?strategy=${encodeURIComponent(strategy)}&index=${encodeURIComponent(index)}`;
  return apiGet<ScanSummary>(url);
}

/**
 * Fetches today's multi-strategy daily signal ranking and top setups (read-only from SQLite).
 */
export async function fetchDailySignals(
  limit: number = 50,
  index: string = 'NIFTY_NEXT_50'
): Promise<DailySignalRanking> {
  const url = `/api/daily-signals?index=${encodeURIComponent(index)}&limit=${limit}`;
  return apiGet<DailySignalRanking>(url);
}

/**
 * Fetches list of historical daily scan run summaries (read-only).
 */
export async function fetchDailyScanHistory(limit: number = 100): Promise<HistoricalScanSummary[]> {
  const url = `/api/daily-signals/history?limit=${limit}`;
  return apiGet<HistoricalScanSummary[]>(url);
}

/**
 * Fetches persisted multi-strategy ranking snapshot for a specific historical date.
 */
export async function fetchHistoricalDailySignals(
  scanDate: string,
  limit?: number,
  index: string = 'NIFTY_NEXT_50'
): Promise<DailySignalRanking> {
  let url = `/api/daily-signals/${encodeURIComponent(scanDate)}?index=${encodeURIComponent(index)}`;
  if (limit) {
    url += `&limit=${limit}`;
  }
  return apiGet<DailySignalRanking>(url);
}

/**
 * Fetches aggregated multi-strategy signals and individual votes for a specific stock.
 */
export async function fetchAggregatedSignals(
  symbol: string,
  strategies?: string
): Promise<AggregatedSignalResult> {
  let url = `/api/aggregator/${encodeURIComponent(symbol)}`;
  if (strategies) {
    url += `?strategies=${encodeURIComponent(strategies)}`;
  }
  return apiGet<AggregatedSignalResult>(url);
}

/**
 * Fetches active watchlist setups.
 */
export async function fetchActiveWatchlist(): Promise<WatchlistSetup[]> {
  const url = `/api/watchlist?status=ACTIVE`;
  return apiGet<WatchlistSetup[]>(url);
}

/**
 * Fetches strategy historical quality analytics.
 */
export async function fetchStrategyAnalytics(
  symbols?: string
): Promise<StrategyAnalyticsResponse> {
  let url = `/api/analytics/strategies`;
  if (symbols) {
    url += `?symbols=${encodeURIComponent(symbols)}`;
  }
  return apiGet<StrategyAnalyticsResponse>(url);
}

/**
 * Fetches historical price candles and EMA indicators for a single stock.
 */
export async function fetchStockHistory(
  symbol: string,
  days?: number
): Promise<StockHistoryResponse> {
  let url = `/api/stocks/${encodeURIComponent(symbol)}/history`;
  if (days && days > 0) {
    url += `?days=${days}`;
  }
  return apiGet<StockHistoryResponse>(url);
}

/**
 * Fetches on-demand single-stock backtest results from FastAPI backend.
 */
export async function fetchSingleStockBacktest(
  symbol: string,
  strategy: string = 'ema_pullback',
  startDate?: string,
  endDate?: string
): Promise<SingleStockBacktestResult> {
  let url = `/api/backtest/${encodeURIComponent(symbol)}?strategy=${encodeURIComponent(strategy)}`;
  if (startDate) url += `&start_date=${encodeURIComponent(startDate)}`;
  if (endDate) url += `&end_date=${encodeURIComponent(endDate)}`;
  return apiGet<SingleStockBacktestResult>(url);
}

/**
 * Fetches on-demand single-stock backtest results from FastAPI backend.
 */
export const AVAILABLE_STRATEGIES = [
  { key: 'ema_pullback', name: 'EMA Pullback', version: '1.0' },
  { key: 'ma_trend_breakout', name: 'MA Trend Breakout', version: '1.0' },
  { key: 'rsi_mean_reversion', name: 'RSI Mean-Reversion', version: '1.0' },
  { key: 'macd_momentum', name: 'MACD Momentum', version: '1.0' },
  { key: 'bollinger_squeeze', name: 'Bollinger Squeeze', version: '1.0' },
];

/**
 * Runs single-stock backtest across all 5 strategies concurrently.
 */
export async function fetchAllStrategiesBacktest(
  symbol: string,
  startDate?: string,
  endDate?: string
): Promise<Record<string, SingleStockBacktestResult>> {
  const results: Record<string, SingleStockBacktestResult> = {};
  await Promise.all(
    AVAILABLE_STRATEGIES.map(async (strat) => {
      try {
        const res = await fetchSingleStockBacktest(symbol, strat.key, startDate, endDate);
        results[strat.key] = res;
      } catch (err) {
        console.error(`Backtest for ${strat.name} failed:`, err);
      }
    })
  );
  return results;
}
