import { create } from "zustand";
import type {
	OfflineModelCatalog,
	OfflinePolicy,
	OfflineReport,
	OfflineStatus,
} from "../../preload/api/modules/offline-mode-api";

interface OfflineModeState {
	status: OfflineStatus | null;
	policy: OfflinePolicy | null;
	report: OfflineReport | null;
	catalog: OfflineModelCatalog | null;
	loading: boolean;
	saving: boolean;
	scanning: boolean;
	error: string | null;
	dirty: boolean;

	loadAll: (projectPath: string) => Promise<void>;
	refreshStatus: (projectPath: string) => Promise<void>;
	scan: (projectPath: string, force?: boolean) => Promise<void>;
	setAirgap: (value: boolean) => void;
	setRouting: (task: string, provider: string, model: string) => void;
	addRoutingRow: (task: string) => void;
	removeRoutingRow: (task: string) => void;
	save: (projectPath: string) => Promise<void>;
}

export const useOfflineModeStore = create<OfflineModeState>((set, get) => ({
	status: null,
	policy: null,
	report: null,
	catalog: null,
	loading: false,
	saving: false,
	scanning: false,
	error: null,
	dirty: false,

	loadAll: async (projectPath) => {
		set({ loading: true, error: null });
		try {
			const [status, policyRes, report, catalog] = await Promise.all([
				globalThis.electronAPI.getOfflineStatus(projectPath),
				globalThis.electronAPI.getOfflinePolicy(projectPath),
				globalThis.electronAPI.getOfflineReport(projectPath),
				globalThis.electronAPI.scanOfflineModels(projectPath),
			]);
			set({
				status,
				policy: policyRes.policy,
				report,
				catalog,
				loading: false,
				dirty: false,
			});
		} catch (e) {
			set({ error: String(e), loading: false });
		}
	},

	refreshStatus: async (projectPath) => {
		try {
			const status = await globalThis.electronAPI.getOfflineStatus(projectPath);
			set({ status });
		} catch (e) {
			set({ error: String(e) });
		}
	},

	scan: async (projectPath, force) => {
		set({ scanning: true, error: null });
		try {
			const catalog = await globalThis.electronAPI.scanOfflineModels(
				projectPath,
				force,
			);
			set({ catalog, scanning: false });
		} catch (e) {
			set({ error: String(e), scanning: false });
		}
	},

	setAirgap: (value) =>
		set((s) =>
			s.policy
				? { policy: { ...s.policy, airgapStrict: value }, dirty: true }
				: s,
		),

	setRouting: (task, provider, model) =>
		set((s) =>
			s.policy
				? {
						policy: {
							...s.policy,
							routing: { ...s.policy.routing, [task]: { provider, model } },
						},
						dirty: true,
					}
				: s,
		),

	addRoutingRow: (task) =>
		set((s) => {
			if (!s.policy || !task.trim()) return s;
			if (s.policy.routing[task]) return s;
			return {
				policy: {
					...s.policy,
					routing: {
						...s.policy.routing,
						[task]: {
							provider: s.policy.defaultProvider,
							model: "claude-sonnet-4-6",
						},
					},
				},
				dirty: true,
			};
		}),

	removeRoutingRow: (task) =>
		set((s) => {
			if (!s.policy) return s;
			const { [task]: _, ...rest } = s.policy.routing;
			return { policy: { ...s.policy, routing: rest }, dirty: true };
		}),

	save: async (projectPath) => {
		const policy = get().policy;
		if (!policy) return;
		set({ saving: true, error: null });
		try {
			await globalThis.electronAPI.setOfflinePolicy(projectPath, policy);
			set({ saving: false, dirty: false });
		} catch (e) {
			set({ error: String(e), saving: false });
		}
	},
}));
