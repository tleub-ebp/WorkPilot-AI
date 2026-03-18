import { create } from 'zustand';

export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'changes_requested';

export interface SpecApprovalRecord {
  specNumber: string;
  specName: string;
  specDir: string;
  status: ApprovalStatus;
  reviewedAt?: string;
  feedback?: string;
  amendments?: string;
}

export interface SpecContent {
  spec_number: string;
  spec_md?: string;
  requirements_json?: string;
  context_json?: string;
  implementation_plan_json?: string;
}

interface SpecApprovalState {
  pendingSpecs: SpecApprovalRecord[];
  history: SpecApprovalRecord[];
  selectedSpec: SpecApprovalRecord | null;
  specContent: SpecContent | null;
  isLoading: boolean;
  isSubmitting: boolean;
  error: string | null;

  loadPendingSpecs: (projectDir: string) => Promise<void>;
  loadHistory: (projectDir: string) => Promise<void>;
  selectSpec: (spec: SpecApprovalRecord | null) => void;
  loadSpecContent: (projectDir: string, specNumber: string) => Promise<void>;
  approve: (projectDir: string, specNumber: string, amendments?: string) => Promise<void>;
  reject: (projectDir: string, specNumber: string, feedback: string) => Promise<void>;
  requestChanges: (projectDir: string, specNumber: string, feedback: string) => Promise<void>;
  clearError: () => void;
}

export const useSpecApprovalStore = create<SpecApprovalState>((set, get) => ({
  pendingSpecs: [],
  history: [],
  selectedSpec: null,
  specContent: null,
  isLoading: false,
  isSubmitting: false,
  error: null,

  loadPendingSpecs: async (projectDir) => {
    set({ isLoading: true, error: null });
    try {
      const result = await globalThis.electronAPI.invoke('specApproval:getPendingSpecs', projectDir);
      if (result.success) {
        set({ pendingSpecs: result.data as SpecApprovalRecord[] });
      } else {
        set({ error: result.error ?? 'Failed to load pending specs' });
      }
    } catch (err) {
      set({ error: String(err) });
    } finally {
      set({ isLoading: false });
    }
  },

  loadHistory: async (projectDir) => {
    try {
      const result = await globalThis.electronAPI.invoke('specApproval:getHistory', projectDir);
      if (result.success) {
        set({ history: result.data as SpecApprovalRecord[] });
      }
    } catch { /* ignore */ }
  },

  selectSpec: (spec) => {
    set({ selectedSpec: spec, specContent: null });
  },

  loadSpecContent: async (projectDir, specNumber) => {
    set({ isLoading: true });
    try {
      const result = await globalThis.electronAPI.invoke('specApproval:getSpec', projectDir, specNumber);
      if (result.success) {
        set({ specContent: result.data as SpecContent });
      } else {
        set({ error: result.error ?? 'Failed to load spec content' });
      }
    } catch (err) {
      set({ error: String(err) });
    } finally {
      set({ isLoading: false });
    }
  },

  approve: async (projectDir, specNumber, amendments) => {
    set({ isSubmitting: true, error: null });
    try {
      const result = await globalThis.electronAPI.invoke('specApproval:approve', projectDir, {
        specNumber,
        amendments,
      });
      if (result.success) {
        set((state) => ({
          pendingSpecs: state.pendingSpecs.filter(s => s.specNumber !== specNumber),
          selectedSpec: null,
          specContent: null,
        }));
        await get().loadHistory(projectDir);
      } else {
        set({ error: result.error ?? 'Approval failed' });
      }
    } catch (err) {
      set({ error: String(err) });
    } finally {
      set({ isSubmitting: false });
    }
  },

  reject: async (projectDir, specNumber, feedback) => {
    set({ isSubmitting: true, error: null });
    try {
      const result = await globalThis.electronAPI.invoke('specApproval:reject', projectDir, {
        specNumber,
        feedback,
      });
      if (result.success) {
        set((state) => ({
          pendingSpecs: state.pendingSpecs.filter(s => s.specNumber !== specNumber),
          selectedSpec: null,
          specContent: null,
        }));
        await get().loadHistory(projectDir);
      } else {
        set({ error: result.error ?? 'Rejection failed' });
      }
    } catch (err) {
      set({ error: String(err) });
    } finally {
      set({ isSubmitting: false });
    }
  },

  requestChanges: async (projectDir, specNumber, feedback) => {
    set({ isSubmitting: true, error: null });
    try {
      const result = await globalThis.electronAPI.invoke('specApproval:requestChanges', projectDir, {
        specNumber,
        feedback,
      });
      if (result.success) {
        set((state) => ({
          pendingSpecs: state.pendingSpecs.map(s =>
            s.specNumber === specNumber ? { ...s, status: 'changes_requested' as ApprovalStatus } : s
          ),
          selectedSpec: null,
          specContent: null,
        }));
      } else {
        set({ error: result.error ?? 'Request changes failed' });
      }
    } catch (err) {
      set({ error: String(err) });
    } finally {
      set({ isSubmitting: false });
    }
  },

  clearError: () => set({ error: null }),
}));
