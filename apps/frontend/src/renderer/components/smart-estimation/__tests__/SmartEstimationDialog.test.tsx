/**
 * Tests for Smart Estimation Dialog Component
 */

import { render, screen, waitFor } from '@testing-library/react';
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

// Mock globalThis.electronAPI
Object.defineProperty(globalThis, 'electronAPI', {
  value: mockElectronAPI,
  writable: true,
});

const mockProjectStore: {
  selectedProjectId: string | null;
  projects: Array<{ id: string; name: string }>;
} = {
  selectedProjectId: 'test-project-id',
  projects: [
    { id: 'test-project-id', name: 'Test Project' }
  ]
};

vi.mock('@/stores/smart-estimation-store', () => {
  const store = {
    isOpen: false,
    phase: 'idle',
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
    setState: vi.fn(),
  };

  const useSmartEstimationStore = () => store;
  // Add setState to the hook function itself
  useSmartEstimationStore.setState = vi.fn();

  const mockStartSmartEstimation = vi.fn();

  return {
    useSmartEstimationStore,
    startSmartEstimation: mockStartSmartEstimation,
    setupSmartEstimationListeners: vi.fn(() => vi.fn()),
  };
});

vi.mock('@/stores/project-store', () => ({
  useProjectStore: (selector?: any) => {
    const store = mockProjectStore;
    return selector ? selector(store) : store;
  },
}));

vi.mock('@/lib/utils', () => ({
  cn: vi.fn((...classes) => classes.filter(Boolean).join(' ')),
}));

