/**
 * Test setup file for Vitest
 * This file sets up the test environment without importing vitest directly
 */

// Mock localStorage for tests that need it
const createLocalStorageMock = () => {
  let store: Record<string, string> = {};
  let shouldThrow = false;
  let throwError: Error | null = null;

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      if (shouldThrow && throwError) {
        throw throwError;
      }
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
    // Helper methods for testing
    _setShouldThrow: (throwNow: boolean, error: Error | null = null) => {
      shouldThrow = throwNow;
      throwError = error;
    },
    _getStore: () => ({ ...store })
  };
};

const localStorageMock = createLocalStorageMock();

// Make localStorage available globally
if (typeof globalThis !== 'undefined') {
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
  if (globalThis.requestAnimationFrame === undefined) {
    globalThis.requestAnimationFrame = (callback: FrameRequestCallback) => {
      return setTimeout(() => callback(Date.now()), 0) as unknown as number;
    };
    globalThis.cancelAnimationFrame = (id: number) => {
      clearTimeout(id);
    };
  }

  // Mock window.electronAPI for renderer tests
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
  const message = typeof args[0] === 'string' ? args[0] : JSON.stringify(args[0]);
  if (message.includes('[TEST]')) {
    originalConsoleError(...args);
  }
};
