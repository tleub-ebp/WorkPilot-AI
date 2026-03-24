/**
 * Tests for Smart Estimation Dialog Component
 */

import { render, screen, } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import userEvent from '@testing-library/user-event';

// Mock the electron API
const mockElectronAPI = {
  runSmartEstimation: vi.fn(),
  cancelSmartEstimation: vi.fn(),
  onSmartEstimationStreamChunk: vi.fn(),
  onSmartEstimationStatus: vi.fn(),
  onSmartEstimationError: vi.fn(),
  onSmartEstimationComplete: vi.fn(),
  onSmartEstimationEvent: vi.fn(),
};

// Mock window.electronAPI
Object.defineProperty(window, 'electronAPI', {
  value: mockElectronAPI,
  writable: true,
});

// Mock the stores
const mockSmartEstimationStore = {
  isOpen: false,
  phase: 'idle' as const,
  status: '',
  streamingOutput: '',
  result: null,
  error: null,
  initialTaskDescription: '',
  openDialog: vi.fn(),
  closeDialog: vi.fn(),
  setPhase: vi.fn(),
  setStatus: vi.fn(),
  appendStreamingOutput: vi.fn(),
  setResult: vi.fn(),
  setError: vi.fn(),
  reset: vi.fn(),
};

const mockProjectStore = {
  selectedProjectId: 'test-project-id',
  projects: [
    { id: 'test-project-id', name: 'Test Project' }
  ]
};

vi.mock('@/stores/smart-estimation-store', () => ({
  useSmartEstimationStore: () => mockSmartEstimationStore,
  startSmartEstimation: vi.fn(),
  setupSmartEstimationListeners: vi.fn(() => vi.fn()),
}));

vi.mock('@/stores/project-store', () => ({
  useProjectStore: () => mockProjectStore,
}));

vi.mock('@/lib/utils', () => ({
  cn: vi.fn((...classes) => classes.filter(Boolean).join(' ')),
}));

// Mock UI components
vi.mock('@/components/ui/dialog', () => ({
  Dialog: ({ children, open, onOpenChange }: any) => 
    open ? <div data-testid="dialog">{children({ onOpenChange })}</div> : null,
  DialogContent: ({ children }: any) => <div data-testid="dialog-content">{children}</div>,
  DialogHeader: ({ children }: any) => <div data-testid="dialog-header">{children}</div>,
  DialogTitle: ({ children }: any) => <div data-testid="dialog-title">{children}</div>,
  DialogDescription: ({ children }: any) => <div data-testid="dialog-description">{children}</div>,
  DialogFooter: ({ children }: any) => <div data-testid="dialog-footer">{children}</div>,
}));

vi.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick, disabled, ...props }: any) => 
    <button onClick={onClick} disabled={disabled} data-testid={props['data-testid']} {...props}>
      {children}
    </button>,
}));

vi.mock('@/components/ui/textarea', () => ({
  Textarea: ({ value, onChange, disabled, placeholder }: any) => (
    <textarea
      value={value}
      onChange={onChange}
      disabled={disabled}
      placeholder={placeholder}
      data-testid="task-textarea"
    />
  ),
}));

vi.mock('@/components/ui/label', () => ({
  Label: ({ children, htmlFor }: any) => <label htmlFor={htmlFor}>{children}</label>,
}));

vi.mock('@/components/ui/badge', () => ({
  Badge: ({ children, variant }: any) => <span data-variant={variant}>{children}</span>,
}));

vi.mock('@/components/ui/progress', () => ({
  Progress: ({ value }: any) => <div data-testid="progress" data-value={value} />,
}));

vi.mock('@/components/ui/card', () => ({
  Card: ({ children }: any) => <div data-testid="card">{children}</div>,
  CardContent: ({ children }: any) => <div data-testid="card-content">{children}</div>,
  CardHeader: ({ children }: any) => <div data-testid="card-header">{children}</div>,
  CardTitle: ({ children }: any) => <div data-testid="card-title">{children}</div>,
  CardDescription: ({ children }: any) => <div data-testid="card-description">{children}</div>,
}));

