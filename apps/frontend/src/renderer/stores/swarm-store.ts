import type {
	ParallelismStats,
	SubtaskState,
	SwarmAnalysisEvent,
	SwarmConfig,
	SwarmPhase,
	SwarmStatus,
	SwarmSubtaskEvent,
	SwarmWaveEvent,
} from "@shared/types/swarm";
import { DEFAULT_SWARM_CONFIG } from "@shared/types/swarm";
import { create } from "zustand";

// ─── Store State ────────────────────────────────────────────────────────────

interface SwarmState {
	/** Whether the swarm panel/dialog is open */
	isOpen: boolean;

	/** Whether swarm mode is enabled for the project */
	isEnabled: boolean;

	/** Current swarm execution status */
	status: SwarmStatus | null;

	/** Config for the current/next swarm run */
	config: SwarmConfig;

	/** Analysis results (available before execution) */
	analysisStats: ParallelismStats | null;

	/** Logs per subtask */
	subtaskLogs: Record<string, string[]>;

	/** Loading / running states */
	isAnalyzing: boolean;
	isExecuting: boolean;

	/** Error state */
	error: string | null;
}

// ─── Actions ────────────────────────────────────────────────────────────────

interface SwarmActions {
	open: () => void;
	close: () => void;
	setEnabled: (enabled: boolean) => void;
	setConfig: (config: Partial<SwarmConfig>) => void;
	setError: (error: string | null) => void;

	/** Start dependency analysis (calls IPC) */
	analyzeSpec: (specId: string) => Promise<void>;

	/** Start swarm execution (calls IPC) */
	startSwarm: (specId: string) => Promise<void>;

	/** Cancel running swarm */
	cancelSwarm: () => Promise<void>;

	/** Handle events from the backend process */
	handleAnalysisComplete: (event: SwarmAnalysisEvent) => void;
	handleSwarmStarted: () => void;
	handleSwarmComplete: (status: SwarmStatus) => void;
	handleSwarmFailed: (error: string) => void;
	handleSubtaskStarted: (event: SwarmSubtaskEvent) => void;
	handleSubtaskCompleted: (event: SwarmSubtaskEvent) => void;
	handleSubtaskRetrying: (event: SwarmSubtaskEvent) => void;
	handleWaveStarted: (event: SwarmWaveEvent) => void;
	handleWaveCompleted: (event: SwarmWaveEvent) => void;
	handlePhaseChanged: (phase: SwarmPhase) => void;
	handleSubtaskLog: (subtaskId: string, line: string) => void;

	/** Reset store to initial state */
	reset: () => void;
}

// ─── Initial State ──────────────────────────────────────────────────────────

const initialState: SwarmState = {
	isOpen: false,
	isEnabled: false,
	status: null,
	config: { ...DEFAULT_SWARM_CONFIG },
	analysisStats: null,
	subtaskLogs: {},
	isAnalyzing: false,
	isExecuting: false,
	error: null,
};

// ─── Store ──────────────────────────────────────────────────────────────────

