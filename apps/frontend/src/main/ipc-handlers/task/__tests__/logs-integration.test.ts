/**
 * Simplified integration tests for task logs loading flow
 */
import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest';
import { ipcMain, BrowserWindow } from 'electron';
import path from 'path';
import type { IPCResult, TaskLogs } from '../../../../shared/types';

// Mock modules
vi.mock('electron', () => ({
  ipcMain: {
    handle: vi.fn(),
    on: vi.fn()
  },
  BrowserWindow: vi.fn()
}));

// Mock fs module with proper named export
const mockExistsSync = vi.fn();
vi.mock('fs', () => ({
  existsSync: mockExistsSync,
  readFileSync: vi.fn(),
  watchFile: vi.fn(),
  default: {
    existsSync: mockExistsSync,
    readFileSync: vi.fn(),
    watchFile: vi.fn()
  }
}));

vi.mock('../../../../shared/constants', () => ({
  IPC_CHANNELS: {
    TASK_LOGS_GET: 'task:logsGet',
    TASK_LOGS_WATCH: 'task:logsWatch',
    TASK_LOGS_UNWATCH: 'task:logsUnwatch',
    TASK_LOGS_CHANGED: 'task:logsChanged',
    TASK_LOGS_STREAM: 'task:logsStream',
  },
  getSpecsDir: vi.fn((_autoBuildPath: string) => '.workpilot/specs'),
}));

vi.mock('../../../project-store', () => ({
  projectStore: {
    getProject: vi.fn()
  }
}));

vi.mock('../../../task-log-service', () => ({
  taskLogService: {
    loadLogs: vi.fn(),
    startWatching: vi.fn(),
    stopWatching: vi.fn(),
    on: vi.fn()
  }
}));

vi.mock('../../../utils/spec-path-helpers', () => ({
  isValidTaskId: vi.fn((id: string) => {
    if (!id || typeof id !== 'string') return false;
    if (id.includes('/') || id.includes('\\')) return false;
    if (id === '.' || id === '..') return false;
    if (id.includes('\0')) return false;
    return true;
  })
}));

vi.mock('../../../../shared/utils/debug-logger', () => ({
  debugLog: vi.fn(),
  debugWarn: vi.fn()
}));

vi.mock('../../../utils/path-helpers', () => ({
  ensureAbsolutePath: vi.fn((p: string) => {
    const pathMod = require('path');
    return pathMod.isAbsolute(p) ? p : pathMod.resolve(p);
  })
}));

