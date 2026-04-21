/**
 * Bounty Board API — renderer-side bridge for competitive multi-agent runs.
 *
 * Provider-agnostic: any combination of (provider, model) registered in the
 * backend provider registry can be submitted as a contestant.
 */

import { invokeIpc } from "./ipc-utils";

export interface BountyContestantInput {
	provider: string;
	model: string;
	profileId?: string;
	promptOverride?: string;
}

export interface BountyContestant {
	id: string;
	label: string;
	provider: string;
	model: string;
	profile_id?: string | null;
	status:
		| "queued"
		| "running"
		| "completed"
		| "error"
		| "archived"
		| "winner";
	worktree_path?: string | null;
	output: string;
	tokens_used: number;
	cost_usd: number;
	duration_ms: number;
	error?: string | null;
	score?: number | null;
	quality_breakdown: Record<string, number>;
	started_at?: number | null;
	completed_at?: number | null;
}

export interface BountyResult {
	id: string;
	specId: string;
	projectPath: string;
	contestants: BountyContestant[];
	winnerId: string | null;
	judgeReport: string;
	judgeRationale: Record<string, string>;
	createdAt: number;
	completedAt: number | null;
	status: "running" | "judging" | "completed" | "error";
}

export interface BountyBoardStartOptions {
	projectPath: string;
	specId: string;
	contestants: BountyContestantInput[];
}

export interface BountyBoardAPI {
	startBounty: (
		options: BountyBoardStartOptions,
	) => Promise<{ result: BountyResult }>;
	listBountyArchives: (options: {
		projectPath: string;
		specId: string;
	}) => Promise<{ archives: BountyResult[] }>;
}

export const createBountyBoardAPI = (): BountyBoardAPI => ({
	startBounty: (options) =>
		invokeIpc<{ result: BountyResult }>("bountyBoard:start", options),
	listBountyArchives: (options) =>
		invokeIpc<{ archives: BountyResult[] }>(
			"bountyBoard:listArchives",
			options,
		),
});
