import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from '../App';
import * as scannerApi from '../api/scanner';
import type {
  AggregatedSignalResult,
  DailyScanStatusResponse,
  DailySignalRanking,
  RankedSignal,
  StrategyAnalyticsResponse,
  WatchlistSetup,
} from '../api/types';
import { StrategyPerformancePreview } from '../components/StrategyPerformancePreview';
import { StrengthBadge } from '../components/StrengthBadge';
import { TopSetupsTable } from '../components/TopSetupsTable';
import { WatchlistPreview } from '../components/WatchlistPreview';

const mockRankedSignals: RankedSignal[] = [
  {
    rank: 1,
    symbol: 'HDFCAMC',
    company_name: 'HDFC Asset Management Company Ltd.',
    signal_date: '2026-08-20',
    score: 4,
    strength: 'STRONG',
    tier: 'STRONG_OPPORTUNITY',
    buy_count: 4,
    strategies_evaluated: 5,
    strategies_total: 5,
    buy_strategies: ['EMA Pullback', 'MA Trend Breakout', 'MACD Momentum', 'Bollinger Squeeze'],
    hold_strategies: ['RSI Mean-Reversion'],
    error_strategies: [],
    best_strategy_name: 'EMA Pullback',
    best_entry_price: 4250.0,
    best_stop_loss: 4100.0,
    best_target_price: 4550.0,
    best_risk_reward: 2.0,
  },
  {
    rank: 2,
    symbol: 'BANKBARODA',
    company_name: 'Bank of Baroda',
    signal_date: '2026-08-20',
    score: 1,
    strength: 'NO_SIGNAL',
    tier: 'WEAK_OR_NO_SIGNAL',
    buy_count: 1,
    strategies_evaluated: 5,
    strategies_total: 5,
    buy_strategies: ['Bollinger Squeeze'],
    hold_strategies: ['EMA Pullback', 'MA Trend Breakout', 'RSI Mean-Reversion', 'MACD Momentum'],
    error_strategies: [],
    best_strategy_name: 'Bollinger Squeeze',
    best_entry_price: 250.0,
    best_stop_loss: 240.0,
    best_target_price: 270.0,
    best_risk_reward: 2.0,
  },
];

const mockDailyRanking: DailySignalRanking = {
  signal_date: '2026-08-20',
  universe: 'NIFTY_NEXT_50',
  universe_size: 49,
  evaluated_count: 49,
  excluded_count: 0,
  buy_signal_count: 2,
  results: mockRankedSignals,
  shortlist: mockRankedSignals,
};

const mockWatchlistSetups: WatchlistSetup[] = [
  {
    id: 1,
    stock_id: 10,
    symbol: 'HDFCAMC',
    company_name: 'HDFC Asset Management Company Ltd.',
    strategy_name: 'EMA Pullback',
    strategy_version: '1.0',
    signal_date: '2026-08-20',
    status: 'ACTIVE',
    score: 4,
    strength: 'STRONG',
    entry_price: 4250.0,
    stop_loss: 4100.0,
    target_price: 4550.0,
    risk_reward: 2.0,
    outcome: 'PENDING',
    holding_days: null,
    mfe_r: null,
    mae_r: null,
    realized_r: null,
    created_at: '2026-08-20T15:30:00',
  },
];

const mockStrategyAnalytics: StrategyAnalyticsResponse = {
  strategies: [
    {
      strategy_name: 'EMA Pullback',
      strategy_version: '1.0',
      trades: 42,
      wins: 26,
      losses: 16,
      win_rate: 61.9,
      average_r: 0.12,
      total_r: 5.04,
      profit_factor: 1.65,
      max_drawdown: 3.8,
      average_holding_days: 8.4,
      target_hit_rate: 59.5,
      stop_hit_rate: 38.1,
      ambiguous_rate: 0.0,
      average_mfe_r: 1.45,
      average_mae_r: -0.55,
      classification: 'POSITIVE',
      classification_reason: 'Total R > 0 and Profit Factor >= 1.0',
      stocks_tested: 5,
    },
    {
      strategy_name: 'Bollinger Squeeze',
      strategy_version: '1.0',
      trades: 20,
      wins: 8,
      losses: 12,
      win_rate: 40.0,
      average_r: -0.27,
      total_r: -5.4,
      profit_factor: 0.72,
      max_drawdown: 7.2,
      average_holding_days: 6.1,
      target_hit_rate: 35.0,
      stop_hit_rate: 60.0,
      ambiguous_rate: 0.0,
      average_mfe_r: 0.85,
      average_mae_r: -0.92,
      classification: 'NEGATIVE',
      classification_reason: 'Total R < 0 and Profit Factor < 1.0',
      stocks_tested: 5,
    },
  ],
  symbols: ['ABB', 'HDFCAMC'],
};

const mockStatusResponse: DailyScanStatusResponse = {
  scan_date: '2026-08-20',
  already_completed: true,
  status: 'COMPLETED',
  latest_market_date: '2026-08-20',
  last_completed_at: '2026-08-20T16:00:00',
  buy_count: 2,
  watch_count: 0,
  hold_count: 47,
  skipped_count: 0,
  error_message: null,
};

