import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from '../App';
import * as scannerApi from '../api/scanner';
import type {
  DailyScanStatusResponse,
  DailySignalRanking,
  RankedSignal,
  StrategyAnalyticsResponse,
  WatchlistSetup,
} from '../api/scanner';
import { StrengthBadge } from '../components/StrengthBadge';
import { TopSetupsTable } from '../components/TopSetupsTable';
import { WatchlistPreview } from '../components/WatchlistPreview';
import { StrategyPerformancePreview } from '../components/StrategyPerformancePreview';

const mockRankedSignals: RankedSignal[] = [
  {
    rank: 1,
    symbol: 'HDFCAMC',
    company_name: 'HDFC Asset Management Co.',
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
    score: 3,
    strength: 'MODERATE',
    tier: 'MODERATE_OPPORTUNITY',
    buy_count: 3,
    strategies_evaluated: 5,
    strategies_total: 5,
    buy_strategies: ['EMA Pullback', 'MACD Momentum', 'Bollinger Squeeze'],
    hold_strategies: ['MA Trend Breakout', 'RSI Mean-Reversion'],
    error_strategies: [],
    best_strategy_name: 'EMA Pullback',
    best_entry_price: 250.0,
    best_stop_loss: 240.0,
    best_target_price: 270.0,
    best_risk_reward: 2.0,
  },
  {
    rank: 3,
    symbol: 'ABB',
    company_name: 'ABB India Ltd.',
    signal_date: '2026-08-20',
    score: 0,
    strength: 'NO_SIGNAL',
    tier: 'WEAK_OR_NO_SIGNAL',
    buy_count: 0,
    strategies_evaluated: 5,
    strategies_total: 5,
    buy_strategies: [],
    hold_strategies: ['EMA Pullback', 'MA Trend Breakout', 'RSI Mean-Reversion', 'MACD Momentum', 'Bollinger Squeeze'],
    error_strategies: [],
    best_strategy_name: null,
    best_entry_price: null,
    best_stop_loss: null,
    best_target_price: null,
    best_risk_reward: null,
  },
];

const mockDailyRanking: DailySignalRanking = {
  signal_date: '2026-08-20',
  universe: 'NIFTY_NEXT_50',
  universe_size: 50,
  evaluated_count: 49,
  excluded_count: 1,
  buy_signal_count: 2,
  results: mockRankedSignals,
  shortlist: mockRankedSignals.slice(0, 2),
};

const mockWatchlistSetups: WatchlistSetup[] = [
  {
    id: 1,
    stock_id: 10,
    symbol: 'HDFCAMC',
    company_name: 'HDFC Asset Management Co.',
    strategy_name: 'EMA Pullback',
    strategy_version: '1.0',
    signal_date: '2026-08-20',
    entry_price: 4250.0,
    stop_loss: 4100.0,
    target_price: 4550.0,
    risk_reward: 2.0,
    score: 4,
    strength: 'STRONG',
    status: 'ACTIVE',
    outcome: 'PENDING',
  },
];

const mockStrategyAnalytics: StrategyAnalyticsResponse = {
  start_date: '2024-01-01',
  end_date: '2026-08-20',
  symbols: ['BANKBARODA', 'HDFCAMC', 'ABB'],
  strategies: [
    {
      strategy_name: 'EMA Pullback',
      strategy_version: '1.0',
      classification: 'POSITIVE',
      classification_reason: 'Positive historical performance',
      trades: 83,
      wins: 34,
      losses: 49,
      win_rate: 41.0,
      average_r: 0.12,
      total_r: 10.03,
      profit_factor: 1.14,
      max_drawdown: 2.3,
      average_holding_days: 7.9,
      target_hit_rate: 41.0,
      stop_hit_rate: 59.0,
      ambiguous_rate: 0.0,
      average_mfe_r: 1.2,
      average_mae_r: 0.8,
      stocks_tested: 10,
    },
    {
      strategy_name: 'MACD Momentum',
      strategy_version: '1.0',
      classification: 'POSITIVE',
      classification_reason: 'Positive historical performance',
      trades: 175,
      wins: 72,
      losses: 103,
      win_rate: 41.1,
      average_r: 0.11,
      total_r: 18.39,
      profit_factor: 1.13,
      max_drawdown: 4.3,
      average_holding_days: 9.2,
      target_hit_rate: 41.1,
      stop_hit_rate: 57.7,
      ambiguous_rate: 0.0,
      average_mfe_r: 1.14,
      average_mae_r: 0.94,
      stocks_tested: 10,
    },
  ],
};

const mockScanStatus: DailyScanStatusResponse = {
  scan_date: '2026-08-20',
  already_completed: true,
  status: 'COMPLETED',
  buy_count: 2,
  watch_count: 0,
  hold_count: 47,
  skipped_count: 1,
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

    expect(screen.getByText("Today's Top Setups")).toBeInTheDocument();
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
    expect(screen.getByText('No setups match the selected filter.')).toBeInTheDocument();
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
    expect(screen.getByText('Strategy Performance')).toBeInTheDocument();
    expect(screen.getByText('EMA Pullback')).toBeInTheDocument();
    expect(screen.getByText('41.0%')).toBeInTheDocument();
    expect(screen.getByText('+0.12')).toBeInTheDocument();
    expect(screen.getByText('1.14')).toBeInTheDocument();
    expect(screen.getAllByText('POSITIVE').length).toBeGreaterThan(0);
  });

  it('6. Full App integration renders daily ranking dashboard, summary cards, and previews', async () => {
    vi.spyOn(scannerApi, 'fetchDailyScanStatus').mockResolvedValue(mockScanStatus);
    vi.spyOn(scannerApi, 'fetchDailySignals').mockResolvedValue(mockDailyRanking);
    vi.spyOn(scannerApi, 'fetchActiveWatchlist').mockResolvedValue(mockWatchlistSetups);
    vi.spyOn(scannerApi, 'fetchStrategyAnalytics').mockResolvedValue(mockStrategyAnalytics);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('SwingLens')).toBeInTheDocument();
      expect(screen.getByText('STOCKS EVALUATED')).toBeInTheDocument();
      expect(screen.getByText('49')).toBeInTheDocument();
      expect(screen.getByText("Today's Top Setups")).toBeInTheDocument();
      expect(screen.getByText('Active Watchlist')).toBeInTheDocument();
      expect(screen.getByText('Strategy Performance')).toBeInTheDocument();
    });
  });
});
