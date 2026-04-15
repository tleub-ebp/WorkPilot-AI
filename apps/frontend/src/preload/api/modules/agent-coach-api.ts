/**
 * Agent Coach API
 *
 * Renderer-side bridge to the agent coach runner which analyses persisted
 * agent run records and returns a coaching report.
 */

import type { CoachReport } from "../../../shared/types/agent-coach";
import { createIpcListener, invokeIpc } from "./ipc-utils";

export interface AgentCoachRunOptions {
	projectPath: string;
}

export interface AgentCoachResult {
	report: CoachReport;
}

export interface AgentCoachEvent {
	type: "start" | "progress" | "complete";
	data: { status?: string; totalRuns?: number; tips?: number };
}

export interface AgentCoachAPI {
	runAgentCoachScan: (
		options: AgentCoachRunOptions,
	) => Promise<AgentCoachResult>;
	cancelAgentCoachScan: () => Promise<boolean>;
	onAgentCoachEvent: (
		callback: (event: AgentCoachEvent) => void,
	) => () => void;
	onAgentCoachResult: (
		callback: (result: AgentCoachResult) => void,
	) => () => void;
	onAgentCoachError: (callback: (error: string) => void) => () => void;
}

export const createAgentCoachAPI = (): AgentCoachAPI => ({
	runAgentCoachScan: (options: AgentCoachRunOptions) =>
		invokeIpc<AgentCoachResult>("agentCoach:run", options),

	cancelAgentCoachScan: () => invokeIpc<boolean>("agentCoach:cancel"),

	onAgentCoachEvent: (callback) =>
		createIpcListener<[AgentCoachEvent]>("agent-coach-event", (payload) =>
			callback(payload),
		),

	onAgentCoachResult: (callback) =>
		createIpcListener<[AgentCoachResult]>("agent-coach-result", (payload) =>
			callback(payload),
		),

	onAgentCoachError: (callback) =>
		createIpcListener<[string]>("agent-coach-error", (payload) =>
			callback(payload),
		),
});
