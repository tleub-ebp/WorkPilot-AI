/**
 * Test setup file for Vitest
 */
import { mkdirSync, rmSync, existsSync } from 'node:fs';
import path from 'node:path';
import '@testing-library/jest-dom';

// Mock localStorage for tests that need it
const localStorageMock = (() => {
  let store: Record<string, string> = {};

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    }
  };
})();

// Make localStorage available globally
Object.defineProperty(globalThis, 'localStorage', {
  value: localStorageMock
});

// Mock scrollIntoView for Radix Select in jsdom
if (typeof HTMLElement !== 'undefined' && !HTMLElement.prototype.scrollIntoView) {
  Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
    value: () => {
      // Intentionally empty for tests
    },
    writable: true
  });
}

// Mock requestAnimationFrame/cancelAnimationFrame for jsdom
// Required by useXterm.ts which uses requestAnimationFrame for initial fit
if (globalThis.requestAnimationFrame === undefined) {
  globalThis.requestAnimationFrame = (callback: FrameRequestCallback) => {
    return setTimeout(() => callback(Date.now()), 0) as unknown as number;
  };
  globalThis.cancelAnimationFrame = (id: number) => {
    clearTimeout(id);
  };
}

// Test data directory for isolated file operations
export const TEST_DATA_DIR = '/tmp/workpilot-ai-tests';

// Create fresh test directory before each test
const setupTest = () => {
  // Clear localStorage
  localStorageMock.clear();

  // Use a unique subdirectory per test to avoid race conditions in parallel tests
  const testId = `test-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const _testDir = path.join(TEST_DATA_DIR, testId);

  try {
    if (existsSync(TEST_DATA_DIR)) {
      rmSync(TEST_DATA_DIR, { recursive: true, force: true });
    }
  } catch {
    // Ignore errors if directory is in use by another parallel test
    // Each test uses unique subdirectory anyway
  }

  try {
    mkdirSync(TEST_DATA_DIR, { recursive: true });
    mkdirSync(path.join(TEST_DATA_DIR, 'store'), { recursive: true });
  } catch {
    // Ignore errors if directory already exists from another parallel test
  }
};

// Export setup function for use in tests
export { setupTest };

// Clean up test directory after each test
const cleanupTest = () => {
  // Manual cleanup without vitest
};

// Export cleanup function for use in tests
export { cleanupTest };

// Mock window.electronAPI for renderer tests
if (typeof globalThis !== 'undefined') {
  (globalThis as unknown as { electronAPI: unknown }).electronAPI = {
    addProject: () => Promise.resolve({ success: true }),
    removeProject: () => Promise.resolve({ success: true }),
    getProjects: () => Promise.resolve({ success: true, data: [] }),
    updateProjectSettings: () => Promise.resolve({ success: true }),
    getTasks: () => Promise.resolve({ success: true, data: [] }),
    createTask: () => Promise.resolve({ success: true, data: { id: 'test-task' } }),
    startTask: () => Promise.resolve({ success: true }),
    stopTask: () => Promise.resolve({ success: true }),
    submitReview: () => Promise.resolve({ success: true }),
    onTaskProgress: () => () => {
      // Intentionally empty for tests
    },
    onTaskError: () => () => {
      // Intentionally empty for tests
    },
    onTaskLog: () => () => {
      // Intentionally empty for tests
    },
    onTaskStatusChange: () => () => {
      // Intentionally empty for tests
    },
    getSettings: () => Promise.resolve({ success: true, data: {} }),
    saveSettings: () => Promise.resolve({ success: true }),
    selectDirectory: () => Promise.resolve({ success: true, data: '/test/path' }),
    getAppVersion: () => Promise.resolve({ success: true, data: '1.0.0' }),
    // Tab state persistence (IPC-based)
    getTabState: () => Promise.resolve({
      success: true,
      data: { openProjectIds: [], activeProjectId: null, tabOrder: [] }
    }),
    saveTabState: () => Promise.resolve({ success: true }),
    // Profile-related API methods (API Profile feature)
    getAPIProfiles: () => Promise.resolve({ success: true, data: [] }),
    saveAPIProfile: () => Promise.resolve({ success: true }),
    updateAPIProfile: () => Promise.resolve({ success: true }),
    deleteAPIProfile: () => Promise.resolve({ success: true }),
    setActiveAPIProfile: () => Promise.resolve({ success: true }),
    testConnection: () => Promise.resolve({ success: true })
  };
}

// Suppress console errors in tests unless explicitly testing error scenarios
const originalConsoleError = console.error;
console.error = (...args: unknown[]) => {
  // Allow certain error messages through for debugging
  const message = args[0]?.toString() || '';
  if (message.includes('[TEST]')) {
    originalConsoleError(...args);
  }
};