// Mock UI components
vi.mock('@/components/ui/dialog', () => ({
  Dialog: ({ children, open, onOpenChange }: any) => 
    open ? <div data-testid="dialog">{children}</div> : null,
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
  Textarea: ({ value, onChange, disabled, placeholder, id }: any) => (
    <textarea
      value={value}
      onChange={(e) => {
        // Call the onChange handler if provided
        if (onChange) {
          onChange(e);
        }
      }}
      disabled={disabled}
      placeholder={placeholder}
      id={id}
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

import SmartEstimationDialog from '../SmartEstimationDialog';
import { useSmartEstimationStore, startSmartEstimation } from '@/stores/smart-estimation-store';

// Helper function to get the mock store
const getMockStore = () => useSmartEstimationStore();

describe('SmartEstimationDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset global store
    const store = getMockStore();
    store.isOpen = false;
    store.phase = 'idle';
    store.status = '';
    store.streamingOutput = '';
    store.result = null;
    store.error = null;
    store.initialTaskDescription = '';
  });

  describe('Dialog Rendering', () => {
    it('should not render when dialog is closed', () => {
      getMockStore().isOpen = false;
      
      render(<SmartEstimationDialog />);
      
      expect(screen.queryByTestId('dialog')).not.toBeInTheDocument();
    });

    it('should render when dialog is open', () => {
      getMockStore().isOpen = true;
      
      render(<SmartEstimationDialog />);
      
      expect(screen.getByTestId('dialog')).toBeInTheDocument();
      expect(screen.getByTestId('dialog-title')).toBeInTheDocument();
      expect(screen.getByTestId('dialog-description')).toBeInTheDocument();
      
      // Debug: check what's actually rendered
      console.log('Document body:', document.body.innerHTML);
    });

    it('should display task description input', () => {
      getMockStore().isOpen = true;
      
      render(<SmartEstimationDialog />);
      
      expect(screen.getByTestId('task-textarea')).toBeInTheDocument();
      expect(screen.getByText('smartEstimation:task.label')).toBeInTheDocument();
    });

    it('should show project warning when no project selected', () => {
      getMockStore().isOpen = true;
      mockProjectStore.selectedProjectId = null;
      
      render(<SmartEstimationDialog />);
      
      expect(screen.getByText('smartEstimation:errors.noProject')).toBeInTheDocument();
    });
  });

  describe('Task Input', () => {
    it('should allow typing task description', async () => {
      getMockStore().isOpen = true;
      getMockStore().initialTaskDescription = '';
      
      render(<SmartEstimationDialog />);
      
      const textarea = screen.getByTestId('task-textarea');
      await userEvent.type(textarea, 'Add user authentication');
      
      expect(textarea).toHaveValue('Add user authentication');
    });

    it('should pre-fill with initial task description', () => {
      getMockStore().isOpen = true;
      getMockStore().initialTaskDescription = 'Pre-filled task';
      
      render(<SmartEstimationDialog />);
      
      const textarea = screen.getByTestId('task-textarea');
      expect(textarea).toHaveValue('Pre-filled task');
    });
  });

  describe('Estimation Actions', () => {
    it('should enable estimate button with valid input and project', async () => {
      getMockStore().isOpen = true;
      getMockStore().phase = 'idle';
      
      // Ensure project is selected
      mockProjectStore.selectedProjectId = 'test-project-id';
      
      render(<SmartEstimationDialog />);
      
      // Type in the textarea to set the editableTaskDescription
      const textarea = screen.getByTestId('task-textarea');
      await userEvent.type(textarea, 'Valid task description');
      
      // Wait for the component to update
      await waitFor(() => {
        const estimateButton = screen.getByText('smartEstimation:actions.estimate');
        expect(estimateButton.closest('button')).not.toBeDisabled();
      });
    });

    it('should disable estimate button without task description', () => {
      getMockStore().isOpen = true;
      getMockStore().initialTaskDescription = '';
      
      render(<SmartEstimationDialog />);
      
      const estimateButton = screen.getByText('smartEstimation:actions.estimate');
      expect(estimateButton.closest('button')).toBeDisabled();
    });

    it('should disable estimate button without project', () => {
      getMockStore().isOpen = true;
      getMockStore().initialTaskDescription = 'Valid task';
      mockProjectStore.selectedProjectId = null;
      
      render(<SmartEstimationDialog />);
      
      const estimateButton = screen.getByText('smartEstimation:actions.estimate');
      expect(estimateButton.closest('button')).toBeDisabled();
    });

    it('should start estimation when estimate button clicked', async () => {
      getMockStore().isOpen = true;
      getMockStore().phase = 'idle';
      getMockStore().initialTaskDescription = 'Test task';
      
      // Ensure project is selected
      mockProjectStore.selectedProjectId = 'test-project-id';
      
      render(<SmartEstimationDialog />);
      
      // Type in the textarea to update editableTaskDescription
      const textarea = screen.getByTestId('task-textarea');
      await userEvent.clear(textarea);
      await userEvent.type(textarea, 'Test task');
      
      const estimateButton = screen.getByText('smartEstimation:actions.estimate');
      await userEvent.click(estimateButton);
      
      expect(startSmartEstimation).toHaveBeenCalledWith('test-project-id');
    });

    it('should close dialog when close button clicked', async () => {
      getMockStore().isOpen = true;
      
      render(<SmartEstimationDialog />);
      
      const closeButton = screen.getByText('smartEstimation:actions.close');
      await userEvent.click(closeButton);
      
      expect(getMockStore().closeDialog).toHaveBeenCalled();
    });
  });

  describe('Analysis State', () => {
    it('should show loading state during analysis', () => {
      getMockStore().isOpen = true;
      getMockStore().phase = 'analyzing';
      getMockStore().status = 'Analyzing complexity...';
      
      render(<SmartEstimationDialog />);
      
      expect(screen.getByTestId('loader-icon')).toBeInTheDocument();
      expect(screen.getByText('Analyzing complexity...')).toBeInTheDocument();
    });

    it('should show streaming output when available', () => {
      getMockStore().isOpen = true;
      getMockStore().phase = 'analyzing';
      getMockStore().streamingOutput = 'Analysis step 1\nAnalysis step 2';
      
      render(<SmartEstimationDialog />);
      
      expect(screen.getByText((content) => content.includes('Analysis step 1') && content.includes('Analysis step 2'))).toBeInTheDocument();
      expect(screen.getByText('smartEstimation:result.analysisProgress')).toBeInTheDocument();
    });

    it('should show try again button on error', () => {
      getMockStore().isOpen = true;
      getMockStore().phase = 'error';
      getMockStore().error = 'Something went wrong';
      
      render(<SmartEstimationDialog />);
      
      expect(screen.getByText('smartEstimation:status.error')).toBeInTheDocument();
      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
      expect(screen.getByText('smartEstimation:actions.tryAgain')).toBeInTheDocument();
    });

    it('should reset and try again when try again clicked', async () => {
      getMockStore().isOpen = true;
      getMockStore().phase = 'error';
      getMockStore().initialTaskDescription = 'Test task';
      
      render(<SmartEstimationDialog />);
      
      const tryAgainButton = screen.getByText('smartEstimation:actions.tryAgain');
      await userEvent.click(tryAgainButton);
      
      expect(getMockStore().reset).toHaveBeenCalled();
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
      estimated_duration_hours: 3,
      estimated_qa_iterations: 2.5,
      token_cost_estimate: 4,
      recommendations: ['Use separate branch', 'Add comprehensive testing']
    };

    it('should display estimation results', () => {
      getMockStore().isOpen = true;
      getMockStore().phase = 'complete';
      getMockStore().result = mockResult;
      
      render(<SmartEstimationDialog />);
      
      expect(screen.getByText('7')).toBeInTheDocument();
      expect(screen.getByText((content) => content.includes('85') && content.includes('confidence'))).toBeInTheDocument();
      expect(screen.getByText('3.0h')).toBeInTheDocument();
      expect(screen.getByText('$4.00')).toBeInTheDocument();
    });

    it('should display reasoning', () => {
      getMockStore().isOpen = true;
      getMockStore().phase = 'complete';
      getMockStore().result = mockResult;
      
      render(<SmartEstimationDialog />);
      
      expect(screen.getByText('smartEstimation:result.reasoning')).toBeInTheDocument();
      expect(screen.getByText('High file impact')).toBeInTheDocument();
      expect(screen.getByText('Risk factors identified')).toBeInTheDocument();
    });

    it('should display risk factors', () => {
      getMockStore().isOpen = true;
      getMockStore().phase = 'complete';
      getMockStore().result = mockResult;
      
      render(<SmartEstimationDialog />);
      
      expect(screen.getByText('smartEstimation:result.riskFactors')).toBeInTheDocument();
      expect(screen.getByText('Authentication complexity')).toBeInTheDocument();
    });

    it('should display recommendations', () => {
      getMockStore().isOpen = true;
      getMockStore().phase = 'complete';
      getMockStore().result = mockResult;
      
      render(<SmartEstimationDialog />);
      
      expect(screen.getByText('smartEstimation:result.recommendations')).toBeInTheDocument();
      expect(screen.getByText('Use separate branch')).toBeInTheDocument();
      expect(screen.getByText('Add comprehensive testing')).toBeInTheDocument();
    });

    it('should display similar tasks', () => {
      getMockStore().isOpen = true;
      getMockStore().phase = 'complete';
      getMockStore().result = mockResult;
      
      render(<SmartEstimationDialog />);
      
      expect(screen.getByText('smartEstimation:result.similarTasks')).toBeInTheDocument();
      expect(screen.getByText('Similar task')).toBeInTheDocument();
      expect(screen.getByText((content) => content.includes('80') && content.includes('% similar'))).toBeInTheDocument();
    });

    it('should handle copy functionality', async () => {
      getMockStore().isOpen = true;
      getMockStore().phase = 'complete';
      getMockStore().result = mockResult;
      
      // Mock clipboard
      const mockWriteText = vi.fn();
      Object.assign(navigator, {
        clipboard: {
          writeText: mockWriteText,
        },
      });
      
      render(<SmartEstimationDialog />);
      
      const copyButton = screen.getByText('smartEstimation:actions.copy');
      await userEvent.click(copyButton);
      
      expect(mockWriteText).toHaveBeenCalledWith(JSON.stringify(mockResult, null, 2));
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      getMockStore().isOpen = true;
      
      render(<SmartEstimationDialog />);
      
      const textarea = screen.getByTestId('task-textarea');
      expect(textarea).toBeInTheDocument();
      expect(textarea).toHaveAttribute('id');
    });

    it('should disable input during analysis', () => {
      getMockStore().isOpen = true;
      getMockStore().phase = 'analyzing';
      
      render(<SmartEstimationDialog />);
      
      const textarea = screen.getByTestId('task-textarea');
      expect(textarea).toBeDisabled();
    });
  });

  describe('Edge Cases', () => {
    it('should handle missing optional result fields', () => {
      getMockStore().isOpen = true;
      getMockStore().phase = 'complete';
      getMockStore().result = {
        complexity_score: 5,
        confidence_level: 0.7,
        reasoning: [],
        similar_tasks: [],
        risk_factors: [],
        recommendations: []
        // Missing optional fields
      };
      
      render(<SmartEstimationDialog />);
      
      // The complexity score should always be displayed
      expect(screen.getByText('5')).toBeInTheDocument();
      expect(screen.getByText((content) => content.includes('70') && content.includes('confidence'))).toBeInTheDocument();
      // Should not crash with missing optional fields
    });

    it('should handle empty similar tasks array', () => {
      getMockStore().isOpen = true;
      getMockStore().phase = 'complete';
      getMockStore().result = {
        complexity_score: 3,
        confidence_level: 0.6,
        reasoning: ['Simple task'],
        similar_tasks: [],
        risk_factors: [],
        recommendations: []
      };
      
      render(<SmartEstimationDialog />);
      
      // The complexity score should always be displayed
      expect(screen.getByText('3')).toBeInTheDocument();
      expect(screen.getByText((content) => content.includes('60') && content.includes('confidence'))).toBeInTheDocument();
      // Should not show similar tasks section
      expect(screen.queryByText('smartEstimation:result.similarTasks')).not.toBeInTheDocument();
    });
  });
});
