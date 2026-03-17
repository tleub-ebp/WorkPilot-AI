/**
 * Self-Healing Codebase + Incident Responder Store
 *
 * Feature #3 (Tier S+) - Zustand store for managing self-healing state.
 */

import { create } from 'zustand';
import type {
  CICDConfig,
  FragilityReport,
  HealingOperation,
  Incident,
  IncidentMode,
  ProductionConfig,
  ProactiveConfig,
  SelfHealingDashboardData,
  SelfHealingStats,
} from '@shared/types/self-healing';

// ── Store State ─────────────────────────────────────────────

interface SelfHealingState {
  // Data
  incidents: Incident[];
  activeOperations: HealingOperation[];
  fragilityReports: FragilityReport[];
  stats: SelfHealingStats;

  // Configuration
  cicdConfig: CICDConfig;
  productionConfig: ProductionConfig;
  proactiveConfig: ProactiveConfig;

  // UI State
  activeTab: IncidentMode;
  isLoading: boolean;
  isScanning: boolean;
  error: string | null;

  // Actions
  setActiveTab: (tab: IncidentMode) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setDashboardData: (data: SelfHealingDashboardData) => void;
  setIncidents: (incidents: Incident[]) => void;
  setFragilityReports: (reports: FragilityReport[]) => void;
  setActiveOperations: (operations: HealingOperation[]) => void;
  setCICDConfig: (config: Partial<CICDConfig>) => void;
  setProductionConfig: (config: Partial<ProductionConfig>) => void;
  setProactiveConfig: (config: Partial<ProactiveConfig>) => void;
  setScanning: (scanning: boolean) => void;

  // Async actions
  fetchDashboard: (projectPath: string) => Promise<void>;
  triggerProactiveScan: (projectPath: string) => Promise<void>;
  triggerFix: (projectPath: string, incidentId: string) => Promise<void>;
  dismissIncident: (projectPath: string, incidentId: string) => Promise<void>;
  retryIncident: (projectPath: string, incidentId: string) => Promise<void>;
}

// ── Default Values ──────────────────────────────────────────

const defaultStats: SelfHealingStats = {
  totalIncidents: 0,
  resolvedIncidents: 0,
  activeIncidents: 0,
  avgResolutionTime: 0,
  autoFixRate: 0,
};

const defaultCICDConfig: CICDConfig = {
  enabled: false,
  watchBranches: ['main', 'develop'],
  autoFixEnabled: true,
  autoCreatePR: true,
};

const defaultProductionConfig: ProductionConfig = {
  enabled: false,
  connectedSources: [],
  autoAnalyze: true,
  autoFix: false,
  severityThreshold: 'high',
};

const defaultProactiveConfig: ProactiveConfig = {
  enabled: false,
  scanFrequency: 'weekly',
  riskThreshold: 40,
  autoGenerateTests: false,
};

// ── Store ───────────────────────────────────────────────────

export const useSelfHealingStore = create<SelfHealingState>((set, get) => ({
  // Initial state
  incidents: [],
  activeOperations: [],
  fragilityReports: [],
  stats: defaultStats,
  cicdConfig: defaultCICDConfig,
  productionConfig: defaultProductionConfig,
  proactiveConfig: defaultProactiveConfig,
  activeTab: 'cicd',
  isLoading: false,
  isScanning: false,
  error: null,

  // Simple setters
  setActiveTab: (tab) => set({ activeTab: tab }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
  setScanning: (scanning) => set({ isScanning: scanning }),

  setDashboardData: (data) =>
    set({
      incidents: data.incidents,
      activeOperations: data.activeOperations,
      fragilityReports: data.fragilityReports,
      stats: data.stats,
    }),

  setIncidents: (incidents) => set({ incidents }),
  setFragilityReports: (reports) => set({ fragilityReports: reports }),
  setActiveOperations: (operations) => set({ activeOperations: operations }),

  setCICDConfig: (config) =>
    set((state) => ({
      cicdConfig: { ...state.cicdConfig, ...config },
    })),

  setProductionConfig: (config) =>
    set((state) => ({
      productionConfig: { ...state.productionConfig, ...config },
    })),

  setProactiveConfig: (config) =>
    set((state) => ({
      proactiveConfig: { ...state.proactiveConfig, ...config },
    })),

  // Async actions
  fetchDashboard: async (projectPath: string) => {
    set({ isLoading: true, error: null });
    try {
      const result = await window.electronAPI.invoke('selfHealing:getDashboard', projectPath);
      if (result?.success && result.data) {
        get().setDashboardData(result.data);
      }
    } catch (error) {
      set({ error: String(error) });
    } finally {
      set({ isLoading: false });
    }
  },

  triggerProactiveScan: async (projectPath: string) => {
    set({ isScanning: true, error: null });
    try {
      await window.electronAPI.invoke('selfHealing:proactive:scan', projectPath);
      // Refresh dashboard after scan
      await get().fetchDashboard(projectPath);
    } catch (error) {
      set({ error: String(error) });
    } finally {
      set({ isScanning: false });
    }
  },

  triggerFix: async (projectPath: string, incidentId: string) => {
    try {
      await window.electronAPI.invoke('selfHealing:triggerFix', projectPath, incidentId);
      await get().fetchDashboard(projectPath);
    } catch (error) {
      set({ error: String(error) });
    }
  },

  dismissIncident: async (projectPath: string, incidentId: string) => {
    try {
      await window.electronAPI.invoke('selfHealing:dismissIncident', projectPath, incidentId);
      set((state) => ({
        incidents: state.incidents.map((i) =>
          i.id === incidentId ? { ...i, status: 'resolved' as const } : i
        ),
      }));
    } catch (error) {
      set({ error: String(error) });
    }
  },

  retryIncident: async (projectPath: string, incidentId: string) => {
    try {
      await window.electronAPI.invoke('selfHealing:retryIncident', projectPath, incidentId);
      await get().fetchDashboard(projectPath);
    } catch (error) {
      set({ error: String(error) });
    }
  },
}));
