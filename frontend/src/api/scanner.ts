export type ScanSignalType = 'BUY' | 'WATCH' | 'HOLD' | 'ERROR';

export interface ScanResult {
  symbol: string;
  company_name?: string | null;
  signal: ScanSignalType;
  signal_date?: string | null;
  close?: number | null;
  entry_price?: number | null;
  stop_loss?: number | null;
  target_price?: number | null;
  risk_reward?: number | null;
  score?: number | null;
  strategy_name: string;
  strategy_version: string;
  reason?: string | null;
  metadata?: Record<string, unknown>;
  error?: string | null;
  status: string;
}

export interface ScanSummary {
  scan_date: string;
  universe: string;
  strategy: string;
  strategy_version: string;
  stocks_scanned: number;
  buy_count: number;
  watch_count: number;
  hold_count: number;
  skip_count: number;
  results: ScanResult[];
}

export interface DailyScanStatusResponse {
  scan_date: string;
  already_completed: boolean;
  status: 'COMPLETED' | 'NOT_RUN' | 'RUNNING' | 'FAILED';
  latest_market_date?: string | null;
  last_completed_at?: string | null;
  buy_count: number;
  watch_count: number;
  hold_count: number;
  skipped_count: number;
  error_message?: string | null;
}

export interface BacktestTrade {
  trade_id?: string;
  symbol: string;
  strategy_name: string;
  strategy_version: string;
  signal_date: string;
  entry_date: string;
  entry_price: number;
  stop_loss?: number | null;
  target_price?: number | null;
  exit_date: string;
  exit_price: number;
  exit_reason: string;
  pnl_points: number;
  pnl_percent: number;
  r_multiple?: number | null;
  holding_days: number;
  status: string;
}

export interface SingleStockBacktestResult {
  symbol: string;
  strategy_name: string;
  strategy_version: string;
  start_date: string;
  end_date: string;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  open_trades: number;
  win_rate: number;
  average_win_percent: number;
  average_loss_percent: number;
  average_trade_percent: number;
  profit_factor: number;
  max_drawdown_percent: number;
  average_holding_days: number;
  maximum_holding_days: number;
  average_r_multiple: number;
  total_r: number;
  winning_r: number;
  losing_r: number;
  ambiguity_policy_note?: string;
  trades: BacktestTrade[];
  warnings?: string[];
}

export interface StockHistoryCandle {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ema20?: number | null;
  ema50?: number | null;
  ema200?: number | null;
}

export interface StockHistoryResponse {
  symbol: string;
  data: StockHistoryCandle[];
}

/**
 * Fetches daily scan status metadata (whether scan completed today).
 */
export async function fetchDailyScanStatus(
  universe: string = 'NIFTY_NEXT_50',
  strategy: string = 'ema_pullback'
): Promise<DailyScanStatusResponse> {
  const url = `/api/daily-scan/status?universe=${encodeURIComponent(universe)}&strategy=${encodeURIComponent(strategy)}`;

  const response = await fetch(url, {
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Daily scan status API returned HTTP ${response.status}`);
  }

  return await response.json();
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
 * Fetches the latest daily market scan results from FastAPI backend.
 */
export async function fetchLatestScan(
  strategy: string = 'ema_pullback',
  index: string = 'NIFTY_NEXT_50'
): Promise<ScanSummary> {
  const url = `/api/scanner/latest?strategy=${encodeURIComponent(strategy)}&index=${encodeURIComponent(index)}`;
  
  const response = await fetch(url, {
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Scanner API returned HTTP ${response.status}`);
  }

  const data: ScanSummary = await response.json();
  return data;
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

  const response = await fetch(url, {
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `History API returned HTTP ${response.status}`);
  }

  return await response.json();
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

  const response = await fetch(url, {
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Backtest API returned HTTP ${response.status}`);
  }

  return await response.json();
}
