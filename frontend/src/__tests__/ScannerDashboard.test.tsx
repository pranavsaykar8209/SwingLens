import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from '../App';
import * as scannerApi from '../api/scanner';
import type { DailyScanStatusResponse, ScanResult } from '../api/types';
import { BuySignalsTable } from '../components/BuySignalsTable';
import { Header } from '../components/Header';
import { StockDetailModal } from '../components/StockDetailModal';
import { SummaryCards } from '../components/SummaryCards';

const mockBuyResult: ScanResult = {
  symbol: 'HINDZINC',
  company_name: 'Hindustan Zinc Ltd.',
  signal: 'BUY',
  signal_date: '2026-08-20',
  close: 573.9,
  entry_price: 573.9,
  stop_loss: 550.27,
  target_price: 621.16,
  risk_reward: 2.0,
  score: 1,
  strategy_name: 'EMA Pullback',
  strategy_version: '1.0',
  reason: 'EMA20 > EMA50 > EMA200 pullback confirmed',
  metadata: {
    ema20: 570.0,
    ema50: 550.0,
    ema200: 500.0,
    trend: 'BULLISH',
  },
  error: null,
  status: 'SUCCESS',
};

const mockCompletedStatus: DailyScanStatusResponse = {
  scan_date: '2026-08-20',
  already_completed: true,
  status: 'COMPLETED',
  latest_market_date: '2026-08-20',
  last_completed_at: '2026-08-20T16:00:00',
  buy_count: 1,
  watch_count: 0,
  hold_count: 49,
  skipped_count: 0,
  error_message: null,
};

describe('React Daily Market Scanner Dashboard Suite', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.history.pushState({}, '', '/');
  });

  it('1. Renders Header component with scan metadata', () => {
    render(
      <Header
        scanDate="2026-08-20"
        universe="NIFTY NEXT 50"
        strategy="EMA Pullback"
        strategyVersion="1.0"
        onRefresh={() => {}}
        isRefreshing={false}
      />
    );
    expect(screen.getByText('SwingLens')).toBeInTheDocument();
    expect(screen.getByText('NIFTY NEXT 50')).toBeInTheDocument();
    expect(screen.getByText('Aug 20, 2026')).toBeInTheDocument();
    expect(screen.getByText('↻ Scan')).toBeInTheDocument();
  });

  it('2. Renders SummaryCards with accurate metric counts', () => {
    render(<SummaryCards buyCount={2} watchCount={0} holdCount={47} skipCount={1} />);
    expect(screen.getByText('BUY SIGNALS')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('47')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('3. Renders BuySignalsTable displaying BUY stocks', () => {
    const handleSelect = vi.fn();
    render(<BuySignalsTable buyResults={[mockBuyResult]} onSelectStock={handleSelect} />);
    expect(screen.getByText('HINDZINC')).toBeInTheDocument();
    expect(screen.getByText('Hindustan Zinc Ltd.')).toBeInTheDocument();
    expect(screen.getAllByText('₹573.90').length).toBeGreaterThan(0);

    fireEvent.click(screen.getByTestId('buy-symbol-HINDZINC'));
    expect(handleSelect).toHaveBeenCalledWith(mockBuyResult);
  });

  it('4. Renders empty BUY state when no BUY signals exist', () => {
    render(<BuySignalsTable buyResults={[]} onSelectStock={() => {}} />);
    expect(screen.getByText('No BUY setups found today.')).toBeInTheDocument();
  });

  it('5. Renders StockDetailModal with complete trade parameters and reasons', () => {
    const handleClose = vi.fn();
    render(<StockDetailModal stock={mockBuyResult} onClose={handleClose} />);

    expect(screen.getByText('Trade Execution Parameters')).toBeInTheDocument();
    expect(screen.getByText('₹573.90')).toBeInTheDocument();
    expect(screen.getByText('₹550.27')).toBeInTheDocument();
    expect(screen.getByText('₹621.16')).toBeInTheDocument();
    expect(screen.getByText('2:1')).toBeInTheDocument();

    const backButton = screen.getByText(/Back to Recommendations/i);
    fireEvent.click(backButton);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('6. App loads and renders dashboard from completed status API response', async () => {
    vi.spyOn(scannerApi, 'fetchDailyScanStatus').mockResolvedValue(mockCompletedStatus);
    vi.spyOn(scannerApi, 'fetchDailySignals').mockResolvedValue({
      signal_date: '2026-08-20',
      universe: 'NIFTY_NEXT_50',
      universe_size: 1,
      evaluated_count: 1,
      excluded_count: 0,
      buy_signal_count: 1,
      results: [
        {
          rank: 1,
          symbol: 'HINDZINC',
          company_name: 'Hindustan Zinc Ltd.',
          signal_date: '2026-08-20',
          score: 1,
          strength: 'NO_SIGNAL',
          tier: 'WEAK_OR_NO_SIGNAL',
          buy_count: 1,
          strategies_evaluated: 1,
          strategies_total: 5,
          buy_strategies: ['EMA Pullback'],
          hold_strategies: [],
          error_strategies: [],
          best_strategy_name: 'EMA Pullback',
          best_entry_price: 573.9,
          best_stop_loss: 550.27,
          best_target_price: 621.16,
          best_risk_reward: 2.0,
        },
      ],
      shortlist: [],
    });
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('SwingLens')).toBeInTheDocument();
      expect(screen.getAllByText('HINDZINC').length).toBeGreaterThan(0);
    });
  });

  it('7. App handles API error state with functional Retry button', async () => {
    const fetchSpy = vi
      .spyOn(scannerApi, 'fetchDailyScanStatus')
      .mockRejectedValueOnce(new Error('Network connection failed'));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText("Today's scan could not be completed.")).toBeInTheDocument();
      expect(screen.getByText('Network connection failed')).toBeInTheDocument();
    });

    fetchSpy.mockResolvedValueOnce(mockCompletedStatus);
    const retryBtn = screen.getByText('Retry Scan');
    fireEvent.click(retryBtn);

    await waitFor(() => {
      expect(screen.queryByText("Today's scan could not be completed.")).not.toBeInTheDocument();
    });
  });

  it('8. App displays loading state while fetching API status', () => {
    vi.spyOn(scannerApi, 'fetchDailyScanStatus').mockReturnValue(new Promise(() => {}));
    render(<App />);
    expect(screen.getByText("Checking today's daily scan status...")).toBeInTheDocument();
  });
});
