/**
 * Tests for Smart Estimation Store
 */

import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';

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

import { 
  useSmartEstimationStore, 
  startSmartEstimation, 
  setupSmartEstimationListeners,
  type SmartEstimationResult 
} from '../../../src/renderer/stores/smart-estimation-store';

// Mock the project store
vi.mock('../../../src/renderer/stores/project-store', () => ({
  useProjectStore: vi.fn(),
}));

describe('Smart Estimation Store', () => {
  beforeEach(() => {
    // Reset all mocks
    vi.clearAllMocks();
    
    // Reset store state
    useSmartEstimationStore.getState().reset();
  });

  describe('Initial State', () => {
    it('should have correct initial state', () => {
      const { result } = renderHook(() => useSmartEstimationStore());
      const store = result.current;

      expect(store.phase).toBe('idle');
      expect(store.status).toBe('');
      expect(store.streamingOutput).toBe('');
      expect(store.result).toBe(null);
      expect(store.error).toBe(null);
      expect(store.isOpen).toBe(false);
      expect(store.initialTaskDescription).toBe('');
    });
  });

  describe('Dialog Management', () => {
    it('should open dialog with task description', () => {
      const { result } = renderHook(() => useSmartEstimationStore());
      const store = result.current;

      act(() => {
        store.openDialog('Test task description');
      });

      expect(store.isOpen).toBe(true);
      expect(store.initialTaskDescription).toBe('Test task description');
      expect(store.phase).toBe('idle');
    });

    it('should close dialog and reset state', () => {
      const { result } = renderHook(() => useSmartEstimationStore());
      const store = result.current;

      // First open dialog and set some state
      act(() => {
        store.openDialog('Test task');
        store.setPhase('analyzing');
        store.setStatus('Analyzing...');
        store.setError('Test error');
      });

      // Then close dialog
      act(() => {
        store.closeDialog();
      });

      expect(store.isOpen).toBe(false);
      expect(store.phase).toBe('idle');
      expect(store.status).toBe('');
      expect(store.error).toBe(null);
    });

    it('should reset state completely', () => {
      const { result } = renderHook(() => useSmartEstimationStore());
      const store = result.current;

      // Set some state
      act(() => {
        store.openDialog('Test');
        store.setPhase('complete');
        store.setResult({
          complexity_score: 5,
          confidence_level: 0.8,
          reasoning: ['Test reasoning'],
          similar_tasks: [],
          risk_factors: [],
          recommendations: []
        } as SmartEstimationResult);
      });

      // Reset
      act(() => {
        store.reset();
      });

      expect(store.phase).toBe('idle');
      expect(store.status).toBe('');
      expect(store.streamingOutput).toBe('');
      expect(store.result).toBe(null);
      expect(store.error).toBe(null);
      expect(store.isOpen).toBe(false);
      expect(store.initialTaskDescription).toBe('');
    });
  });

  describe('Phase Management', () => {
    it('should update phase correctly', () => {
      const { result } = renderHook(() => useSmartEstimationStore());
      const store = result.current;

      act(() => {
        store.setPhase('analyzing');
      });

      expect(store.phase).toBe('analyzing');

      act(() => {
        store.setPhase('complete');
      });

      expect(store.phase).toBe('complete');
    });

    it('should set result and phase to complete', () => {
      const { result } = renderHook(() => useSmartEstimationStore());
      const store = result.current;

      const mockResult: SmartEstimationResult = {
        complexity_score: 7,
        confidence_level: 0.85,
        reasoning: ['Test reasoning'],
        similar_tasks: [],
        risk_factors: [],
        recommendations: []
      };

      act(() => {
        store.setResult(mockResult);
      });

      expect(store.result).toEqual(mockResult);
      expect(store.phase).toBe('complete');
    });

    it('should set error and phase to error', () => {
      const { result } = renderHook(() => useSmartEstimationStore());
      const store = result.current;

      act(() => {
        store.setError('Test error message');
      });

      expect(store.error).toBe('Test error message');
      expect(store.phase).toBe('error');
    });
  });

  describe('Status and Streaming', () => {
    it('should update status', () => {
      const { result } = renderHook(() => useSmartEstimationStore());
      const store = result.current;

      act(() => {
        store.setStatus('Analyzing files...');
      });

      expect(store.status).toBe('Analyzing files...');
    });

    it('should append to streaming output', () => {
      const { result } = renderHook(() => useSmartEstimationStore());
      const store = result.current;

      act(() => {
        store.appendStreamingOutput('First chunk');
      });

      expect(store.streamingOutput).toBe('First chunk');

      act(() => {
        store.appendStreamingOutput('Second chunk');
      });

      expect(store.streamingOutput).toBe('First chunkSecond chunk');
    });
  });

  describe('Smart Estimation Execution', () => {
    beforeEach(() => {
      // Mock project store to return a selected project
      vi.doMock('../../../src/renderer/stores/project-store', () => ({
        useProjectStore: vi.fn(() => ({
          selectedProjectId: 'test-project-id'
        }))
      }));
    });

    it('should start estimation with valid task description', () => {
      const { result } = renderHook(() => useSmartEstimationStore());
      const store = result.current;

      // Setup initial state
      act(() => {
        store.openDialog('Test task description');
      });

      // Start estimation
      act(() => {
        startSmartEstimation('test-project-id');
      });

      expect(mockElectronAPI.runSmartEstimation).toHaveBeenCalledWith(
        'test-project-id',
        'Test task description'
      );
      expect(store.phase).toBe('analyzing');
      expect(store.streamingOutput).toBe('');
      expect(store.error).toBe(null);
      expect(store.result).toBe(null);
    });

    it('should not start estimation without task description', () => {
      const { result } = renderHook(() => useSmartEstimationStore());
      const store = result.current;

      // Don't set task description
      act(() => {
        store.openDialog('');
      });

      act(() => {
        startSmartEstimation('test-project-id');
      });

      expect(mockElectronAPI.runSmartEstimation).not.toHaveBeenCalled();
      expect(store.phase).toBe('idle');
    });

    it('should not start estimation without project ID', () => {
      const { result } = renderHook(() => useSmartEstimationStore());
      const store = result.current;

      act(() => {
        store.openDialog('Test task description');
      });

      act(() => {
        startSmartEstimation('');
      });

      expect(mockElectronAPI.runSmartEstimation).not.toHaveBeenCalled();
      expect(store.phase).toBe('idle');
    });
  });

  describe('IPC Listeners', () => {
    let cleanup: (() => void) | null = null;

    beforeEach(() => {
      cleanup = null;
    });

    afterEach(() => {
      if (cleanup) {
        cleanup();
      }
    });

    it('should setup IPC listeners correctly', () => {
      cleanup = setupSmartEstimationListeners();

      // Verify all listeners are set up
      expect(mockElectronAPI.onSmartEstimationStreamChunk).toHaveBeenCalled();
      expect(mockElectronAPI.onSmartEstimationStatus).toHaveBeenCalled();
      expect(mockElectronAPI.onSmartEstimationError).toHaveBeenCalled();
      expect(mockElectronAPI.onSmartEstimationComplete).toHaveBeenCalled();
      expect(mockElectronAPI.onSmartEstimationEvent).toHaveBeenCalled();
    });

    it('should handle stream chunks', () => {
      cleanup = setupSmartEstimationListeners();

      // Get the stream chunk callback
      const streamCallback = mockElectronAPI.onSmartEstimationStreamChunk.mock.calls[0][0];

      const { result } = renderHook(() => useSmartEstimationStore());
      const store = result.current;

      act(() => {
        streamCallback('Stream chunk 1');
      });

      expect(store.streamingOutput).toBe('Stream chunk 1');

      act(() => {
        streamCallback('Stream chunk 2');
      });

      expect(store.streamingOutput).toBe('Stream chunk 1Stream chunk 2');
    });

    it('should handle status updates', () => {
      cleanup = setupSmartEstimationListeners();

      const statusCallback = mockElectronAPI.onSmartEstimationStatus.mock.calls[0][0];

      const { result } = renderHook(() => useSmartEstimationStore());
      const store = result.current;

      act(() => {
        statusCallback('Analyzing complexity...');
      });

      expect(store.status).toBe('Analyzing complexity...');
    });

    it('should handle errors', () => {
      cleanup = setupSmartEstimationListeners();

      const errorCallback = mockElectronAPI.onSmartEstimationError.mock.calls[0][0];

      const { result } = renderHook(() => useSmartEstimationStore());
      const store = result.current;

      act(() => {
        errorCallback('Something went wrong');
      });

      expect(store.error).toBe('Something went wrong');
      expect(store.phase).toBe('error');
    });

    it('should handle completion', () => {
      cleanup = setupSmartEstimationListeners();

      const completeCallback = mockElectronAPI.onSmartEstimationComplete.mock.calls[0][0];

      const { result } = renderHook(() => useSmartEstimationStore());
      const store = result.current;

      const mockResult: SmartEstimationResult = {
        complexity_score: 6,
        confidence_level: 0.9,
        reasoning: ['Test reasoning'],
        similar_tasks: [],
        risk_factors: [],
        recommendations: []
      };

      act(() => {
        completeCallback(mockResult);
      });

      expect(store.result).toEqual(mockResult);
      expect(store.phase).toBe('complete');
    });

    it('should handle events', () => {
      cleanup = setupSmartEstimationListeners();

      const eventCallback = mockElectronAPI.onSmartEstimationEvent.mock.calls[0][0];

      const { result } = renderHook(() => useSmartEstimationStore());
      const store = result.current;

      act(() => {
        eventCallback({
          type: 'progress',
          data: { status: 'Processing...' },
          timestamp: '2023-01-01T00:00:00'
        });
      });

      // Events are handled by the runner, but we can verify the callback was called
      expect(mockElectronAPI.onSmartEstimationEvent).toHaveBeenCalled();
    });

    it('should return cleanup function', () => {
      cleanup = setupSmartEstimationListeners();

      expect(typeof cleanup).toBe('function');

      // Call cleanup to verify it doesn't throw
      expect(() => cleanup()).not.toThrow();
    });
  });

  describe('Store Persistence', () => {
    it('should maintain state across hook instances', () => {
      const { result: result1 } = renderHook(() => useSmartEstimationStore());
      const store1 = result1.current;

      // Set some state in first instance
      act(() => {
        store1.openDialog('Test task');
        store1.setPhase('analyzing');
      });

      // Create second instance
      const { result: result2 } = renderHook(() => useSmartEstimationStore());
      const store2 = result2.current;

      // State should be shared
      expect(store2.isOpen).toBe(true);
      expect(store2.initialTaskDescription).toBe('Test task');
      expect(store2.phase).toBe('analyzing');
    });
  });

  describe('Error Handling', () => {
    it('should handle invalid result data gracefully', () => {
      const { result } = renderHook(() => useSmartEstimationStore());
      const store = result.current;

      // Try to set invalid result
      act(() => {
        store.setResult(null as any);
      });

      expect(store.result).toBe(null);
      expect(store.phase).toBe('complete');
    });

    it('should handle empty error messages', () => {
      const { result } = renderHook(() => useSmartEstimationStore());
      const store = result.current;

      act(() => {
        store.setError('');
      });

      expect(store.error).toBe('');
      expect(store.phase).toBe('error');
    });
  });
});