// Mock i18n
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  Check: () => <span data-testid="check-icon" />,
  Copy: () => <span data-testid="copy-icon" />,
  Loader2: () => <span data-testid="loader-icon" />,
  TrendingUp: () => <span data-testid="trending-up-icon" />,
  AlertTriangle: () => <span data-testid="alert-triangle-icon" />,
  Clock: () => <span data-testid="clock-icon" />,
  DollarSign: () => <span data-testid="dollar-sign-icon" />,
  RotateCcw: () => <span data-testid="rotate-ccw-icon" />,
  X: () => <span data-testid="x-icon" />,
  Info: () => <span data-testid="info-icon" />,
  Target: () => <span data-testid="target-icon" />,
  Zap: () => <span data-testid="zap-icon" />,
  Shield: () => <span data-testid="shield-icon" />,
}));

import SmartEstimationDialog from '../smart-estimation-dialog';

describe('Smart Estimation Dialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Reset store state
    mockSmartEstimationStore.isOpen = false;
    mockSmartEstimationStore.phase = 'idle';
    mockSmartEstimationStore.status = '';
    mockSmartEstimationStore.streamingOutput = '';
    mockSmartEstimationStore.result = null;
    mockSmartEstimationStore.error = null;
    mockSmartEstimationStore.initialTaskDescription = '';
  });

  describe('Dialog Rendering', () => {
    it('should not render when dialog is closed', () => {
      mockSmartEstimationStore.isOpen = false;
      
      render(<SmartEstimationDialog />);
      
      expect(screen.queryByTestId('dialog')).not.toBeInTheDocument();
    });

    it('should render when dialog is open', () => {
      mockSmartEstimationStore.isOpen = true;
      
      render(<SmartEstimationDialog />);
      
      expect(screen.getByTestId('dialog')).toBeInTheDocument();
      expect(screen.getByTestId('dialog-title')).toBeInTheDocument();
      expect(screen.getByTestId('dialog-description')).toBeInTheDocument();
    });

    it('should display task description input', () => {
      mockSmartEstimationStore.isOpen = true;
      
      render(<SmartEstimationDialog />);
      
      expect(screen.getByTestId('task-textarea')).toBeInTheDocument();
      expect(screen.getByText('smartEstimation:task.label')).toBeInTheDocument();
    });

    it('should show project warning when no project selected', () => {
      mockSmartEstimationStore.isOpen = true;
      mockProjectStore.selectedProjectId = null;
      
      render(<SmartEstimationDialog />);
      
      expect(screen.getByText('smartEstimation:errors.noProject')).toBeInTheDocument();
    });
  });

  describe('Task Input', () => {
    it('should allow typing task description', async () => {
      mockSmartEstimationStore.isOpen = true;
      mockSmartEstimationStore.initialTaskDescription = '';
      
      render(<SmartEstimationDialog />);
      
      const textarea = screen.getByTestId('task-textarea');
      await userEvent.type(textarea, 'Add user authentication');
      
      expect(textarea).toHaveValue('Add user authentication');
    });

    it('should pre-fill with initial task description', () => {
      mockSmartEstimationStore.isOpen = true;
      mockSmartEstimationStore.initialTaskDescription = 'Pre-filled task';
      
      render(<SmartEstimationDialog />);
      
      const textarea = screen.getByTestId('task-textarea');
      expect(textarea).toHaveValue('Pre-filled task');
    });
  });

  describe('Estimation Actions', () => {
    it('should enable estimate button with valid input and project', () => {
      mockSmartEstimationStore.isOpen = true;
      mockSmartEstimationStore.initialTaskDescription = 'Valid task description';
      
      render(<SmartEstimationDialog />);
      
      const estimateButton = screen.getByTestId('estimate-button');
      expect(estimateButton).not.toBeDisabled();
    });

    it('should disable estimate button without task description', () => {
      mockSmartEstimationStore.isOpen = true;
      mockSmartEstimationStore.initialTaskDescription = '';
      
      render(<SmartEstimationDialog />);
      
      const estimateButton = screen.getByTestId('estimate-button');
      expect(estimateButton).toBeDisabled();
    });

    it('should disable estimate button without project', () => {
      mockSmartEstimationStore.isOpen = true;
      mockSmartEstimationStore.initialTaskDescription = 'Valid task';
      mockProjectStore.selectedProjectId = null;
      
      render(<SmartEstimationDialog />);
      
      const estimateButton = screen.getByTestId('estimate-button');
      expect(estimateButton).toBeDisabled();
    });

    it('should start estimation when estimate button clicked', async () => {
      mockSmartEstimationStore.isOpen = true;
      mockSmartEstimationStore.initialTaskDescription = 'Test task';
      
      render(<SmartEstimationDialog />);
      
      const estimateButton = screen.getByTestId('estimate-button');
      await userEvent.click(estimateButton);
      
      expect(mockSmartEstimationStore.setPhase).toHaveBeenCalledWith('analyzing');
      expect(mockElectronAPI.runSmartEstimation).toHaveBeenCalledWith(
        'test-project-id',
        'Test task'
      );
    });

    it('should close dialog when close button clicked', async () => {
      mockSmartEstimationStore.isOpen = true;
      
      render(<SmartEstimationDialog />);
      
      const closeButton = screen.getByTestId('close-button');
      await userEvent.click(closeButton);
      
      expect(mockSmartEstimationStore.closeDialog).toHaveBeenCalled();
    });
  });

  describe('Analysis State', () => {
    it('should show loading state during analysis', () => {
      mockSmartEstimationStore.isOpen = true;
      mockSmartEstimationStore.phase = 'analyzing';
      mockSmartEstimationStore.status = 'Analyzing complexity...';
      
      render(<SmartEstimationDialog />);
      
      expect(screen.getByTestId('loader-icon')).toBeInTheDocument();
      expect(screen.getByText('Analyzing complexity...')).toBeInTheDocument();
    });

    it('should show streaming output when available', () => {
      mockSmartEstimationStore.isOpen = true;
      mockSmartEstimationStore.phase = 'analyzing';
      mockSmartEstimationStore.streamingOutput = 'Analysis step 1\nAnalysis step 2';
      
      render(<SmartEstimationDialog />);
      
      expect(screen.getByText('Analysis step 1\nAnalysis step 2')).toBeInTheDocument();
      expect(screen.getByText('smartEstimation:result.analysisProgress')).toBeInTheDocument();
    });

    it('should show try again button on error', () => {
      mockSmartEstimationStore.isOpen = true;
      mockSmartEstimationStore.phase = 'error';
      mockSmartEstimationStore.error = 'Something went wrong';
      
      render(<SmartEstimationDialog />);
      
      expect(screen.getByText('smartEstimation:status.error')).toBeInTheDocument();
      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
      expect(screen.getByTestId('try-again-button')).toBeInTheDocument();
    });

    it('should reset and try again when try again clicked', async () => {
      mockSmartEstimationStore.isOpen = true;
      mockSmartEstimationStore.phase = 'error';
      mockSmartEstimationStore.initialTaskDescription = 'Test task';
      
      render(<SmartEstimationDialog />);
      
      const tryAgainButton = screen.getByTestId('try-again-button');
      await userEvent.click(tryAgainButton);
      
      expect(mockSmartEstimationStore.reset).toHaveBeenCalled();
    });
  });

  describe('Results Display', () => {
    const mockResult = {
      complexity_score: 7,
      confidence_level: 0.85,
      reasoning: ['High file impact', 'Risk factors identified'],
      similar_tasks: [
        {
          build_id: 'build-123',
          spec_name: 'Similar task',
          similarity_score: 0.8,
          complexity_score: 6,
          duration_hours: 2.5,
          qa_iterations: 2,
          success_rate: 0.9,
          tokens_used: 5000,
          cost_usd: 2.5,
          status: 'COMPLETE'
        }
      ],
      risk_factors: ['Authentication complexity'],
      estimated_duration_hours: 3.0,
      estimated_qa_iterations: 2.5,
      token_cost_estimate: 4.0,
      recommendations: ['Use separate branch', 'Add comprehensive testing']
    };

    it('should display estimation results', () => {
      mockSmartEstimationStore.isOpen = true;
      mockSmartEstimationStore.phase = 'complete';
      mockSmartEstimationStore.result = mockResult;
      
      render(<SmartEstimationDialog />);
      
      expect(screen.getByText('7')).toBeInTheDocument();
      expect(screen.getByText('85% confidence')).toBeInTheDocument();
      expect(screen.getByText('3.0h')).toBeInTheDocument();
      expect(screen.getByText('2.5 iterations')).toBeInTheDocument();
      expect(screen.getByText('$4.00')).toBeInTheDocument();
    });

    it('should display reasoning', () => {
      mockSmartEstimationStore.isOpen = true;
      mockSmartEstimationStore.phase = 'complete';
      mockSmartEstimationStore.result = mockResult;
      
      render(<SmartEstimationDialog />);
      
      expect(screen.getByText('smartEstimation:result.reasoning')).toBeInTheDocument();
      expect(screen.getByText('High file impact')).toBeInTheDocument();
      expect(screen.getByText('Risk factors identified')).toBeInTheDocument();
    });

    it('should display risk factors', () => {
      mockSmartEstimationStore.isOpen = true;
      mockSmartEstimationStore.phase = 'complete';
      mockSmartEstimationStore.result = mockResult;
      
      render(<SmartEstimationDialog />);
      
      expect(screen.getByText('smartEstimation:result.riskFactors')).toBeInTheDocument();
      expect(screen.getByText('Authentication complexity')).toBeInTheDocument();
    });

    it('should display recommendations', () => {
      mockSmartEstimationStore.isOpen = true;
      mockSmartEstimationStore.phase = 'complete';
      mockSmartEstimationStore.result = mockResult;
      
      render(<SmartEstimationDialog />);
      
      expect(screen.getByText('smartEstimation:result.recommendations')).toBeInTheDocument();
      expect(screen.getByText('Use separate branch')).toBeInTheDocument();
      expect(screen.getByText('Add comprehensive testing')).toBeInTheDocument();
    });

    it('should display similar tasks', () => {
      mockSmartEstimationStore.isOpen = true;
      mockSmartEstimationStore.phase = 'complete';
      mockSmartEstimationStore.result = mockResult;
      
      render(<SmartEstimationDialog />);
      
      expect(screen.getByText('smartEstimation:result.similarTasks')).toBeInTheDocument();
      expect(screen.getByText('Similar task')).toBeInTheDocument();
      expect(screen.getByText('80% similar')).toBeInTheDocument();
    });

    it('should handle copy functionality', async () => {
      mockSmartEstimationStore.isOpen = true;
      mockSmartEstimationStore.phase = 'complete';
      mockSmartEstimationStore.result = mockResult;
      
      // Mock clipboard
      const mockWriteText = vi.fn();
      Object.assign(navigator, {
        clipboard: {
          writeText: mockWriteText,
        },
      });
      
      render(<SmartEstimationDialog />);
      
      const copyButton = screen.getByTestId('copy-button');
      await userEvent.click(copyButton);
      
      expect(mockWriteText).toHaveBeenCalledWith(JSON.stringify(mockResult, null, 2));
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      mockSmartEstimationStore.isOpen = true;
      
      render(<SmartEstimationDialog />);
      
      const textarea = screen.getByTestId('task-textarea');
      expect(textarea).toHaveAttribute('placeholder');
    });

    it('should disable input during analysis', () => {
      mockSmartEstimationStore.isOpen = true;
      mockSmartEstimationStore.phase = 'analyzing';
      
      render(<SmartEstimationDialog />);
      
      const textarea = screen.getByTestId('task-textarea');
      expect(textarea).toBeDisabled();
    });
  });

  describe('Edge Cases', () => {
    it('should handle missing optional result fields', () => {
      mockSmartEstimationStore.isOpen = true;
      mockSmartEstimationStore.phase = 'complete';
      mockSmartEstimationStore.result = {
        complexity_score: 5,
        confidence_level: 0.7,
        reasoning: [],
        similar_tasks: [],
        risk_factors: [],
        recommendations: []
        // Missing optional fields
      };
      
      render(<SmartEstimationDialog />);
      
      expect(screen.getByText('5')).toBeInTheDocument();
      expect(screen.getByText('70% confidence')).toBeInTheDocument();
      // Should not crash with missing optional fields
    });

    it('should handle empty similar tasks array', () => {
      mockSmartEstimationStore.isOpen = true;
      mockSmartEstimationStore.phase = 'complete';
      mockSmartEstimationStore.result = {
        complexity_score: 3,
        confidence_level: 0.6,
        reasoning: ['Simple task'],
        similar_tasks: [],
        risk_factors: [],
        recommendations: []
      };
      
      render(<SmartEstimationDialog />);
      
      expect(screen.getByText('3')).toBeInTheDocument();
      expect(screen.getByText('Simple task')).toBeInTheDocument();
      // Should not show similar tasks section
      expect(screen.queryByText('smartEstimation:result.similarTasks')).not.toBeInTheDocument();
    });
  });
});
