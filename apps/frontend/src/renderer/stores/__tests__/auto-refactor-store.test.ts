import { renderHook, act } from '@testing-library/react';
import { useAutoRefactorStore, startAutoRefactor, cancelAutoRefactor, setupAutoRefactorListeners } from '../auto-refactor-store';
import type { AutoRefactorResult, AutoRefactorPhase } from '../auto-refactor-store';

// Mock electronAPI
const mockElectronAPI = {
  startAutoRefactor: vi.fn(),
  cancelAutoRefactor: vi.fn(),
  onAutoRefactorStatus: vi.fn(),
  onAutoRefactorStreamChunk: vi.fn(),
  onAutoRefactorError: vi.fn(),
  onAutoRefactorComplete: vi.fn(),
  onAutoRefactorExecutionComplete: vi.fn(),
};

// Mock window.electronAPI
Object.defineProperty(window, 'electronAPI', {
  value: mockElectronAPI,
  writable: true,
});

describe('AutoRefactorStore', () => {
  beforeEach(() => {
    // Reset store before each test
    useAutoRefactorStore.getState().reset();
    
    // Clear all mocks
    vi.clearAllMocks();
    
    // Mock event listener cleanup functions
    mockElectronAPI.onAutoRefactorStatus.mockReturnValue(() => {});
    mockElectronAPI.onAutoRefactorStreamChunk.mockReturnValue(() => {});
    mockElectronAPI.onAutoRefactorError.mockReturnValue(() => {});
    mockElectronAPI.onAutoRefactorComplete.mockReturnValue(() => {});
    mockElectronAPI.onAutoRefactorExecutionComplete.mockReturnValue(() => {});
  });

  describe('initial state', () => {
    it('should have correct initial state', () => {
      const { result } = renderHook(() => useAutoRefactorStore());
      
      expect(result.current.phase).toBe('idle');
      expect(result.current.status).toBe('');
      expect(result.current.streamingOutput).toBe('');
      expect(result.current.result).toBeNull();
      expect(result.current.executionResult).toBeNull();
      expect(result.current.error).toBeNull();
      expect(result.current.isOpen).toBe(false);
      expect(result.current.autoExecute).toBe(false);
      expect(result.current.model).toBeUndefined();
      expect(result.current.thinkingLevel).toBeUndefined();
    });
  });

  describe('dialog management', () => {
    it('should open dialog with default values', () => {
      const { result } = renderHook(() => useAutoRefactorStore());
      
      act(() => {
        result.current.openDialog();
      });
      
      expect(result.current.isOpen).toBe(true);
      expect(result.current.autoExecute).toBe(false);
      expect(result.current.model).toBeUndefined();
      expect(result.current.thinkingLevel).toBeUndefined();
      expect(result.current.phase).toBe('idle');
    });

    it('should open dialog with custom values', () => {
      const { result } = renderHook(() => useAutoRefactorStore());
      
      act(() => {
        result.current.openDialog(true, 'claude-3.5-sonnet', 'high');
      });
      
      expect(result.current.isOpen).toBe(true);
      expect(result.current.autoExecute).toBe(true);
      expect(result.current.model).toBe('claude-3.5-sonnet');
      expect(result.current.thinkingLevel).toBe('high');
    });

    it('should close dialog and reset state', () => {
      const { result } = renderHook(() => useAutoRefactorStore());
      
      // First open dialog and modify state
      act(() => {
        result.current.openDialog(true, 'test-model', 'medium');
        result.current.setStatus('Test status');
        result.current.appendStreamingOutput('Test output');
      });
      
      // Then close dialog
      act(() => {
        result.current.closeDialog();
      });
      
      expect(result.current.isOpen).toBe(false);
      expect(result.current.phase).toBe('idle');
      expect(result.current.status).toBe('');
      expect(result.current.streamingOutput).toBe('');
      expect(result.current.result).toBeNull();
      expect(result.current.executionResult).toBeNull();
      expect(result.current.error).toBeNull();
    });
  });

  describe('configuration', () => {
    it('should update auto execute setting', () => {
      const { result } = renderHook(() => useAutoRefactorStore());
      
      act(() => {
        result.current.setAutoExecute(true);
      });
      
      expect(result.current.autoExecute).toBe(true);
      
      act(() => {
        result.current.setAutoExecute(false);
      });
      
      expect(result.current.autoExecute).toBe(false);
    });

    it('should update model setting', () => {
      const { result } = renderHook(() => useAutoRefactorStore());
      
      act(() => {
        result.current.setModel('claude-3.5-sonnet');
      });
      
      expect(result.current.model).toBe('claude-3.5-sonnet');
      
      act(() => {
        result.current.setModel(undefined);
      });
      
      expect(result.current.model).toBeUndefined();
    });

    it('should update thinking level setting', () => {
      const { result } = renderHook(() => useAutoRefactorStore());
      
      act(() => {
        result.current.setThinkingLevel('high');
      });
      
      expect(result.current.thinkingLevel).toBe('high');
      
      act(() => {
        result.current.setThinkingLevel(undefined);
      });
      
      expect(result.current.thinkingLevel).toBeUndefined();
    });
  });

  describe('phase management', () => {
    it('should update phase correctly', () => {
      const { result } = renderHook(() => useAutoRefactorStore());
      
      const phases: Array<AutoRefactorPhase> = ['idle', 'analyzing', 'executing', 'complete', 'error'];
      
      phases.forEach(phase => {
        act(() => {
          result.current.setPhase(phase);
        });
        expect(result.current.phase).toBe(phase);
      });
    });

    it('should update status', () => {
      const { result } = renderHook(() => useAutoRefactorStore());
      
      act(() => {
        result.current.setStatus('Test status');
      });
      
      expect(result.current.status).toBe('Test status');
    });

    it('should append streaming output', () => {
      const { result } = renderHook(() => useAutoRefactorStore());
      
      act(() => {
        result.current.appendStreamingOutput('First chunk\n');
      });
      
      expect(result.current.streamingOutput).toBe('First chunk\n');
      
      act(() => {
        result.current.appendStreamingOutput('Second chunk\n');
      });
      
      expect(result.current.streamingOutput).toBe('First chunk\nSecond chunk\n');
    });

    it('should set and clear error', () => {
      const { result } = renderHook(() => useAutoRefactorStore());
      
      act(() => {
        result.current.setError('Test error');
      });
      
      expect(result.current.error).toBe('Test error');
      expect(result.current.phase).toBe('error');
      
      act(() => {
        result.current.reset();
      });
      
      expect(result.current.error).toBeNull();
      expect(result.current.phase).toBe('idle');
    });
  });

  describe('result management', () => {
    const mockResult: AutoRefactorResult = {
      analysis: {
        status: 'success',
        analysis: { issues: [] },
        files_analyzed: 10,
      },
      plan: {
        status: 'success',
        plan: { items: [] },
      },
      execution: {
        status: 'success',
        execution: { changes: [] },
        auto_executed: false,
      },
      summary: {
        issues_found: 5,
        files_analyzed: 10,
        refactoring_items: 3,
        quick_wins: 2,
        estimated_effort: '2 hours',
        risk_level: 'Medium',
      },
    };

    it('should set analysis result', () => {
      const { result } = renderHook(() => useAutoRefactorStore());
      
      act(() => {
        result.current.setResult(mockResult);
      });
      
      expect(result.current.result).toEqual(mockResult);
      expect(result.current.phase).toBe('complete');
    });

    it('should set execution result', () => {
      const { result } = renderHook(() => useAutoRefactorStore());
      
      const mockExecutionResult = {
        status: 'success',
        changes_made: 3,
        files_modified: ['test.py'],
      };
      
      act(() => {
        result.current.setExecutionResult(mockExecutionResult);
      });
      
      expect(result.current.executionResult).toEqual(mockExecutionResult);
      expect(result.current.phase).toBe('complete');
    });
  });

  describe('reset functionality', () => {
    it('should reset all state to initial values', () => {
      const { result } = renderHook(() => useAutoRefactorStore());
      
      // Modify all state values
      act(() => {
        result.current.openDialog(true, 'test-model', 'high');
        result.current.setStatus('Test status');
        result.current.appendStreamingOutput('Test output');
        result.current.setResult({
          analysis: { status: 'success', analysis: {}, files_analyzed: 1 },
          plan: { status: 'success', plan: {} },
          execution: { status: 'success', execution: {}, auto_executed: false },
          summary: {
            issues_found: 0,
            files_analyzed: 1,
            refactoring_items: 0,
            quick_wins: 0,
            estimated_effort: 'Unknown',
            risk_level: 'Unknown',
          },
        });
        result.current.setError('Test error');
      });
      
      // Reset state
      act(() => {
        result.current.reset();
      });
      
      // Check all values are reset
      expect(result.current.phase).toBe('idle');
      expect(result.current.status).toBe('');
      expect(result.current.streamingOutput).toBe('');
      expect(result.current.result).toBeNull();
      expect(result.current.executionResult).toBeNull();
      expect(result.current.error).toBeNull();
      expect(result.current.isOpen).toBe(false);
      expect(result.current.autoExecute).toBe(false);
      expect(result.current.model).toBeUndefined();
      expect(result.current.thinkingLevel).toBeUndefined();
    });
  });
});

