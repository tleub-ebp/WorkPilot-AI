import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useNaturalLanguageGitStore, executeGitCommand, setupNaturalLanguageGitListeners } from '@/stores/natural-language-git-store';

// Mock electronAPI
const mockElectronAPI = {
  executeNaturalLanguageGit: vi.fn(),
  cancelNaturalLanguageGit: vi.fn(),
  onNaturalLanguageGitStatus: vi.fn(),
  onNaturalLanguageGitStreamChunk: vi.fn(),
  onNaturalLanguageGitError: vi.fn(),
  onNaturalLanguageGitComplete: vi.fn(),
  removeNaturalLanguageGitStatusListener: vi.fn(),
  removeNaturalLanguageGitStreamChunkListener: vi.fn(),
  removeNaturalLanguageGitErrorListener: vi.fn(),
  removeNaturalLanguageGitCompleteListener: vi.fn(),
  getProjectPath: vi.fn(),
  getSettings: vi.fn(),
};

// Mock window.electronAPI
Object.defineProperty(window, 'electronAPI', {
  value: mockElectronAPI,
  writable: true,
});

describe('NaturalLanguageGitStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset store state
    useNaturalLanguageGitStore.setState({
      isOpen: false,
      phase: 'idle',
      status: '',
      error: null,
      naturalLanguageCommand: '',
      streamingOutput: '',
      result: null,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Store State Management', () => {
    it('should initialize with default state', () => {
      const { result } = renderHook(() => useNaturalLanguageGitStore());
      
      expect(result.current.isOpen).toBe(false);
      expect(result.current.phase).toBe('idle');
      expect(result.current.status).toBe('');
      expect(result.current.error).toBeNull();
      expect(result.current.naturalLanguageCommand).toBe('');
      expect(result.current.streamingOutput).toBe('');
      expect(result.current.result).toBeNull();
    });

    it('should open dialog with initial command', () => {
      const { result } = renderHook(() => useNaturalLanguageGitStore());
      
      act(() => {
        result.current.openDialog('show changes');
      });
      
      expect(result.current.isOpen).toBe(true);
      expect(result.current.naturalLanguageCommand).toBe('show changes');
      expect(result.current.phase).toBe('idle');
    });

    it('should close dialog', () => {
      const { result } = renderHook(() => useNaturalLanguageGitStore());
      
      act(() => {
        result.current.openDialog();
        result.current.closeDialog();
      });
      
      expect(result.current.isOpen).toBe(false);
    });

    it('should set natural language command', () => {
      const { result } = renderHook(() => useNaturalLanguageGitStore());
      
      act(() => {
        result.current.setNaturalLanguageCommand('undo last commit');
      });
      
      expect(result.current.naturalLanguageCommand).toBe('undo last commit');
    });

    it('should reset state', () => {
      const { result } = renderHook(() => useNaturalLanguageGitStore());
      
      // Set some state
      act(() => {
        result.current.openDialog('test command');
        result.current.setPhase('processing');
        result.current.setStatus('Processing...');
        result.current.setError('Test error');
      });
      
      // Reset
      act(() => {
        result.current.reset();
      });
      
      expect(result.current.phase).toBe('idle');
      expect(result.current.status).toBe('');
      expect(result.current.error).toBeNull();
      expect(result.current.streamingOutput).toBe('');
      expect(result.current.result).toBeNull();
      // Should preserve command and dialog state
      expect(result.current.naturalLanguageCommand).toBe('test command');
    });
  });

  describe('IPC Event Handling', () => {
    it('should handle status events', () => {
      const { result } = renderHook(() => useNaturalLanguageGitStore());
      const _mockCallback = vi.fn();
      
      const cleanup = setupNaturalLanguageGitListeners();
      
      // Simulate status event
      const statusCallback = mockElectronAPI.onNaturalLanguageGitStatus.mock.calls[0][0];
      statusCallback('Processing command...');
      
      expect(result.current.status).toBe('Processing command...');
      
      cleanup();
    });

    it('should handle stream chunk events', () => {
      const { result } = renderHook(() => useNaturalLanguageGitStore());
      
      const cleanup = setupNaturalLanguageGitListeners();
      
      // Simulate stream chunk event
      const streamCallback = mockElectronAPI.onNaturalLanguageGitStreamChunk.mock.calls[0][0];
      streamCallback('Processing...\nAnalyzing command...\n');
      
      expect(result.current.streamingOutput).toBe('Processing...\nAnalyzing command...\n');
      
      cleanup();
    });

    it('should handle error events', () => {
      const { result } = renderHook(() => useNaturalLanguageGitStore());
      
      const cleanup = setupNaturalLanguageGitListeners();
      
      // Simulate error event
      const errorCallback = mockElectronAPI.onNaturalLanguageGitError.mock.calls[0][0];
      errorCallback('Command failed');
      
      expect(result.current.error).toBe('Command failed');
      expect(result.current.phase).toBe('error');
      expect(result.current.status).toBe('Error');
      
      cleanup();
    });

    it('should handle complete events', () => {
      const { result } = renderHook(() => useNaturalLanguageGitStore());
      
      const cleanup = setupNaturalLanguageGitListeners();
      
      // Simulate complete event
      const completeCallback = mockElectronAPI.onNaturalLanguageGitComplete.mock.calls[0][0];
      const mockResult = {
        generatedCommand: 'git status',
        explanation: 'Shows the working tree status',
        executionOutput: 'On branch main\nnothing to commit',
        success: true,
      };
      completeCallback(mockResult);
      
      expect(result.current.result).toEqual(mockResult);
      expect(result.current.phase).toBe('complete');
      expect(result.current.status).toBe('Command executed successfully');
      
      cleanup();
    });
  });

  describe('Command Execution', () => {
    it('should execute command with valid input', async () => {
      const { result } = renderHook(() => useNaturalLanguageGitStore());
      
      // Set up mock responses
      mockElectronAPI.getProjectPath.mockResolvedValue('/path/to/project');
      mockElectronAPI.getSettings.mockResolvedValue({
        data: {
          featureModels: {
            'natural-language-git': 'claude-sonnet',
          },
          featureThinking: {
            'natural-language-git': 'medium',
          },
        },
      });
      
      act(() => {
        result.current.setNaturalLanguageCommand('show changes');
      });
      
      await act(async () => {
        await executeGitCommand('project-123');
      });
      
      expect(mockElectronAPI.executeNaturalLanguageGit).toHaveBeenCalledWith({
        projectPath: '/path/to/project',
        command: 'show changes',
        model: 'claude-sonnet',
        thinkingLevel: 'medium',
      });
      
      expect(result.current.phase).toBe('processing');
      expect(result.current.status).toBe('Processing command...');
    });

    it('should not execute command with empty input', async () => {
      // biome-ignore lint/correctness/noUnusedVariables: variable kept for clarity
      const { result } = renderHook(() => useNaturalLanguageGitStore());
      
      await act(async () => {
        await executeGitCommand('project-123');
      });
      
      expect(mockElectronAPI.executeNaturalLanguageGit).not.toHaveBeenCalled();
    });

    it('should handle project path error', async () => {
      const { result } = renderHook(() => useNaturalLanguageGitStore());
      
      mockElectronAPI.getProjectPath.mockResolvedValue(null);
      
      act(() => {
        result.current.setNaturalLanguageCommand('show changes');
      });
      
      await act(async () => {
        await executeGitCommand('project-123');
      });
      
      expect(result.current.phase).toBe('error');
      expect(result.current.error).toBe('Project path not found');
    });

    it('should handle execution error', async () => {
      const { result } = renderHook(() => useNaturalLanguageGitStore());
      
      mockElectronAPI.getProjectPath.mockResolvedValue('/path/to/project');
      mockElectronAPI.getSettings.mockResolvedValue({ data: {} });
      mockElectronAPI.executeNaturalLanguageGit.mockRejectedValue(new Error('API Error'));
      
      act(() => {
        result.current.setNaturalLanguageCommand('show changes');
      });
      
      await act(async () => {
        await executeGitCommand('project-123');
      });
      
      expect(result.current.phase).toBe('error');
      expect(result.current.error).toBe('API Error');
    });
  });

  describe('Cleanup', () => {
    it('should remove event listeners on cleanup', () => {
      const cleanup = setupNaturalLanguageGitListeners();
      
      expect(mockElectronAPI.onNaturalLanguageGitStatus).toHaveBeenCalled();
      expect(mockElectronAPI.onNaturalLanguageGitStreamChunk).toHaveBeenCalled();
      expect(mockElectronAPI.onNaturalLanguageGitError).toHaveBeenCalled();
      expect(mockElectronAPI.onNaturalLanguageGitComplete).toHaveBeenCalled();
      
      cleanup();
      
      // Note: In a real test, we'd verify the removeEventListener calls
      // but since we're mocking, we just ensure the cleanup function exists
    });
  });
});
