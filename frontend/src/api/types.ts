/**
 * TypeScript type definitions for SwingLens API models.
 */

export type ScanSignalType = 'BUY' | 'WATCH' | 'HOLD' | 'ERROR';

export type SignalStrengthType = 'VERY_STRONG' | 'STRONG' | 'MODERATE' | 'WEAK' | 'NO_SIGNAL';

export type SignalTierType = 'STRONG_OPPORTUNITY' | 'MODERATE_OPPORTUNITY' | 'WEAK_OR_NO_SIGNAL';

export type WatchlistStatusType = 'ACTIVE' | 'EXPIRED' | 'TRIGGERED' | 'CANCELLED';

export type WatchlistOutcomeType = 'PENDING' | 'ENTRY_REACHED' | 'TARGET_HIT' | 'STOP_HIT' | 'AMBIGUOUS' | 'EXPIRED' | 'NO_ENTRY';

export type StrategyQualityClassificationType = 'POSITIVE' | 'NEUTRAL' | 'NEGATIVE' | 'INSUFFICIENT_DATA';

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

export interface HistoricalScanSummary {
  scan_date: string;
  status: string;
  stocks_evaluated: number;
  buy_setups: number;
  strong_signals: number;
  completed_at?: string | null;
}

export interface RankedSignal {
  rank: number;
  symbol: string;
  company_name?: string | null;
  signal_date?: string | null;
  score: number;
  strength: SignalStrengthType;
  tier: SignalTierType;
  buy_count: number;
  strategies_evaluated: number;
  strategies_total: number;
  buy_strategies: string[];
  hold_strategies: string[];
  error_strategies: string[];
  best_strategy_name?: string | null;
  best_entry_price?: number | null;
  best_stop_loss?: number | null;
  best_target_price?: number | null;
  best_risk_reward?: number | null;
}

export interface DailySignalRanking {
  signal_date?: string | null;
  universe: string;
  universe_size: number;
  evaluated_count: number;
  excluded_count: number;
  buy_signal_count: number;
  results: RankedSignal[];
  shortlist: RankedSignal[];
}

export interface StrategyVote {
  strategy_name: string;
  strategy_version: string;
  signal: string;
  entry_price?: number | null;
  stop_loss?: number | null;
  target_price?: number | null;
  risk_reward?: number | null;
  reason?: string | null;
  error?: string | null;
}

export interface AggregatedSignalResult {
  symbol: string;
  signal_date?: string | null;
  strategies_evaluated: number;
  strategies_total: number;
  buy_count: number;
  hold_count: number;
  score: number;
  strength: SignalStrengthType;
  buy_strategies: string[];
  hold_strategies: string[];
  error_strategies: string[];
  best_entry_price?: number | null;
  best_stop_loss?: number | null;
  best_target_price?: number | null;
  best_risk_reward?: number | null;
  best_strategy_name?: string | null;
  votes: StrategyVote[];
  metadata?: Record<string, unknown>;
}

export interface WatchlistSetup {
  id: number;
  stock_id: number;
  symbol: string;
  company_name?: string | null;
  strategy_name: string;
  strategy_version: string;
  signal_date: string;
  entry_price: number;
  stop_loss: number;
  target_price: number;
  risk_reward: number;
  score?: number | null;
  strength?: string | null;
  notes?: string | null;
  status: WatchlistStatusType;
  outcome: WatchlistOutcomeType;
  realized_r?: number | null;
  holding_days?: number | null;
  mfe_r?: number | null;
  mae_r?: number | null;
  created_at?: string;
  outcome_checked_at?: string | null;
}

export interface StrategyQualityMetrics {
  strategy_name: string;
  strategy_version: string;
  classification: StrategyQualityClassificationType;
  classification_reason: string;
  trades: number;
  wins: number;
  losses: number;
  win_rate: number;
  average_r: number;
  total_r: number;
  profit_factor: number;
  max_drawdown: number;
  average_holding_days: number;
  target_hit_rate: number;
  stop_hit_rate: number;
  ambiguous_rate: number;
  average_mfe_r: number;
  average_mae_r: number;
  stocks_tested: number;
}

export interface StrategyAnalyticsResponse {
  start_date?: string | null;
  end_date?: string | null;
  symbols: string[];
  strategies: StrategyQualityMetrics[];
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
