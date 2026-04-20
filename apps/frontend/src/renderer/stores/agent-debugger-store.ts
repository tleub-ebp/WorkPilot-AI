import { create } from "zustand";
import type {
	BreakpointSpec,
	DebugFrameDTO,
	ResumeAction,
} from "../../preload/api/modules/agent-debugger-api";

interface AgentDebuggerState {
	sessionId: string | null;
	breakpoints: BreakpointSpec[];
	frames: DebugFrameDTO[];
	loading: boolean;
	error: string | null;

	attach: (sessionId: string) => Promise<void>;
	detach: () => Promise<void>;
	refresh: () => Promise<void>;
	addBreakpoint: (bp: BreakpointSpec) => Promise<void>;
	removeBreakpoint: (id: string) => Promise<void>;
	resume: (
		frameId: string,
		action: ResumeAction,
		options?: { toolInput?: Record<string, unknown>; reason?: string },
	) => Promise<void>;
}

export const useAgentDebuggerStore = create<AgentDebuggerState>((set, get) => ({
	sessionId: null,
	breakpoints: [],
	frames: [],
	loading: false,
	error: null,

	attach: async (sessionId) => {
		set({ loading: true, error: null });
		try {
			await window.electronAPI.attachDebugger(sessionId);
			set({ sessionId });
			await get().refresh();
		} catch (e) {
			set({ error: (e as Error).message });
		} finally {
			set({ loading: false });
		}
	},

	detach: async () => {
		const { sessionId } = get();
		if (!sessionId) return;
		await window.electronAPI.detachDebugger(sessionId);
		set({ sessionId: null, breakpoints: [], frames: [] });
	},

	refresh: async () => {
		const { sessionId } = get();
		if (!sessionId) return;
		const [bp, fr] = await Promise.all([
			window.electronAPI.listBreakpoints(sessionId),
			window.electronAPI.listDebugFrames(sessionId),
		]);
		set({ breakpoints: bp.breakpoints, frames: fr.frames });
	},

	addBreakpoint: async (bp) => {
		const { sessionId } = get();
		if (!sessionId) return;
		await window.electronAPI.setBreakpoint(sessionId, bp);
		await get().refresh();
	},

	removeBreakpoint: async (id) => {
		const { sessionId } = get();
		if (!sessionId) return;
		await window.electronAPI.removeBreakpoint(sessionId, id);
		await get().refresh();
	},

	resume: async (frameId, action, options) => {
		const { sessionId } = get();
		if (!sessionId) return;
		await window.electronAPI.resumeFrame(sessionId, frameId, action, options);
		await get().refresh();
	},
}));