describe('Task Logs Integration (Simplified)', () => {
  let ipcHandlers: Record<string, Function>;
  let mockMainWindow: Partial<BrowserWindow>;
  let getMainWindow: () => BrowserWindow | null;

  beforeEach(async () => {
    vi.clearAllMocks();
    ipcHandlers = {};

    // Capture IPC handlers
    (ipcMain.handle as Mock).mockImplementation((channel: string, handler: Function) => {
      ipcHandlers[channel] = handler;
    });

    // Mock main window
    mockMainWindow = {
      webContents: {
        send: vi.fn()
      } as any
    };
    getMainWindow = vi.fn(() => mockMainWindow as BrowserWindow);
  });

  afterEach(() => {
    vi.resetModules();
  });

  describe('TASK_LOGS_GET handler', () => {
    it('should successfully load and return task logs', async () => {
      const { projectStore } = await import('../../../project-store');
      const { taskLogService } = await import('../../../task-log-service');
      const { IPC_CHANNELS } = await import('../../../../shared/constants');

      const mockProject = {
        id: 'project-123',
        path: '/absolute/path/to/project',
        autoBuildPath: '.workpilot'
      };

      const mockLogs: TaskLogs = {
        spec_id: '001-test-task',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T01:00:00Z',
        phases: {
          planning: { phase: 'planning', status: 'completed', started_at: null, completed_at: null, entries: [] },
          coding: { phase: 'coding', status: 'active', started_at: null, completed_at: null, entries: [] },
          validation: { phase: 'validation', status: 'pending', started_at: null, completed_at: null, entries: [] }
        }
      };

      (projectStore.getProject as Mock).mockReturnValue(mockProject);
      mockExistsSync.mockReturnValue(true);
      (taskLogService.loadLogs as Mock).mockReturnValue(mockLogs);

      // Import and register handlers after mocks are set up
      const { registerTaskLogsHandlers } = await import('../logs-handlers');
      registerTaskLogsHandlers(getMainWindow);

      const handler = ipcHandlers[IPC_CHANNELS.TASK_LOGS_GET];
      const result = await handler({}, 'project-123', '001-test-task') as IPCResult<TaskLogs>;

      expect(result.success).toBe(true);
      expect(result.data).toEqual(mockLogs);
      expect(projectStore.getProject).toHaveBeenCalledWith('project-123');
      expect(taskLogService.loadLogs).toHaveBeenCalledWith(
        path.join('/absolute/path/to/project', '.workpilot/specs', '001-test-task'),
        '/absolute/path/to/project',
        '.workpilot/specs',
        '001-test-task'
      );
    });

    it('should reject invalid specId with path traversal characters', async () => {
      const { IPC_CHANNELS } = await import('../../../../shared/constants');
      
      // Import and register handlers
      const { registerTaskLogsHandlers } = await import('../logs-handlers');
      registerTaskLogsHandlers(getMainWindow);
      
      const handler = ipcHandlers[IPC_CHANNELS.TASK_LOGS_GET];
      const result = await handler({}, 'project-123', '../../../etc/passwd') as IPCResult<TaskLogs>;

      expect(result.success).toBe(false);
      expect(result.error).toBe('Invalid spec ID');
    });

    it('should return error when project not found', async () => {
      const { projectStore } = await import('../../../project-store');
      const { IPC_CHANNELS } = await import('../../../../shared/constants');

      (projectStore.getProject as Mock).mockReturnValue(null);
      
      // Import and register handlers
      const { registerTaskLogsHandlers } = await import('../logs-handlers');
      registerTaskLogsHandlers(getMainWindow);

      const handler = ipcHandlers[IPC_CHANNELS.TASK_LOGS_GET];
      const result = await handler({}, 'nonexistent-project', '001-test-task') as IPCResult<TaskLogs>;

      expect(result.success).toBe(false);
      expect(result.error).toBe('Project not found');
    });
  });

  describe('TASK_LOGS_WATCH handler', () => {
    it('should start watching spec directory for log changes', async () => {
      const { projectStore } = await import('../../../project-store');
      const { taskLogService } = await import('../../../task-log-service');
      const { IPC_CHANNELS } = await import('../../../../shared/constants');

      const mockProject = {
        id: 'project-123',
        path: '/absolute/path/to/project',
        autoBuildPath: '.workpilot'
      };

      (projectStore.getProject as Mock).mockReturnValue(mockProject);
      mockExistsSync.mockReturnValue(true);

      // Import and register handlers after mocks are set up
      const { registerTaskLogsHandlers } = await import('../logs-handlers');
      registerTaskLogsHandlers(getMainWindow);

      const handler = ipcHandlers[IPC_CHANNELS.TASK_LOGS_WATCH];
      const result = await handler({}, 'project-123', '001-test-task') as IPCResult;

      expect(result.success).toBe(true);
      expect(taskLogService.startWatching).toHaveBeenCalledWith(
        '001-test-task',
        path.join('/absolute/path/to/project', '.workpilot/specs', '001-test-task'),
        '/absolute/path/to/project',
        '.workpilot/specs'
      );
    });
  });

  describe('TASK_LOGS_UNWATCH handler', () => {
    it('should stop watching spec directory', async () => {
      const { taskLogService } = await import('../../../task-log-service');
      const { IPC_CHANNELS } = await import('../../../../shared/constants');

      // Import and register handlers
      const { registerTaskLogsHandlers } = await import('../logs-handlers');
      registerTaskLogsHandlers(getMainWindow);

      const handler = ipcHandlers[IPC_CHANNELS.TASK_LOGS_UNWATCH];
      const result = await handler({}, '001-test-task') as IPCResult;

      expect(result.success).toBe(true);
      expect(taskLogService.stopWatching).toHaveBeenCalledWith('001-test-task');
    });
  });
});
