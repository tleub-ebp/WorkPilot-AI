/**
 * Team Bot API — renderer-side bridge.
 *
 * Provider-agnostic: posts to Slack/Teams webhooks with structured events
 * sourced from the WorkPilot runtime (no LLM interaction).
 */

import { invokeIpc } from "./ipc-utils";

export type TeamBotKind = "slack" | "teams";
export type TeamBotSeverity = "info" | "warning" | "critical";
export type TeamBotEvent =
	| "agent_started"
	| "agent_finished"
	| "cost_alert"
	| "guardrail_blocked"
	| "blast_radius_high"
	| "custom";

export interface TeamBotConfig {
	kind: TeamBotKind;
	webhook_url: string;
	default_channel?: string;
	enabled?: boolean;
	tags?: string[];
}

export interface TeamBotNotification {
	event: TeamBotEvent;
	title: string;
	summary: string;
	fields?: Record<string, unknown>;
	severity?: TeamBotSeverity;
}

export interface TeamBotAPI {
	teamBotSend: (
		config: TeamBotConfig,
		payload: TeamBotNotification,
	) => Promise<{ ok: boolean }>;
	teamBotTest: (config: TeamBotConfig) => Promise<{ ok: boolean }>;
}

export const createTeamBotAPI = (): TeamBotAPI => ({
	teamBotSend: (config, payload) =>
		invokeIpc("teamBot:send", { config, payload }),
	teamBotTest: (config) => invokeIpc("teamBot:test", { config }),
});
