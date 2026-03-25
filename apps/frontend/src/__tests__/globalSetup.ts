/**
 * Global test setup for Vitest
 * This file runs before all tests and doesn't import vitest directly
 */

import { mkdirSync, rmSync, existsSync } from 'node:fs';
import path from 'node:path';

// Test data directory for isolated file operations
export const TEST_DATA_DIR = '/tmp/workpilot-ai-tests';

// Create fresh test directory before all tests
export async function setup() {
  try {
    if (existsSync(TEST_DATA_DIR)) {
      rmSync(TEST_DATA_DIR, { recursive: true, force: true });
    }
  } catch {
    // Ignore errors if directory is in use by another parallel test
  }

  try {
    mkdirSync(TEST_DATA_DIR, { recursive: true });
    mkdirSync(path.join(TEST_DATA_DIR, 'store'), { recursive: true });
  } catch {
    // Ignore errors if directory already exists from another parallel test
  }

  // Setup global mocks
  setupGlobalMocks();
}

// Clean up after all tests
export async function teardown() {
  try {
    if (existsSync(TEST_DATA_DIR)) {
      rmSync(TEST_DATA_DIR, { recursive: true, force: true });
    }
  } catch {
    // Ignore errors
  }
}

// Mock localStorage for tests that need it
export function createLocalStorageMock() {
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
}

// Mock window.electronAPI for renderer tests
export function createElectronAPIMock() {
  return {
    addProject: () => Promise.resolve({ success: true }),
    removeProject: () => Promise.resolve({ success: true }),
    getProjects: () => Promise.resolve({ success: true, data: [] }),
    updateProjectSettings: () => Promise.resolve({ success: true }),
    getTasks: () => Promise.resolve({ success: true, data: [] }),
    createTask: () => Promise.resolve({ success: true, data: { id: 'test-task' } }),
    startTask: () => Promise.resolve({ success: true }),
    stopTask: () => Promise.resolve({ success: true }),
    submitReview: () => Promise.resolve({ success: true }),
    onTaskProgress: () => () => {},
    onTaskError: () => () => {},
    onTaskLog: () => () => {},
    onTaskStatusChange: () => () => {},
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

// Setup global mocks
export function setupGlobalMocks() {
  // Make localStorage available globally
  if (typeof globalThis !== 'undefined') {
    Object.defineProperty(globalThis, 'localStorage', {
      value: createLocalStorageMock()
    });

    // Mock scrollIntoView for Radix Select in jsdom
    if (typeof HTMLElement !== 'undefined' && !HTMLElement.prototype.scrollIntoView) {
      Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
        value: () => {},
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

    // Mock electronAPI
    (globalThis as any).electronAPI = createElectronAPIMock();
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
}