describe('AutoRefactorStore Actions', () => {
  beforeEach(() => {
    // Reset store before each test
    useAutoRefactorStore.getState().reset();
    vi.clearAllMocks();
  });

  describe('startAutoRefactor', () => {
    it('should call electronAPI with correct parameters', () => {
      const projectId = 'test-project-id';
      
      // Configure store state
      act(() => {
        useAutoRefactorStore.getState().openDialog(true, 'claude-3.5-sonnet', 'high');
      });
      
      startAutoRefactor(projectId);
      
      expect(mockElectronAPI.startAutoRefactor).toHaveBeenCalledWith({
        projectDir: projectId,
        model: 'claude-3.5-sonnet',
        thinkingLevel: 'high',
        autoExecute: true,
      });
    });

    it('should reset streaming state and set analyzing phase', () => {
      const { result } = renderHook(() => useAutoRefactorStore());
      
      // Set some initial state
      act(() => {
        result.current.setStatus('Previous status');
        result.current.appendStreamingOutput('Previous output');
        result.current.setResult({
          analysis: { status: 'success', analysis: {}, files_analyzed: 1 },
          plan: { status: 'success', plan: {} },
          execution: { status: 'success', execution: {}, auto_executed: false },
          summary: {
            issues_found: 0,
            files_analyzed: 1,
            refactoring_items: 0,
            quick_wins: 0,
            estimated_effort: 'Unknown',
            risk_level: 'Unknown',
          },
        });
      });
      
      startAutoRefactor('test-project');
      
      expect(result.current.phase).toBe('analyzing');
      expect(result.current.status).toBe('');
      expect(result.current.streamingOutput).toBe('');
      expect(result.current.result).toBeNull();
      expect(result.current.executionResult).toBeNull();
      expect(result.current.error).toBeNull();
    });
  });

  describe('cancelAutoRefactor', () => {
    it('should call electronAPI cancel method', () => {
      cancelAutoRefactor();
      
      expect(mockElectronAPI.cancelAutoRefactor).toHaveBeenCalled();
    });

    it('should set phase to idle', () => {
      const { result } = renderHook(() => useAutoRefactorStore());
      
      // Set analyzing phase
      act(() => {
        result.current.setPhase('analyzing');
      });
      
      cancelAutoRefactor();
      
      expect(result.current.phase).toBe('idle');
    });
  });

  describe('setupAutoRefactorListeners', () => {
    it('should setup all event listeners', () => {
      const cleanup = setupAutoRefactorListeners();
      
      expect(mockElectronAPI.onAutoRefactorStatus).toHaveBeenCalled();
      expect(mockElectronAPI.onAutoRefactorStreamChunk).toHaveBeenCalled();
      expect(mockElectronAPI.onAutoRefactorError).toHaveBeenCalled();
      expect(mockElectronAPI.onAutoRefactorComplete).toHaveBeenCalled();
      expect(mockElectronAPI.onAutoRefactorExecutionComplete).toHaveBeenCalled();
      
      expect(typeof cleanup).toBe('function');
    });

    it('should handle status updates', () => {
      const { result } = renderHook(() => useAutoRefactorStore());
      const mockCallback = mockElectronAPI.onAutoRefactorStatus.mock.calls[0][0];
      
      // Test analyzing status
      act(() => {
        mockCallback('Analyzing codebase...');
      });
      
      expect(result.current.status).toBe('Analyzing codebase...');
      expect(result.current.phase).toBe('analyzing');
      
      // Test executing status
      act(() => {
        mockCallback('Executing refactoring...');
      });
      
      expect(result.current.status).toBe('Executing refactoring...');
      expect(result.current.phase).toBe('executing');
    });

    it('should handle stream chunks', () => {
      const { result } = renderHook(() => useAutoRefactorStore());
      const mockCallback = mockElectronAPI.onAutoRefactorStreamChunk.mock.calls[0][0];
      
      act(() => {
        mockCallback('First chunk\n');
      });
      
      expect(result.current.streamingOutput).toBe('First chunk\n');
      
      act(() => {
        mockCallback('Second chunk\n');
      });
      
      expect(result.current.streamingOutput).toBe('First chunk\nSecond chunk\n');
    });

    it('should handle errors', () => {
      const { result } = renderHook(() => useAutoRefactorStore());
      const mockCallback = mockElectronAPI.onAutoRefactorError.mock.calls[0][0];
      
      act(() => {
        mockCallback('Test error message');
      });
      
      expect(result.current.error).toBe('Test error message');
      expect(result.current.phase).toBe('error');
    });

    it('should handle completion', () => {
      const { result } = renderHook(() => useAutoRefactorStore());
      const mockCallback = mockElectronAPI.onAutoRefactorComplete.mock.calls[0][0];
      
      const mockResult: AutoRefactorResult = {
        analysis: { status: 'success', analysis: {}, files_analyzed: 5 },
        plan: { status: 'success', plan: {} },
        execution: { status: 'success', execution: {}, auto_executed: false },
        summary: {
          issues_found: 3,
          files_analyzed: 5,
          refactoring_items: 2,
          quick_wins: 1,
          estimated_effort: '1 hour',
          risk_level: 'Low',
        },
      };
      
      act(() => {
        mockCallback(mockResult);
      });
      
      expect(result.current.result).toEqual(mockResult);
      expect(result.current.phase).toBe('complete');
    });

    it('should handle execution completion', () => {
      const { result } = renderHook(() => useAutoRefactorStore());
      const mockCallback = mockElectronAPI.onAutoRefactorExecutionComplete.mock.calls[0][0];
      
      const mockExecutionResult = {
        status: 'success',
        changes_made: 5,
        files_modified: ['file1.js', 'file2.js'],
      };
      
      act(() => {
        mockCallback(mockExecutionResult);
      });
      
      expect(result.current.executionResult).toEqual(mockExecutionResult);
      expect(result.current.phase).toBe('complete');
    });
  });
});
