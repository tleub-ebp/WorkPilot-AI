import { create } from "zustand";
import type { PredictionReport } from "../../preload/api/modules/cost-predictor-api";

interface CostPredictorState {
	report: PredictionReport | null;
	loading: boolean;
	error: string | null;
	provider: string;
	model: string;
	compare: string;
	thinking: boolean;

	setProvider: (v: string) => void;
	setModel: (v: string) => void;
	setCompare: (v: string) => void;
	setThinking: (v: boolean) => void;
	run: (projectPath: string, specId: string) => Promise<void>;
	reset: () => void;
}

export const useCostPredictorStore = create<CostPredictorState>((set, get) => ({
	report: null,
	loading: false,
	error: null,
	provider: "anthropic",
	model: "claude-sonnet-4-6",
	compare: "anthropic:claude-haiku-4-5-20251001",
	thinking: true,

	setProvider: (provider) => set({ provider }),
	setModel: (model) => set({ model }),
	setCompare: (compare) => set({ compare }),
	setThinking: (thinking) => set({ thinking }),

	run: async (projectPath, specId) => {
		set({ loading: true, error: null });
		try {
			const { provider, model, compare, thinking } = get();
			const { report } = await globalThis.electronAPI.runCostPrediction({
				projectPath,
				specId,
				provider,
				model,
				compare: compare || undefined,
				thinking,
			});
			set({ report, loading: false });
		} catch (e) {
			set({ error: String(e), loading: false });
		}
	},

	reset: () => set({ report: null, error: null, loading: false }),
}));
