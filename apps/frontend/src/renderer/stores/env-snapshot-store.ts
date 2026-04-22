import { create } from "zustand";
import type {
	EnvSnapshot,
	EnvSnapshotFormat,
} from "../../preload/api/modules/env-snapshot-api";

interface EnvSnapshotState {
	snapshots: EnvSnapshot[];
	selectedId: string | null;
	capturing: boolean;
	exporting: boolean;
	replayPayload: { snapId: string; format: EnvSnapshotFormat; payload: string } | null;
	lastExportedPath: string | null;
	error: string | null;

	load: (projectPath: string) => Promise<void>;
	capture: (
		projectPath: string,
		opts?: { label?: string; specId?: string },
	) => Promise<void>;
	select: (id: string | null) => void;
	replay: (
		projectPath: string,
		snapId: string,
		format: EnvSnapshotFormat,
	) => Promise<void>;
	exportSnapshot: (
		projectPath: string,
		snapId: string,
		format: EnvSnapshotFormat,
	) => Promise<void>;
	clearReplay: () => void;
}

export const useEnvSnapshotStore = create<EnvSnapshotState>((set, get) => ({
	snapshots: [],
	selectedId: null,
	capturing: false,
	exporting: false,
	replayPayload: null,
	lastExportedPath: null,
	error: null,

	load: async (projectPath) => {
		set({ error: null });
		try {
			const { snapshots } = await globalThis.electronAPI.listEnvSnapshots(
				projectPath,
			);
			set({ snapshots });
		} catch (e) {
			set({ error: String(e) });
		}
	},

	capture: async (projectPath, opts) => {
		set({ capturing: true, error: null });
		try {
			const { snapshot } = await globalThis.electronAPI.captureEnvSnapshot({
				projectPath,
				specId: opts?.specId,
				label: opts?.label,
			});
			set((s) => ({
				snapshots: [snapshot, ...s.snapshots],
				selectedId: snapshot.id,
				capturing: false,
			}));
		} catch (e) {
			set({ error: String(e), capturing: false });
		}
	},

	select: (id) => set({ selectedId: id, replayPayload: null, lastExportedPath: null }),

	replay: async (projectPath, snapId, format) => {
		set({ error: null });
		try {
			const res = await globalThis.electronAPI.replayEnvSnapshot(
				projectPath,
				snapId,
				format,
			);
			set({ replayPayload: { snapId, format: res.format, payload: res.payload } });
		} catch (e) {
			set({ error: String(e) });
		}
	},

	exportSnapshot: async (projectPath, snapId, format) => {
		set({ exporting: true, error: null });
		try {
			const { path: exported } = await globalThis.electronAPI.exportEnvSnapshot(
				projectPath,
				snapId,
				format,
			);
			set({ lastExportedPath: exported, exporting: false });
		} catch (e) {
			set({ error: String(e), exporting: false });
		}
	},

	clearReplay: () => {
		get();
		set({ replayPayload: null, lastExportedPath: null });
	},
}));
