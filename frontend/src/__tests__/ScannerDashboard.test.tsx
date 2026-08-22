import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from '../App';
import * as scannerApi from '../api/scanner';
import type { ScanResult, ScanSummary } from '../api/scanner';
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
  score: 0.85,
  strategy_name: 'EMA Pullback',
  strategy_version: '1.0',
  reason: 'EMA20 > EMA50 > EMA200 pullback confirmed',
  metadata: { rsi14: 58.4 },
  error: null,
  status: 'SUCCESS',
};

const mockScanSummary: ScanSummary = {
  scan_date: '2026-08-20',
  universe: 'NIFTY_NEXT_50',
  strategy: 'EMA Pullback',
  strategy_version: '1.0',
  stocks_scanned: 50,
  buy_count: 2,
  watch_count: 0,
  hold_count: 47,
  skip_count: 1,
  results: [
    mockBuyResult,
    {
      symbol: 'INDHOTEL',
      company_name: 'Indian Hotels Co. Ltd.',
      signal: 'BUY',
      signal_date: '2026-08-20',
      close: 735.85,
      entry_price: 735.85,
      stop_loss: 716.81,
      target_price: 773.93,
      risk_reward: 2.0,
      score: 0.85,
      strategy_name: 'EMA Pullback',
      strategy_version: '1.0',
      reason: 'Pullback setup met',
      metadata: { rsi14: 61.2 },
      error: null,
      status: 'SUCCESS',
    },
    {
      symbol: 'ABB',
      company_name: 'ABB India Ltd.',
      signal: 'HOLD',
      signal_date: '2026-08-20',
      close: 7479.0,
      entry_price: 7479.0,
      stop_loss: null,
      target_price: null,
      risk_reward: null,
      score: null,
      strategy_name: 'EMA Pullback',
      strategy_version: '1.0',
      reason: 'Setup conditions not satisfied',
      metadata: {},
      error: null,
      status: 'SUCCESS',
    },
  ],
};

const mockEmptyBuySummary: ScanSummary = {
  ...mockScanSummary,
  buy_count: 0,
  results: [
    {
      symbol: 'ABB',
      company_name: 'ABB India Ltd.',
      signal: 'HOLD',
      signal_date: '2026-08-20',
      close: 7479.0,
      entry_price: 7479.0,
      stop_loss: null,
      target_price: null,
      risk_reward: null,
      score: null,
      strategy_name: 'EMA Pullback',
      strategy_version: '1.0',
      reason: 'Setup conditions not satisfied',
      metadata: {},
      error: null,
      status: 'SUCCESS',
    },
  ],
};

describe('React Daily Market Scanner Dashboard Suite', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('1. Renders Header component with scan metadata', () => {
    render(
      <Header
        scanDate="2026-08-20"
        universe="NIFTY_NEXT_50"
        strategy="EMA Pullback"
        strategyVersion="1.0"
        onRefresh={() => {}}
        isRefreshing={false}
      />
    );
    expect(screen.getByText('SwingLens')).toBeInTheDocument();
    expect(screen.getByText('NIFTY_NEXT_50')).toBeInTheDocument();
    expect(screen.getByText('2026-08-20')).toBeInTheDocument();
    expect(screen.getByText('Refresh Scan')).toBeInTheDocument();
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
    expect(mockEmptyBuySummary.buy_count).toBe(0);
  });

  it('5. Renders StockDetailModal with complete trade parameters and reasons', () => {
    const handleClose = vi.fn();
    render(<StockDetailModal stock={mockBuyResult} onClose={handleClose} />);

    expect(screen.getByText('Trade Execution Parameters')).toBeInTheDocument();
    expect(screen.getByText('₹573.90')).toBeInTheDocument();
    expect(screen.getByText('₹550.27')).toBeInTheDocument();
    expect(screen.getByText('₹621.16')).toBeInTheDocument();
    expect(screen.getByText('2:1')).toBeInTheDocument();
    expect(screen.getByText('EMA20 > EMA50 > EMA200 pullback confirmed')).toBeInTheDocument();

    const backButton = screen.getByText('Back to Scanner Dashboard');
    fireEvent.click(backButton);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('6. App loads and renders dashboard from API response', async () => {
    vi.spyOn(scannerApi, 'fetchLatestScan').mockResolvedValue(mockScanSummary);
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('SwingLens')).toBeInTheDocument();
      expect(screen.getAllByText('HINDZINC').length).toBeGreaterThan(0);
    });
  });

  it('7. App handles API error state with functional Retry button', async () => {
    const fetchSpy = vi
      .spyOn(scannerApi, 'fetchLatestScan')
      .mockRejectedValueOnce(new Error('Network connection failed'));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText("Unable to load today's scan.")).toBeInTheDocument();
      expect(screen.getByText('Network connection failed')).toBeInTheDocument();
    });

    fetchSpy.mockResolvedValue(mockScanSummary);

    const retryBtn = screen.getByRole('button', { name: /retry/i });
    fireEvent.click(retryBtn);

    await waitFor(() => {
      expect(screen.getAllByText('HINDZINC').length).toBeGreaterThan(0);
    });
  });

  it('8. App displays loading state while fetching API', () => {
    vi.spyOn(scannerApi, 'fetchLatestScan').mockImplementation(() => new Promise(() => {}));
    render(<App />);
    expect(screen.getByText("Loading today's scan...")).toBeInTheDocument();
  });
});
