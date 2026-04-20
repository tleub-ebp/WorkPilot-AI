import { create } from "zustand";
import { persist } from "zustand/middleware";
import type {
	TeamBotConfig,
	TeamBotNotification,
} from "../../preload/api/modules/team-bot-api";

interface TeamBotState {
	config: TeamBotConfig;
	testing: boolean;
	lastResult: "ok" | "error" | null;
	lastError: string | null;
	setConfig: (patch: Partial<TeamBotConfig>) => void;
	sendTest: () => Promise<void>;
	notify: (payload: TeamBotNotification) => Promise<boolean>;
}

const DEFAULT_CONFIG: TeamBotConfig = {
	kind: "slack",
	webhook_url: "",
	enabled: false,
	tags: [],
};

export const useTeamBotStore = create<TeamBotState>()(
	persist(
		(set, get) => ({
			config: DEFAULT_CONFIG,
			testing: false,
			lastResult: null,
			lastError: null,

			setConfig: (patch) =>
				set((s) => ({ config: { ...s.config, ...patch } })),

			sendTest: async () => {
				set({ testing: true, lastResult: null, lastError: null });
				try {
					const { ok } = await window.electronAPI.teamBotTest(get().config);
					set({ lastResult: ok ? "ok" : "error" });
				} catch (e) {
					set({ lastResult: "error", lastError: (e as Error).message });
				} finally {
					set({ testing: false });
				}
			},

			notify: async (payload) => {
				try {
					const { ok } = await window.electronAPI.teamBotSend(
						get().config,
						payload,
					);
					return ok;
				} catch {
					return false;
				}
			},
		}),
		{ name: "workpilot-team-bot" },
	),
);
