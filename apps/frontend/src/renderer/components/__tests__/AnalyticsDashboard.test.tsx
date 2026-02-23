/**
 * Tests for the Analytics Dashboard component.
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { AnalyticsDashboard } from '../AnalyticsDashboard';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock data
const mockDashboardOverview = {
  total_builds: 150,
  successful_builds: 120,
  success_rate: 80.0,
  total_tokens_used: 1500000,
  total_cost_usd: 12.50,
  avg_build_duration: 2400.0,
  recent_builds: [
    {
      build_id: 'build-123',
      spec_id: 'spec-001',
      spec_name: 'User Authentication',
      started_at: '2024-01-15T10:00:00Z',
      completed_at: '2024-01-15T11:00:00Z',
      status: 'complete',
      total_duration_seconds: 3600.0,
      total_tokens_used: 10000,
      total_cost_usd: 0.08,
      qa_iterations: 2,
      qa_success_rate: 90.0,
      llm_provider: 'anthropic',
      llm_model: 'claude-3-opus'
    },
    {
      build_id: 'build-124',
      spec_id: 'spec-002',
      spec_name: 'Payment Processing',
      started_at: '2024-01-15T12:00:00Z',
      completed_at: null,
      status: 'coding',
      total_duration_seconds: null,
      total_tokens_used: 5000,
      total_cost_usd: 0.04,
      qa_iterations: 0,
      qa_success_rate: 0.0,
      llm_provider: 'anthropic',
      llm_model: 'claude-3-opus'
    }
  ],
  top_error_types: [
    {
      error_type: 'syntax_error',
      error_category: 'user_error',
      count: 15,
      resolved_count: 12,
      resolution_rate: 80.0
    },
    {
      error_type: 'import_error',
      error_category: 'system_error',
      count: 8,
      resolved_count: 6,
      resolution_rate: 75.0
    }
  ],
  phase_performance: [
    {
      phase_name: 'planning',
      phase_type: 'planner',
      duration_seconds: 600.0,
      tokens_used: 2000,
      cost_usd: 0.02,
      success: true,
      builds_count: 150
    },
    {
      phase_name: 'coding',
      phase_type: 'coder',
      duration_seconds: 1200.0,
      tokens_used: 8000,
      cost_usd: 0.08,
      success: true,
      builds_count: 140
    }
  ]
};

const mockBuilds = [
  {
    build_id: 'build-123',
    spec_id: 'spec-001',
    spec_name: 'User Authentication',
    started_at: '2024-01-15T10:00:00Z',
    completed_at: '2024-01-15T11:00:00Z',
    status: 'complete',
    total_duration_seconds: 3600.0,
    total_tokens_used: 10000,
    total_cost_usd: 0.08,
    qa_iterations: 2,
    qa_success_rate: 90.0,
    llm_provider: 'anthropic',
    llm_model: 'claude-3-opus'
  }
];

const mockTokenMetrics = [
  {
    date: '2024-01-15',
    total_tokens: 50000,
    total_cost_usd: 0.40,
    builds_count: 5,
    avg_tokens_per_build: 10000
  },
  {
    date: '2024-01-14',
    total_tokens: 45000,
    total_cost_usd: 0.36,
    builds_count: 4,
    avg_tokens_per_build: 11250
  }
];

const mockQAMetrics = [
  {
    date: '2024-01-15',
    avg_success_rate: 85.0,
    total_iterations: 10,
    builds_tested: 5,
    avg_coverage: 88.0
  }
];

const mockAgentPerformance = [
  {
    agent_type: 'coder',
    llm_provider: 'anthropic',
    llm_model: 'claude-3-opus',
    total_builds: 100,
    success_rate: 85.0,
    avg_duration_seconds: 1800.0,
    avg_tokens_per_build: 8000,
    avg_cost_per_build: 0.06
  }
];

describe('AnalyticsDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Setup default fetch responses
    mockFetch.mockImplementation((url) => {
      if (url.includes('/analytics/overview')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockDashboardOverview)
        });
      } else if (url.includes('/analytics/builds')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockBuilds)
        });
      } else if (url.includes('/analytics/metrics/tokens')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockTokenMetrics)
        });
      } else if (url.includes('/analytics/metrics/qa')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockQAMetrics)
        });
      } else if (url.includes('/analytics/metrics/agent-performance')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockAgentPerformance)
        });
      }
      return Promise.resolve({
        ok: false,
        status: 404
      });
    });
  });

  it('renders the dashboard header', async () => {
    render(<AnalyticsDashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('Build Analytics')).toBeInTheDocument();
      expect(screen.getByText('Monitor agent performance, token usage, and build metrics')).toBeInTheDocument();
    });
  });

  it('displays KPI cards with correct data', async () => {
    render(<AnalyticsDashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('150')).toBeInTheDocument(); // Total Builds
      expect(screen.getByText('80.0%')).toBeInTheDocument(); // Success Rate
      expect(screen.getByText('1.5M')).toBeInTheDocument(); // Total Tokens
      expect(screen.getByText('$12.5000')).toBeInTheDocument(); // Total Cost
    });
  });

  it('shows recent builds in the overview tab', async () => {
    render(<AnalyticsDashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('User Authentication')).toBeInTheDocument();
      expect(screen.getByText('Payment Processing')).toBeInTheDocument();
    });
    
    // Check build status badges
    await waitFor(() => {
      expect(screen.getByText('complete')).toBeInTheDocument();
      expect(screen.getByText('coding')).toBeInTheDocument();
    });
  });

  it('displays phase performance metrics', async () => {
    render(<AnalyticsDashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('planning')).toBeInTheDocument();
      expect(screen.getByText('coding')).toBeInTheDocument();
      expect(screen.getByText('150 builds')).toBeInTheDocument();
      expect(screen.getByText('140 builds')).toBeInTheDocument();
    });
  });

  it('switches between tabs correctly', async () => {
    render(<AnalyticsDashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('Overview')).toBeInTheDocument();
    });
    
    // Click on Builds tab
    fireEvent.click(screen.getByText('Builds'));
    
    await waitFor(() => {
      expect(screen.getByText('All Builds')).toBeInTheDocument();
    });
    
    // Click on Performance tab
    fireEvent.click(screen.getByText('Performance'));
    
    await waitFor(() => {
      expect(screen.getByText('Agent Performance')).toBeInTheDocument();
      expect(screen.getByText('Token Usage Trend')).toBeInTheDocument();
    });
    
    // Click on Errors tab
    fireEvent.click(screen.getByText('Errors'));
    
    await waitFor(() => {
      expect(screen.getByText('Top Error Types')).toBeInTheDocument();
    });
  });

  it('displays agent performance data', async () => {
    render(<AnalyticsDashboard />);
    
    // Switch to Performance tab
    await waitFor(() => {
      fireEvent.click(screen.getByText('Performance'));
    });
    
    await waitFor(() => {
      expect(screen.getByText('coder')).toBeInTheDocument();
      expect(screen.getByText('85.0%')).toBeInTheDocument();
      expect(screen.getByText('anthropic • claude-3-opus')).toBeInTheDocument();
    });
  });

  it('shows error metrics with resolution rates', async () => {
    render(<AnalyticsDashboard />);
    
    // Switch to Errors tab
    await waitFor(() => {
      fireEvent.click(screen.getByText('Errors'));
    });
    
    await waitFor(() => {
      expect(screen.getByText('syntax_error')).toBeInTheDocument();
      expect(screen.getByText('80.0% resolved')).toBeInTheDocument();
      expect(screen.getByText('import_error')).toBeInTheDocument();
      expect(screen.getByText('75.0% resolved')).toBeInTheDocument();
    });
  });

  it('handles day range selection', async () => {
    render(<AnalyticsDashboard />);
    
    await waitFor(() => {
      expect(screen.getByDisplayValue('Last 30 days')).toBeInTheDocument();
    });
    
    // Change to 7 days
    const select = screen.getByDisplayValue('Last 30 days');
    fireEvent.change(select, { target: { value: '7' } });
    
    // Verify fetch was called with new parameter
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('days=7'),
        expect.any(Object)
      );
    });
  });

  it('handles refresh button click', async () => {
    render(<AnalyticsDashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('Refresh')).toBeInTheDocument();
    });
    
    // Clear previous calls
    mockFetch.mockClear();
    
    // Click refresh
    fireEvent.click(screen.getByText('Refresh'));
    
    // Verify fetch was called again
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(5); // 5 endpoints
    });
  });

  it('displays loading state initially', () => {
    // Mock fetch to delay response
    mockFetch.mockImplementation(() => new Promise(() => {}));
    
    render(<AnalyticsDashboard />);
    
    expect(screen.getByText('Loading analytics...')).toBeInTheDocument();
  });

  it('handles API errors gracefully', async () => {
    // Mock fetch to return error
    mockFetch.mockRejectedValue(new Error('Network error'));
    
    render(<AnalyticsDashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('Error Loading Analytics')).toBeInTheDocument();
      expect(screen.getByText('Network error')).toBeInTheDocument();
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });
  });

  it('retries on error when retry button is clicked', async () => {
    // Mock fetch to return error initially
    mockFetch.mockRejectedValueOnce(new Error('Network error'));
    
    render(<AnalyticsDashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });
    
    // Clear the error
    mockFetch.mockImplementation((url) => {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockDashboardOverview)
      });
    });
    
    // Click retry
    fireEvent.click(screen.getByText('Retry'));
    
    await waitFor(() => {
      expect(screen.getByText('Build Analytics')).toBeInTheDocument();
    });
  });

  it('formats token numbers correctly', async () => {
    const mockDataWithLargeTokens = {
      ...mockDashboardOverview,
      total_tokens_used: 2500000, // 2.5M tokens
    };
    
    mockFetch.mockImplementation((url) => {
      if (url.includes('/analytics/overview')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockDataWithLargeTokens)
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve([])
      });
    });
    
    render(<AnalyticsDashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('2.5M')).toBeInTheDocument(); // Should show 2.5M instead of 2500000
    });
  });

  it('formats duration correctly', async () => {
    render(<AnalyticsDashboard />);
    
    await waitFor(() => {
      // Check for duration formatting in recent builds
      expect(screen.getByText(/1h/)).toBeInTheDocument(); // 3600 seconds should show as 1h
    });
  });

  it('displays build status with correct colors and icons', async () => {
    render(<AnalyticsDashboard />);
    
    await waitFor(() => {
      // Check that status badges are rendered
      const completeStatus = screen.getByText('complete');
      const codingStatus = screen.getByText('coding');
      
      expect(completeStatus).toBeInTheDocument();
      expect(codingStatus).toBeInTheDocument();
    });
  });

  it('shows empty state when no data is available', async () => {
    // Mock empty responses
    mockFetch.mockImplementation((url) => {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          total_builds: 0,
          successful_builds: 0,
          success_rate: 0,
          total_tokens_used: 0,
          total_cost_usd: 0,
          avg_build_duration: 0,
          recent_builds: [],
          top_error_types: [],
          phase_performance: []
        })
      });
    });
    
    render(<AnalyticsDashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('0')).toBeInTheDocument(); // Total builds should be 0
    });
  });

  it('handles token usage trend display', async () => {
    render(<AnalyticsDashboard />);
    
    // Switch to Performance tab
    await waitFor(() => {
      fireEvent.click(screen.getByText('Performance'));
    });
    
    await waitFor(() => {
      expect(screen.getByText('Token Usage Trend')).toBeInTheDocument();
      // Should show dates from token metrics
      expect(screen.getByText('2024-01-15')).toBeInTheDocument();
      expect(screen.getByText('50K')).toBeInTheDocument(); // Formatted tokens
      expect(screen.getByText('$0.4000')).toBeInTheDocument(); // Formatted cost
    });
  });
});
