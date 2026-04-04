/**
 * Mission Control Store — Zustand state management for the Multi-Agent Orchestration Hub.
 *
 * Manages:
 * - Agent slots (create, remove, update config)
 * - Agent controls (start, pause, resume, stop)
 * - Live state polling from the backend
 * - Decision tree data per agent
 * - Session lifecycle
 */

import { create } from "zustand";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface TokenUsage {
	input_tokens: number;
	output_tokens: number;
	total_tokens: number;
	estimated_cost_usd: number;
}

export interface AgentSlot {
	id: string;
	name: string;
	role: string;
	status: "idle" | "running" | "paused" | "completed" | "error" | "waiting";
	provider: string;
	model: string;
	model_label: string;
	current_task: string;
	current_step: string;
	progress: number;
	tokens: TokenUsage;
	active_files: string[];
	current_thinking: string;
	last_tool_call: string;
	last_tool_input: string;
	decision_path: string[];
	started_at: number | null;
	completed_at: number | null;
	elapsed_seconds: number;
	streaming_session_id: string | null;
	error_message: string;
}

export interface DecisionNode {
	id: string;
	parent_id: string | null;
	node_type:
		| "root"
		| "thinking"
		| "tool_call"
		| "decision"
		| "result"
		| "error"
		| "branch";
	status: "active" | "completed" | "failed" | "skipped";
	label: string;
	description: string;
	timestamp: number;
	tool_name: string;
	tool_input: string;
	tool_output: string;
	options_considered: string[];
	chosen_option: string;
	reasoning: string;
	children: string[];
	duration_ms: number;
}

export interface DecisionTree {
	agent_id: string;
	root_id: string | null;
	current_node_id: string | null;
	node_count: number;
	nodes: Record<string, DecisionNode>;
}

export interface MCSession {
	session_id: string;
	is_active: boolean;
	created_at: number;
	agent_count: number;
	running_count: number;
	total_tokens: number;
	total_cost_usd: number;
	elapsed_seconds: number;
}

export interface MCEvent {
	type: string;
	timestamp: number;
	data: Record<string, unknown>;
}

export interface MissionControlState {
	// Session
	session: MCSession | null;
	isActive: boolean;

	// Agents
	agents: AgentSlot[];
	selectedAgentId: string | null;

	// Decision trees
	decisionTrees: Record<string, DecisionTree>;

	// Events
	events: MCEvent[];

	// Polling
	isPolling: boolean;
	pollIntervalMs: number;
	lastPollAt: number | null;

	// Loading states
	isLoading: boolean;
	error: string | null;

