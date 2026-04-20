/**
 * Agent Debugger API — renderer-side bridge.
 *
 * Provider-agnostic: the debugger operates on Claude Agent SDK hook events,
 * which look identical regardless of the underlying provider (Anthropic,
 * OpenAI, Copilot, Windsurf, Ollama, …).
 */

import { invokeIpc } from "./ipc-utils";

export interface BreakpointSpec {
	id: string;
	tool: string;
	path_pattern?: string;
	content_pattern?: string;
	command_pattern?: string;
	enabled?: boolean;
}

export interface DebugFrameDTO {
	frame_id: string;
	session_id: string;
	breakpoint_id: string;
	tool_name: string;
	tool_input: Record<string, unknown>;
	captured_at: number;
	context_snapshot: Record<string, unknown>;
}

export type ResumeAction = "continue" | "skip" | "modify";

export interface AgentDebuggerAPI {
	attachDebugger: (sessionId: string) => Promise<{ ok: boolean }>;
	detachDebugger: (sessionId: string) => Promise<{ ok: boolean }>;
	listBreakpoints: (
		sessionId: string,
	) => Promise<{ breakpoints: BreakpointSpec[] }>;
	setBreakpoint: (
		sessionId: string,
		breakpoint: BreakpointSpec,
	) => Promise<{ ok: boolean; breakpoint_id: string }>;
	removeBreakpoint: (
		sessionId: string,
		id: string,
	) => Promise<{ ok: boolean }>;
	listDebugFrames: (
		sessionId: string,
	) => Promise<{ frames: DebugFrameDTO[] }>;
	resumeFrame: (
		sessionId: string,
		frameId: string,
		action: ResumeAction,
		options?: {
			toolInput?: Record<string, unknown>;
			reason?: string;
		},
	) => Promise<{ ok: boolean }>;
}

export const createAgentDebuggerAPI = (): AgentDebuggerAPI => ({
	attachDebugger: (sessionId) =>
		invokeIpc("agentDebugger:attach", { sessionId }),
	detachDebugger: (sessionId) =>
		invokeIpc("agentDebugger:detach", { sessionId }),
	listBreakpoints: (sessionId) =>
		invokeIpc("agentDebugger:listBreakpoints", { sessionId }),
	setBreakpoint: (sessionId, breakpoint) =>
		invokeIpc("agentDebugger:setBreakpoint", { sessionId, breakpoint }),
	removeBreakpoint: (sessionId, id) =>
		invokeIpc("agentDebugger:removeBreakpoint", { sessionId, id }),
	listDebugFrames: (sessionId) =>
		invokeIpc("agentDebugger:listFrames", { sessionId }),
	resumeFrame: (sessionId, frameId, action, options) =>
		invokeIpc("agentDebugger:resume", {
			sessionId,
			frameId,
			action,
			toolInput: options?.toolInput,
			reason: options?.reason,
		}),
});