export const useSwarmStore = create<SwarmState & SwarmActions>()(
	(set, get) => ({
		...initialState,

		open: () => set({ isOpen: true }),
		close: () => set({ isOpen: false }),
		setEnabled: (enabled) => set({ isEnabled: enabled }),
		setConfig: (partial) =>
			set((state) => ({ config: { ...state.config, ...partial } })),
		setError: (error) => set({ error }),

		analyzeSpec: async (specId) => {
			set({ isAnalyzing: true, error: null, analysisStats: null });
			try {
				const result = await globalThis.electronAPI.swarm.analyze(
					specId,
					get().config,
				);
				if (result?.parallelismStats) {
					set({
						analysisStats: result.parallelismStats,
						isAnalyzing: false,
					});
				}
			} catch (err) {
				set({
					error: err instanceof Error ? err.message : String(err),
					isAnalyzing: false,
				});
			}
		},

		startSwarm: async (specId) => {
			set({ isExecuting: true, error: null, subtaskLogs: {} });
			try {
				await globalThis.electronAPI.swarm.start(specId, get().config);
			} catch (err) {
				set({
					error: err instanceof Error ? err.message : String(err),
					isExecuting: false,
				});
			}
		},

		cancelSwarm: async () => {
			try {
				await globalThis.electronAPI.swarm.cancel();
			} catch {
				// Best effort
			}
		},

		// ── Event handlers ──────────────────────────────────────────────

		handleAnalysisComplete: (event) => {
			set({
				analysisStats: event.parallelismStats,
				isAnalyzing: false,
				status: {
					phase: "analyzing_dependencies",
					totalSubtasks: event.totalSubtasks,
					completedSubtasks: 0,
					failedSubtasks: 0,
					runningSubtasks: 0,
					totalWaves: event.totalWaves,
					currentWave: -1,
					waves: event.waves,
					nodes: {},
					progressPercent: 0,
					durationSeconds: 0,
					error: null,
					config: get().config,
				},
			});
		},

		handleSwarmStarted: () => {
			set({ isExecuting: true, error: null });
		},

		handleSwarmComplete: (status) => {
			set({
				status,
				isExecuting: false,
			});
		},

		handleSwarmFailed: (error) => {
			set((state) => ({
				error,
				isExecuting: false,
				status: state.status
					? { ...state.status, phase: "failed" as SwarmPhase, error }
					: null,
			}));
		},

		handleSubtaskStarted: (event) => {
			set((state) => {
				if (!state.status) return {};
				const nodes = { ...state.status.nodes };
				const existing = nodes[event.subtaskId];
				if (existing) {
					nodes[event.subtaskId] = {
						...existing,
						state: "running" as SubtaskState,
					};
				}
				return {
					status: {
						...state.status,
						nodes,
						runningSubtasks: state.status.runningSubtasks + 1,
					},
				};
			});
		},

		handleSubtaskCompleted: (event) => {
			set((state) => {
				if (!state.status) return {};
				const nodes = { ...state.status.nodes };
				const existing = nodes[event.subtaskId];
				if (existing) {
					nodes[event.subtaskId] = {
						...existing,
						state: (event.success ? "completed" : "failed") as SubtaskState,
						error: event.error ?? null,
						durationSeconds: event.durationSeconds ?? null,
					};
				}
				return {
					status: {
						...state.status,
						nodes,
						completedSubtasks: event.success
							? state.status.completedSubtasks + 1
							: state.status.completedSubtasks,
						failedSubtasks: event.success
							? state.status.failedSubtasks
							: state.status.failedSubtasks + 1,
						runningSubtasks: Math.max(0, state.status.runningSubtasks - 1),
						progressPercent: event.success
							? Math.round(
									((state.status.completedSubtasks + 1) /
										state.status.totalSubtasks) *
										100,
								)
							: state.status.progressPercent,
					},
				};
			});
		},

		handleSubtaskRetrying: (event) => {
			set((state) => {
				if (!state.status) return {};
				const nodes = { ...state.status.nodes };
				const existing = nodes[event.subtaskId];
				if (existing) {
					nodes[event.subtaskId] = {
						...existing,
						state: "retrying" as SubtaskState,
						retryCount: event.attempt ?? existing.retryCount + 1,
					};
				}
				return { status: { ...state.status, nodes } };
			});
		},

		handleWaveStarted: (event) => {
			set((state) => {
				if (!state.status) return {};
				const waves = [...state.status.waves];
				const wave = waves[event.waveIndex];
				if (wave) {
					waves[event.waveIndex] = {
						...wave,
						state: "running" as SubtaskState,
					};
				}
				return {
					status: {
						...state.status,
						waves,
						currentWave: event.waveIndex,
						phase: "executing_wave" as SwarmPhase,
					},
				};
			});
		},

		handleWaveCompleted: (event) => {
			set((state) => {
				if (!state.status) return {};
				const waves = [...state.status.waves];
				const wave = waves[event.waveIndex];
				if (wave) {
					waves[event.waveIndex] = {
						...wave,
						state: (event.allSucceeded
							? "completed"
							: "failed") as SubtaskState,
						durationSeconds: event.durationSeconds ?? null,
					};
				}
				return { status: { ...state.status, waves } };
			});
		},

		handlePhaseChanged: (phase) => {
			set((state) => {
				if (!state.status) return {};
				return { status: { ...state.status, phase } };
			});
		},

		handleSubtaskLog: (subtaskId, line) => {
			set((state) => {
				const logs = { ...state.subtaskLogs };
				const existing = logs[subtaskId] ?? [];
				// Keep last 200 lines per subtask
				const updated = [...existing, line].slice(-200);
				logs[subtaskId] = updated;
				return { subtaskLogs: logs };
			});
		},

		reset: () => set(initialState),
	}),
);
