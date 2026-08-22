import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import * as scannerApi from '../api/scanner';
import type { DailySignalRanking, HistoricalScanSummary } from '../api/types';
import { ScanHistoryPage } from '../pages/ScanHistoryPage';
import { HistoricalScanDetailPage } from '../pages/HistoricalScanDetailPage';

const mockHistory: HistoricalScanSummary[] = [
  {
    scan_date: '2026-08-20',
    status: 'COMPLETED',
    stocks_evaluated: 49,
    buy_setups: 3,
    strong_signals: 1,
    completed_at: '2026-08-20T16:00:00',
  },
  {
    scan_date: '2026-08-19',
    status: 'COMPLETED',
    stocks_evaluated: 49,
    buy_setups: 2,
    strong_signals: 0,
    completed_at: '2026-08-19T16:00:00',
  },
];

const mockDailySnapshot: DailySignalRanking = {
  signal_date: '2026-08-20',
  universe: 'NIFTY_NEXT_50',
  universe_size: 49,
  evaluated_count: 49,
  excluded_count: 0,
  buy_signal_count: 1,
  results: [
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
  ],
  shortlist: [],
};

describe('Scan History & Historical Detail Views', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    scannerApi.resetApiCache();
  });

  afterEach(() => {
    cleanup();
  });

  it('1. Renders ScanHistoryPage with saved scans table and metadata', async () => {
    const mockFetch = vi.fn().mockImplementation((url: string) => {
      return Promise.resolve({
        ok: true,
        json: async () => (url.includes('history') ? mockHistory : mockDailySnapshot),
      } as any);
    });
    window.fetch = mockFetch;
    globalThis.fetch = mockFetch;

    render(
      <MemoryRouter initialEntries={['/scan-history']}>
        <Routes>
          <Route path="/scan-history" element={<ScanHistoryPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getAllByText('Scan History').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('2 Saved Scans')).toBeInTheDocument();
      expect(screen.getByText('Aug 20, 2026')).toBeInTheDocument();
      expect(screen.getByText('Aug 19, 2026')).toBeInTheDocument();
      expect(screen.getAllByText('View Scan').length).toBe(2);
    });
  });

  it('2. Renders HistoricalScanDetailPage with immutable snapshot data', async () => {
    const mockFetch = vi.fn().mockImplementation((url: string) => {
      return Promise.resolve({
        ok: true,
        json: async () => (url.includes('history') ? mockHistory : mockDailySnapshot),
      } as any);
    });
    window.fetch = mockFetch;
    globalThis.fetch = mockFetch;

    render(
      <MemoryRouter>
        <HistoricalScanDetailPage scanDate="2026-08-20" />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Immutable Historical Snapshot/i)).toBeInTheDocument();
      expect(screen.getAllByText('HDFCAMC').length).toBeGreaterThan(0);
      expect(screen.getAllByText('₹4250.00').length).toBeGreaterThan(0);
      expect(screen.getByText(/Back to Scan History/i)).toBeInTheDocument();
    });
  });
});
