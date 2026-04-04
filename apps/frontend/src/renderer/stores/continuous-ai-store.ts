import type {
	ContinuousAIConfig,
	ContinuousAIStatus,
	DaemonAction,
	DaemonEvent,
	ModuleName,
} from "@shared/types/continuous-ai";
import { DEFAULT_CONTINUOUS_AI_CONFIG } from "@shared/types/continuous-ai";
import { create } from "zustand";
import { persist } from "zustand/middleware";

// ─── Store State ────────────────────────────────────────────────────────────

interface ContinuousAIState {
	/** Whether the panel is open */
	isOpen: boolean;

	/** Master config (persisted to localStorage) */
	config: ContinuousAIConfig;

	/** Live daemon status */
	status: ContinuousAIStatus | null;

	/** Actions needing user approval */
	pendingApprovals: DaemonAction[];

	/** Recent action history */
	recentActions: DaemonAction[];

	/** Loading states */
	isStarting: boolean;
	isStopping: boolean;

	/** Error */
	error: string | null;
}

// ─── Actions ────────────────────────────────────────────────────────────────

interface ContinuousAIActions {
	open: () => void;
	close: () => void;
	setConfig: (partial: Partial<ContinuousAIConfig>) => void;
	setModuleConfig: (
		module: ModuleName,
		partial: Record<string, unknown>,
	) => void;
	setError: (error: string | null) => void;

	/** Start the daemon (calls IPC) */
	startDaemon: () => Promise<void>;

	/** Stop the daemon (calls IPC) */
	stopDaemon: () => Promise<void>;

	/** Approve a pending action */
	approveAction: (actionId: string) => Promise<void>;

	/** Reject a pending action */
	rejectAction: (actionId: string) => Promise<void>;

	/** Refresh daemon status from backend */
	refreshStatus: () => Promise<void>;

	/** Handle events from the backend daemon process */
	handleDaemonEvent: (event: DaemonEvent) => void;

	/** Reset to initial state */
	reset: () => void;
}

// ─── Initial State ──────────────────────────────────────────────────────────

const initialState: ContinuousAIState = {
	isOpen: false,
	config: { ...DEFAULT_CONTINUOUS_AI_CONFIG },
	status: null,
	pendingApprovals: [],
	recentActions: [],
	isStarting: false,
	isStopping: false,
	error: null,
};

// ─── Store ──────────────────────────────────────────────────────────────────

export const useContinuousAIStore = create<
	ContinuousAIState & ContinuousAIActions
>()(
	persist(
		(set, get) => ({
			...initialState,

			open: () => set({ isOpen: true }),
			close: () => set({ isOpen: false }),

			setConfig: (partial) =>
				set((state) => {
					const newConfig = { ...state.config, ...partial };
					// Fire-and-forget config update to backend
					globalThis.electronAPI?.continuousAI
						?.updateConfig(newConfig)
						.catch(() => {
							// Intentionally silent - config update is best effort
						});
					return { config: newConfig };
				}),

			setModuleConfig: (module, partial) =>
				set((state) => {
					const moduleKey = module.replaceAll(/_([a-z])/g, (_, c) =>
						c.toUpperCase(),
					) as keyof ContinuousAIConfig;
					const current = state.config[moduleKey];
					if (typeof current === "object" && current !== null) {
						const newConfig = {
							...state.config,
							[moduleKey]: { ...current, ...partial },
						};
						globalThis.electronAPI?.continuousAI
							?.updateConfig(newConfig)
							.catch(() => {
								// Intentionally silent - config update is best effort
							});
						return { config: newConfig };
					}
					return {};
				}),

			setError: (error) => set({ error }),

			startDaemon: async () => {
				set({ isStarting: true, error: null });
				try {
					await globalThis.electronAPI.continuousAI.start(get().config);
				} catch (err) {
					set({ error: err instanceof Error ? err.message : String(err) });
				} finally {
					set({ isStarting: false });
				}
			},

			stopDaemon: async () => {
				set({ isStopping: true });
				try {
					await globalThis.electronAPI.continuousAI.stop();
				} catch {
					// Best effort
				} finally {
					set({ isStopping: false, status: null });
				}
			},

			approveAction: async (actionId) => {
				try {
					await globalThis.electronAPI.continuousAI.approveAction(actionId);
					set((state) => ({
						pendingApprovals: state.pendingApprovals.filter(
							(a) => a.id !== actionId,
						),
					}));
				} catch (err) {
					set({ error: err instanceof Error ? err.message : String(err) });
				}
			},

			rejectAction: async (actionId) => {
				try {
					await globalThis.electronAPI.continuousAI.rejectAction(actionId);
					set((state) => ({
						pendingApprovals: state.pendingApprovals.filter(
							(a) => a.id !== actionId,
						),
					}));
				} catch {
					// Best effort
				}
			},

			refreshStatus: async () => {
				try {
					const status = await globalThis.electronAPI.continuousAI.getStatus();
					if (status) {
						set({ status });
					}
				} catch {
					// Silent — daemon might not be running
				}
			},

			handleDaemonEvent: (event) => {
				switch (event.type) {
					case "daemon_started":
						set({
							status: {
								running: true,
								startedAt: event.timestamp,
								modules: {},
								recentActions: [],
								totalCostTodayUsd: 0,
								dailyBudgetUsd: get().config.dailyBudgetUsd,
								enabledModulesCount: 0,
								isOverBudget: false,
							},
						});
						break;

					case "daemon_stopped":
						set((state) => ({
							status: state.status ? { ...state.status, running: false } : null,
						}));
						break;

					case "action_needs_approval": {
						const action = event as unknown as DaemonAction;
						if (action.id) {
							set((state) => ({
								pendingApprovals: [...state.pendingApprovals, action],
							}));
						}
						break;
					}

					case "action_completed": {
						const completedAction = event as unknown as DaemonAction;
						if (completedAction.id) {
							set((state) => ({
								recentActions: [...state.recentActions, completedAction].slice(
									-50,
								),
								pendingApprovals: state.pendingApprovals.filter(
									(a) => a.id !== completedAction.id,
								),
							}));
						}
						break;
					}

					case "budget_exceeded":
						set({ error: "Daily budget exceeded — daemon paused" });
						break;

					case "module_error":
						set({
							error: `Module error: ${String(event.module)} — ${String(event.error)}`,
						});
						break;

					default:
						break;
				}
			},

			reset: () => set({ ...initialState, config: get().config }),
		}),
		{
			name: "continuous-ai-config",
			partialize: (state) => ({ config: state.config }),
		},
	),
);

/** Imperative opener for use outside React */
export const openContinuousAIPanel = () =>
	useContinuousAIStore.getState().open();
