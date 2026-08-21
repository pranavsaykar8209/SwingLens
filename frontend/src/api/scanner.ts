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
