/**
 * Tests for the Analytics Dashboard component.
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { AnalyticsDashboard } from '../AnalyticsDashboard';

const mockCostSummary = {
  total_cost: 12.5,
  cost_by_provider: { anthropic: 10, openai: 2.5 },
  cost_by_model: { 'claude-opus': 8, 'gpt-4': 2.5, 'claude-sonnet': 4 },
  total_tokens: 1_500_000,
  tokens_input: 1_000_000,
  tokens_output: 500_000,
  period_days: 30,
  daily_avg: 0.4167,
  trend_pct: 5,
};

const mockSnapshot = {
  tasks_by_status: { completed: 120, in_progress: 10, pending: 20 },
  avg_completion_by_complexity: { low: 600, medium: 1800, high: 3600 },
  qa_first_pass_rate: 85,
  qa_avg_score: 88,
  total_tokens: 1_500_000,
  tokens_by_provider: { anthropic: 1_200_000, openai: 300_000 },
  total_cost: 12.5,
  cost_by_model: { 'claude-opus': 8, 'gpt-4': 2.5 },
  merge_auto_count: 95,
  merge_manual_count: 25,
};

const mockGetCostSummary = vi.fn();
const mockGetDashboardSnapshot = vi.fn();

describe('AnalyticsDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockGetCostSummary.mockResolvedValue({ success: true, summary: mockCostSummary });
    mockGetDashboardSnapshot.mockResolvedValue({ success: true, snapshot: mockSnapshot });

    interface ElectronAPIMock {
      getCostSummary: typeof mockGetCostSummary;
      getDashboardSnapshot: typeof mockGetDashboardSnapshot;
      [key: string]: unknown;
    }
    (globalThis as unknown as { electronAPI?: ElectronAPIMock }).electronAPI = {
      ...(globalThis as unknown as { electronAPI?: ElectronAPIMock }).electronAPI,
      getCostSummary: mockGetCostSummary,
      getDashboardSnapshot: mockGetDashboardSnapshot,
    };
  });

  it('renders the no-project empty state when projectPath is not provided', () => {
    render(<AnalyticsDashboard />);
    expect(screen.getByText('Select a project to view analytics')).toBeInTheDocument();
  });

  it('renders loading state initially when projectPath is provided', () => {
    // Keep fetch pending
    mockGetCostSummary.mockReturnValue(new Promise(() => { /* noop */ }));
    mockGetDashboardSnapshot.mockReturnValue(new Promise(() => { /* noop */ }));

    render(<AnalyticsDashboard projectPath="/test/project" />);
    expect(screen.getByText('Loading analytics...')).toBeInTheDocument();
  });

  it('renders the dashboard header after data loads', async () => {
    render(<AnalyticsDashboard projectPath="/test/project" />);

    await waitFor(() => {
      expect(screen.getByText('Build Analytics')).toBeInTheDocument();
    });
    expect(screen.getByText('Monitor agent performance, token usage, and build metrics')).toBeInTheDocument();
  });

  it('displays KPI cards with correct data', async () => {
    render(<AnalyticsDashboard projectPath="/test/project" />);

    await waitFor(() => {
      // Total tasks: 120 + 10 + 20 = 150
      expect(screen.getByText('150')).toBeInTheDocument();
      // Success rate: 120/150 * 100 = 80.0%
      expect(screen.getByText('80.0%')).toBeInTheDocument();
      // Total tokens: 1.5M
      expect(screen.getByText('1.50M')).toBeInTheDocument();
      // Total cost
      expect(screen.getByText('$12.5000')).toBeInTheDocument();
    });
  });

  it('shows Overview tab content by default', async () => {
    render(<AnalyticsDashboard projectPath="/test/project" />);

    await waitFor(() => {
      expect(screen.getByText('Overview')).toBeInTheDocument();
      expect(screen.getByText('Tasks by Status')).toBeInTheDocument();
      expect(screen.getByText('QA & Merges')).toBeInTheDocument();
    });
  });

  it('switches to Costs tab', async () => {
    render(<AnalyticsDashboard projectPath="/test/project" />);

    // Wait for data to fully load before switching tabs
    await waitFor(() => {
      expect(screen.getByText('Build Analytics')).toBeInTheDocument();
    });

    // Radix UI Tabs triggers on mouseDown, not click
    fireEvent.mouseDown(screen.getByText('Costs'));

    await waitFor(() => {
      expect(screen.getByText('Cost by Provider')).toBeInTheDocument();
      expect(screen.getByText('Cost by Model')).toBeInTheDocument();
    });
  });

  it('switches to Performance tab', async () => {
    render(<AnalyticsDashboard projectPath="/test/project" />);

    // Wait for data to fully load before switching tabs
    await waitFor(() => {
      expect(screen.getByText('Build Analytics')).toBeInTheDocument();
    });

    // Radix UI Tabs triggers on mouseDown, not click
    fireEvent.mouseDown(screen.getByText('Performance'));

    await waitFor(() => {
      expect(screen.getByText('Tokens by Provider')).toBeInTheDocument();
      expect(screen.getByText('Avg. Completion by Complexity')).toBeInTheDocument();
    });
  });

  it('shows Refresh button and triggers reload on click', async () => {
    render(<AnalyticsDashboard projectPath="/test/project" />);

    await waitFor(() => {
      expect(screen.getByText('Refresh')).toBeInTheDocument();
    });

    const callsBefore = mockGetCostSummary.mock.calls.length;
    fireEvent.click(screen.getByText('Refresh'));

    await waitFor(() => {
      expect(mockGetCostSummary.mock.calls.length).toBeGreaterThan(callsBefore);
    });
  });

  it('displays QA metrics from snapshot', async () => {
    render(<AnalyticsDashboard projectPath="/test/project" />);

    await waitFor(() => {
      expect(screen.getByText('85.0%')).toBeInTheDocument();
      // auto-merged count
      expect(screen.getByText('95')).toBeInTheDocument();
      // manual merge count
      expect(screen.getByText('25')).toBeInTheDocument();
    });
  });

  it('handles API errors gracefully when both calls fail', async () => {
    mockGetCostSummary.mockRejectedValue(new Error('Network error'));
    mockGetDashboardSnapshot.mockRejectedValue(new Error('Network error'));

    render(<AnalyticsDashboard projectPath="/test/project" />);

    // Component uses allSettled so shows generic error message (not individual error text)
    await waitFor(() => {
      expect(screen.getByText('Error Loading Analytics')).toBeInTheDocument();
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });
  });

  it('retries on error when Retry button is clicked', async () => {
    mockGetCostSummary.mockRejectedValueOnce(new Error('Network error'));
    mockGetDashboardSnapshot.mockRejectedValueOnce(new Error('Network error'));

    render(<AnalyticsDashboard projectPath="/test/project" />);

    await waitFor(() => {
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });

    // Now mock success
    mockGetCostSummary.mockResolvedValue({ success: true, summary: mockCostSummary });
    mockGetDashboardSnapshot.mockResolvedValue({ success: true, snapshot: mockSnapshot });

    fireEvent.click(screen.getByText('Retry'));

    await waitFor(() => {
      expect(screen.getByText('Build Analytics')).toBeInTheDocument();
    });
  });

  it('shows error state when both API calls return failure', async () => {
    mockGetCostSummary.mockResolvedValue({ success: false });
    mockGetDashboardSnapshot.mockResolvedValue({ success: false });

    render(<AnalyticsDashboard projectPath="/test/project" />);

    // When both return success:false, component treats it as an error (bothFailed=true)
    await waitFor(() => {
      expect(screen.getByText('Error Loading Analytics')).toBeInTheDocument();
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });
  });
});