	// Actions
	startSession: (name?: string) => Promise<void>;
	stopSession: () => Promise<void>;
	fetchState: () => Promise<void>;
	createAgent: (
		name: string,
		role: string,
		provider: string,
		model: string,
		modelLabel: string,
	) => Promise<AgentSlot | null>;
	removeAgent: (agentId: string) => Promise<void>;
	updateAgentConfig: (
		agentId: string,
		config: Partial<{
			provider: string;
			model: string;
			model_label: string;
			name: string;
			role: string;
		}>,
	) => Promise<void>;
	startAgent: (agentId: string, task: string) => Promise<void>;
	pauseAgent: (agentId: string) => Promise<void>;
	resumeAgent: (agentId: string) => Promise<void>;
	stopAgent: (agentId: string) => Promise<void>;
	selectAgent: (agentId: string | null) => void;
	startPolling: () => void;
	stopPolling: () => void;
	fetchDecisionTree: (agentId: string) => Promise<void>;
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

const getBackendUrl = () => {
	return import.meta?.env?.VITE_BACKEND_URL || "";
};

async function mcFetch<T = Record<string, unknown>>(
	path: string,
	options?: RequestInit,
): Promise<T> {
	const url = `${getBackendUrl()}/api/mission-control${path}`;
	const res = await fetch(url, {
		headers: { "Content-Type": "application/json" },
		...options,
	});
	if (!res.ok) {
		const err = await res.text();
		throw new Error(err || `HTTP ${res.status}`);
	}
	return res.json();
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

let pollTimer: ReturnType<typeof setInterval> | null = null;

export const useMissionControlStore = create<MissionControlState>(
	(set, get) => ({
		// Initial state
		session: null,
		isActive: false,
		agents: [],
		selectedAgentId: null,
		decisionTrees: {},
		events: [],
		isPolling: false,
		pollIntervalMs: 1500,
		lastPollAt: null,
		isLoading: false,
		error: null,

		// --- Session ---
		startSession: async (name = "Mission Control") => {
			set({ isLoading: true, error: null });
			try {
				const res = await mcFetch<{ success: boolean; session: MCSession }>(
					"/session/start",
					{
						method: "POST",
						body: JSON.stringify({ name }),
					},
				);
				set({ session: res.session, isActive: true, isLoading: false });
				get().startPolling();
			} catch (e) {
				set({ error: (e as Error).message, isLoading: false });
			}
		},

		stopSession: async () => {
			get().stopPolling();
			try {
				await mcFetch("/session/stop", { method: "POST" });
			} catch {
				// ignore
			}
			set({
				session: null,
				isActive: false,
				agents: [],
				decisionTrees: {},
				events: [],
			});
		},

		// --- State fetch ---
		fetchState: async () => {
			try {
				const res = await mcFetch<{
					success: boolean;
					state: {
						session: MCSession;
						agents: AgentSlot[];
						decision_trees: Record<string, DecisionTree>;
						recent_events: MCEvent[];
					};
				}>("/state");
				if (res.success) {
					set({
						session: res.state.session,
						isActive: res.state.session.is_active,
						agents: res.state.agents,
						decisionTrees: res.state.decision_trees,
						events: res.state.recent_events,
						lastPollAt: Date.now(),
						error: null,
					});
				}
			} catch (e) {
				set({ error: (e as Error).message });
			}
		},

		// --- Agent CRUD ---
		createAgent: async (name, role, provider, model, modelLabel) => {
			set({ isLoading: true });
			try {
				const res = await mcFetch<{ success: boolean; agent: AgentSlot }>(
					"/agents",
					{
						method: "POST",
						body: JSON.stringify({
							name,
							role,
							provider,
							model,
							model_label: modelLabel,
						}),
					},
				);
				if (res.success) {
					set((s) => ({ agents: [...s.agents, res.agent], isLoading: false }));
					return res.agent;
				}
				set({ isLoading: false });
				return null;
			} catch (e) {
				set({ error: (e as Error).message, isLoading: false });
				return null;
			}
		},

		removeAgent: async (agentId) => {
			try {
				await mcFetch(`/agents/${agentId}`, { method: "DELETE" });
				set((s) => ({
					agents: s.agents.filter((a) => a.id !== agentId),
					selectedAgentId:
						s.selectedAgentId === agentId ? null : s.selectedAgentId,
				}));
			} catch (e) {
				set({ error: (e as Error).message });
			}
		},

		updateAgentConfig: async (agentId, config) => {
			try {
				const res = await mcFetch<{ success: boolean; agent: AgentSlot }>(
					`/agents/${agentId}`,
					{
						method: "PUT",
						body: JSON.stringify(config),
					},
				);
				if (res.success) {
					set((s) => ({
						agents: s.agents.map((a) => (a.id === agentId ? res.agent : a)),
					}));
				}
			} catch (e) {
				set({ error: (e as Error).message });
			}
		},

		// --- Agent control ---
		startAgent: async (agentId, task) => {
			try {
				await mcFetch(`/agents/${agentId}/start`, {
					method: "POST",
					body: JSON.stringify({ task }),
				});
			} catch (e) {
				set({ error: (e as Error).message });
			}
		},

		pauseAgent: async (agentId) => {
			try {
				await mcFetch(`/agents/${agentId}/pause`, { method: "POST" });
			} catch (e) {
				set({ error: (e as Error).message });
			}
		},

		resumeAgent: async (agentId) => {
			try {
				await mcFetch(`/agents/${agentId}/resume`, { method: "POST" });
			} catch (e) {
				set({ error: (e as Error).message });
			}
		},

		stopAgent: async (agentId) => {
			try {
				await mcFetch(`/agents/${agentId}/stop`, { method: "POST" });
			} catch (e) {
				set({ error: (e as Error).message });
			}
		},

		selectAgent: (agentId) => {
			set({ selectedAgentId: agentId });
		},

		// --- Polling ---
		startPolling: () => {
			if (pollTimer) return;
			set({ isPolling: true });
			pollTimer = setInterval(() => {
				get().fetchState();
			}, get().pollIntervalMs);
			// Immediate first fetch
			get().fetchState();
		},

		stopPolling: () => {
			if (pollTimer) {
				clearInterval(pollTimer);
				pollTimer = null;
			}
			set({ isPolling: false });
		},

		// --- Decision tree ---
		fetchDecisionTree: async (agentId) => {
			try {
				const res = await mcFetch<{ success: boolean; tree: DecisionTree }>(
					`/agents/${agentId}/decision-tree`,
				);
				if (res.success) {
					set((s) => ({
						decisionTrees: { ...s.decisionTrees, [agentId]: res.tree },
					}));
				}
			} catch {
				// ignore
			}
		},
	}),
);
