import { create } from "zustand";
import type { BlastRadiusReport } from "../../preload/api/modules/blast-radius-api";

interface BlastRadiusState {
	report: BlastRadiusReport | null;
	loading: boolean;
	error: string | null;
	analyze: (projectRoot: string, targets: string[]) => Promise<void>;
	clear: () => void;
}

export const useBlastRadiusStore = create<BlastRadiusState>((set) => ({
	report: null,
	loading: false,
	error: null,
	analyze: async (projectRoot, targets) => {
		set({ loading: true, error: null });
		try {
			const report = await window.electronAPI.analyzeBlastRadius(
				projectRoot,
				targets,
			);
			set({ report });
		} catch (e) {
			set({ error: (e as Error).message });
		} finally {
			set({ loading: false });
		}
	},
	clear: () => set({ report: null, error: null }),
}));
