/**
 * Browser Agent Store
 *
 * Feature #20 — Zustand store for the Built-in Browser Agent.
 */

import { create } from 'zustand';
import type {
  BaselineInfo,
  BrowserAgentDashboardData,
  BrowserAgentStats,
  BrowserAgentTab,
  BrowserStatus,
  ComparisonResult,
  ScreenshotInfo,
  TestRunResult,
} from '@shared/types/browser-agent';

// ── Store State ─────────────────────────────────────────────

interface BrowserAgentState {
  // Data
  stats: BrowserAgentStats;
  screenshots: ScreenshotInfo[];
  baselines: BaselineInfo[];
  comparisons: ComparisonResult[];
  recentTestRun: TestRunResult | null;

  // Browser state
  currentUrl: string;
  browserStatus: BrowserStatus;
  browserScreenshot: string | null;

  // UI state
  activeTab: BrowserAgentTab;
  isLoading: boolean;
  isRunningTests: boolean;
  isCapturing: boolean;
  isComparing: boolean;
  error: string | null;

  // Actions
  setActiveTab: (tab: BrowserAgentTab) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setCurrentUrl: (url: string) => void;
  setBrowserStatus: (status: BrowserStatus) => void;
  setBrowserScreenshot: (screenshot: string | null) => void;
  setDashboardData: (data: BrowserAgentDashboardData) => void;

  // Async actions
  fetchDashboard: (projectPath: string) => Promise<void>;
  captureScreenshot: (projectPath: string, name: string, url: string) => Promise<void>;
  setBaseline: (projectPath: string, name: string, screenshotPath?: string) => Promise<void>;
  compareScreenshot: (projectPath: string, name: string, url?: string) => Promise<void>;
  deleteBaseline: (projectPath: string, name: string) => Promise<void>;
  runTests: (projectPath: string) => Promise<void>;
  loadScreenshotImage: (screenshotPath: string) => Promise<string | null>;
}

// ── Default Values ──────────────────────────────────────────

const defaultStats: BrowserAgentStats = {
  totalTests: 0,
  passRate: 0,
  screenshotsCaptured: 0,
  regressionsDetected: 0,
};

// ── Store ───────────────────────────────────────────────────

export const useBrowserAgentStore = create<BrowserAgentState>((set, get) => ({
  // Initial state
  stats: { ...defaultStats },
  screenshots: [],
  baselines: [],
  comparisons: [],
  recentTestRun: null,
  currentUrl: '',
  browserStatus: 'idle',
  browserScreenshot: null,
  activeTab: 'browser',
  isLoading: false,
  isRunningTests: false,
  isCapturing: false,
  isComparing: false,
  error: null,

  // Simple setters
  setActiveTab: (tab) => set({ activeTab: tab }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
  setCurrentUrl: (url) => set({ currentUrl: url }),
  setBrowserStatus: (status) => set({ browserStatus: status }),
  setBrowserScreenshot: (screenshot) => set({ browserScreenshot: screenshot }),
  setDashboardData: (data) =>
    set({
      stats: data.stats,
      screenshots: data.screenshots,
      baselines: data.baselines,
      comparisons: data.comparisons,
      recentTestRun: data.recentTestRun,
    }),

  // Async: Fetch dashboard data
  fetchDashboard: async (projectPath) => {
    set({ isLoading: true, error: null });
    try {
      const result = await window.electronAPI.invoke('browserAgent:getDashboard', projectPath);
      if (result?.success && result.data) {
        get().setDashboardData(result.data);
      }
    } catch (err) {
      set({ error: String(err) });
    } finally {
      set({ isLoading: false });
    }
  },

  // Async: Capture screenshot
  captureScreenshot: async (projectPath, name, url) => {
    set({ isCapturing: true, error: null, browserStatus: 'navigating' });
    try {
      const result = await window.electronAPI.invoke(
        'browserAgent:captureScreenshot',
        projectPath,
        name,
        url
      );
      if (result?.success && result.data) {
        // Reload dashboard to refresh screenshot list
        await get().fetchDashboard(projectPath);
        // Load the captured screenshot for preview
        const imgResult = await get().loadScreenshotImage(result.data.path);
        if (imgResult) {
          set({ browserScreenshot: imgResult, browserStatus: 'ready' });
        }
      } else {
        set({ error: result?.error || 'Screenshot capture failed', browserStatus: 'error' });
      }
    } catch (err) {
      set({ error: String(err), browserStatus: 'error' });
    } finally {
      set({ isCapturing: false });
    }
  },

  // Async: Set baseline
  setBaseline: async (projectPath, name, screenshotPath) => {
    set({ isLoading: true, error: null });
    try {
      const result = await window.electronAPI.invoke(
        'browserAgent:setBaseline',
        projectPath,
        name,
        screenshotPath
      );
      if (result?.success) {
        await get().fetchDashboard(projectPath);
      } else {
        set({ error: result?.error || 'Failed to set baseline' });
      }
    } catch (err) {
      set({ error: String(err) });
    } finally {
      set({ isLoading: false });
    }
  },

  // Async: Compare screenshot against baseline
  compareScreenshot: async (projectPath, name, url) => {
    set({ isComparing: true, error: null });
    try {
      const result = await window.electronAPI.invoke(
        'browserAgent:compare',
        projectPath,
        name,
        url
      );
      if (result?.success && result.data) {
        set((state) => ({
          comparisons: [
            result.data,
            ...state.comparisons.filter(
              (c: ComparisonResult) => c.name !== result.data.name
            ),
          ],
        }));
      } else {
        set({ error: result?.error || 'Comparison failed' });
      }
    } catch (err) {
      set({ error: String(err) });
    } finally {
      set({ isComparing: false });
    }
  },

  // Async: Delete baseline
  deleteBaseline: async (projectPath, name) => {
    set({ isLoading: true, error: null });
    try {
      await window.electronAPI.invoke('browserAgent:deleteBaseline', projectPath, name);
      await get().fetchDashboard(projectPath);
    } catch (err) {
      set({ error: String(err) });
    } finally {
      set({ isLoading: false });
    }
  },

  // Async: Run E2E tests
  runTests: async (projectPath) => {
    set({ isRunningTests: true, error: null });
    try {
      const result = await window.electronAPI.invoke('browserAgent:runTests', projectPath);
      if (result?.success && result.data) {
        set({ recentTestRun: result.data });
      } else {
        set({ error: result?.error || 'Test run failed' });
      }
    } catch (err) {
      set({ error: String(err) });
    } finally {
      set({ isRunningTests: false });
    }
  },

  // Async: Load screenshot image as base64
  loadScreenshotImage: async (screenshotPath) => {
    try {
      const result = await window.electronAPI.invoke(
        'browserAgent:getScreenshotImage',
        screenshotPath
      );
      if (result?.success && result.data) {
        return `data:${result.data.mimeType};base64,${result.data.base64}`;
      }
    } catch {
      // Ignore load errors
    }
    return null;
  },
}));