const mockAggregatedSignal: AggregatedSignalResult = {
  symbol: 'HDFCAMC',
  signal_date: '2026-08-20',
  score: 4,
  strength: 'STRONG',
  buy_count: 4,
  hold_count: 1,
  strategies_evaluated: 5,
  strategies_total: 5,
  best_strategy_name: 'EMA Pullback',
  best_entry_price: 4250.0,
  best_stop_loss: 4100.0,
  best_target_price: 4550.0,
  best_risk_reward: 2.0,
  buy_strategies: ['EMA Pullback', 'MA Trend Breakout', 'MACD Momentum', 'Bollinger Squeeze'],
  hold_strategies: ['RSI Mean-Reversion'],
  error_strategies: [],
  votes: [
    {
      strategy_name: 'EMA Pullback',
      strategy_version: '1.0',
      signal: 'BUY',
      entry_price: 4250.0,
      stop_loss: 4100.0,
      target_price: 4550.0,
      risk_reward: 2.0,
      reason: 'EMA pullback setup confirmed',
    },
  ],
};

describe('Daily Recommendation Dashboard Component Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.history.pushState({}, '', '/');
  });

  it('1. Renders StrengthBadge correctly for all signal tiers', () => {
    const { unmount } = render(<StrengthBadge strength="VERY_STRONG" />);
    expect(screen.getByText('VERY STRONG')).toBeInTheDocument();
    unmount();

    render(<StrengthBadge strength="STRONG" />);
    expect(screen.getByText('STRONG')).toBeInTheDocument();

    render(<StrengthBadge strength="MODERATE" />);
    expect(screen.getByText('MODERATE')).toBeInTheDocument();

    render(<StrengthBadge strength="NO_SIGNAL" />);
    expect(screen.getByText('NO SIGNAL')).toBeInTheDocument();
  });

  it('2. Renders TopSetupsTable with accurate ranking columns', () => {
    const handleSelect = vi.fn();
    render(
      <TopSetupsTable
        signals={mockRankedSignals}
        selectedStrategyFilter="ALL"
        onSelectStrategyFilter={() => {}}
        onSelectStock={handleSelect}
      />
    );

    expect(screen.getByText("Today's Recommendations")).toBeInTheDocument();
    expect(screen.getByText('HDFCAMC')).toBeInTheDocument();
    expect(screen.getByText('BANKBARODA')).toBeInTheDocument();
    expect(screen.getByText('4/5')).toBeInTheDocument();
    expect(screen.getByText('₹4250.00')).toBeInTheDocument();
    expect(screen.getByText('₹4100.00')).toBeInTheDocument();
    expect(screen.getByText('₹4550.00')).toBeInTheDocument();

    fireEvent.click(screen.getByText('HDFCAMC'));
    expect(handleSelect).toHaveBeenCalledWith(mockRankedSignals[0]);
  });

  it('3. Filters TopSetupsTable when a specific strategy is selected', () => {
    const { rerender } = render(
      <TopSetupsTable
        signals={mockRankedSignals}
        selectedStrategyFilter="MA Trend Breakout"
        onSelectStrategyFilter={() => {}}
        onSelectStock={() => {}}
      />
    );

    // HDFCAMC has MA Trend Breakout, BANKBARODA does not
    expect(screen.getByText('HDFCAMC')).toBeInTheDocument();
    expect(screen.queryByText('BANKBARODA')).not.toBeInTheDocument();

    // Rerender with non-matching strategy
    rerender(
      <TopSetupsTable
        signals={mockRankedSignals}
        selectedStrategyFilter="RSI Mean-Reversion"
        onSelectStrategyFilter={() => {}}
        onSelectStock={() => {}}
      />
    );
    expect(screen.getByText('No Actionable Recommendations Today')).toBeInTheDocument();
  });

  it('4. Renders WatchlistPreview with active setups', () => {
    render(<WatchlistPreview setups={mockWatchlistSetups} />);
    expect(screen.getByText('Active Watchlist')).toBeInTheDocument();
    expect(screen.getByText('1 Monitored')).toBeInTheDocument();
    expect(screen.getByText('HDFCAMC')).toBeInTheDocument();
    expect(screen.getByText('PENDING')).toBeInTheDocument();
  });

  it('5. Renders StrategyPerformancePreview with historical metrics', () => {
    render(<StrategyPerformancePreview strategies={mockStrategyAnalytics.strategies} />);
    expect(screen.getByText('Strategy Health')).toBeInTheDocument();
    expect(screen.getByText('EMA Pullback')).toBeInTheDocument();
    expect(screen.getByText('61.9%')).toBeInTheDocument();
    expect(screen.getByText('+0.12R')).toBeInTheDocument();
    expect(screen.getByText('POSITIVE')).toBeInTheDocument();
    expect(screen.getByText('NEGATIVE')).toBeInTheDocument();
  });

  it('6. Full App integration renders daily ranking dashboard, summary cards, and previews', async () => {
    vi.spyOn(scannerApi, 'fetchDailyScanStatus').mockResolvedValue(mockStatusResponse);
    vi.spyOn(scannerApi, 'fetchDailySignals').mockResolvedValue(mockDailyRanking);
    vi.spyOn(scannerApi, 'fetchActiveWatchlist').mockResolvedValue(mockWatchlistSetups);
    vi.spyOn(scannerApi, 'fetchStrategyAnalytics').mockResolvedValue(mockStrategyAnalytics);
    vi.spyOn(scannerApi, 'fetchAggregatedSignals').mockResolvedValue(mockAggregatedSignal);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('SwingLens')).toBeInTheDocument();
      expect(screen.getByText('STOCKS EVALUATED')).toBeInTheDocument();
      expect(screen.getByText('BUY SETUPS')).toBeInTheDocument();
      expect(screen.getByText('HIGH AGREEMENT')).toBeInTheDocument();
      expect(screen.getByText('ACTIVE WATCHLIST')).toBeInTheDocument();
      expect(screen.getByText("Today's Recommendations")).toBeInTheDocument();
      expect(screen.getByText('Market Scanner')).toBeInTheDocument();
    });
  });
});
