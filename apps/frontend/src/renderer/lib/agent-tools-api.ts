/**
 * Typed client for the three agent-tooling endpoints added with the
 * "Cost Estimator / Restart / Prompt Preview" feature.
 *
 *   POST /api/cost-estimator/preview
 *   GET  /api/restart/plan
 *   POST /api/restart/prepare
 *   GET  /api/prompt-preview/
 *
 * Each call returns `{ ok: true, data: T } | { ok: false, error: string }`
 * so callers don't have to repeat the success/error switch. AbortSignal
 * is supported on every call (for useEffect cleanup).
 */

export type ApiResult<T> =
	| { ok: true; data: T }
	| { ok: false; error: string };

const backendUrl = (): string =>
	(import.meta.env?.VITE_BACKEND_URL as string | undefined) ?? "";

async function _post<T>(
	path: string,
	body: unknown,
	signal?: AbortSignal,
): Promise<ApiResult<T>> {
	try {
		const res = await fetch(`${backendUrl()}${path}`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(body),
			signal,
		});
		const json = (await res.json()) as Record<string, unknown>;
		if (json.success === true) {
			return { ok: true, data: json as T };
		}
		return {
			ok: false,
			error:
				typeof json.error === "string"
					? json.error
					: `request failed with HTTP ${res.status}`,
		};
	} catch (err) {
		if ((err as { name?: string })?.name === "AbortError") {
			return { ok: false, error: "aborted" };
		}
		return {
			ok: false,
			error: err instanceof Error ? err.message : "network error",
		};
	}
}

async function _get<T>(
	path: string,
	params: Record<string, string>,
	signal?: AbortSignal,
): Promise<ApiResult<T>> {
	try {
		const qs = new URLSearchParams(params).toString();
		const res = await fetch(`${backendUrl()}${path}?${qs}`, { signal });
		const json = (await res.json()) as Record<string, unknown>;
		if (json.success === true) {
			return { ok: true, data: json as T };
		}
		return {
			ok: false,
			error:
				typeof json.error === "string"
					? json.error
					: `request failed with HTTP ${res.status}`,
		};
	} catch (err) {
		if ((err as { name?: string })?.name === "AbortError") {
			return { ok: false, error: "aborted" };
		}
		return {
			ok: false,
			error: err instanceof Error ? err.message : "network error",
		};
	}
}

// ---------------------------------------------------------------------------
// Cost Estimator

export interface PhaseEstimate {
	phase: string;
	provider: string;
	model: string;
	input_tokens: number;
	output_tokens: number;
	iterations: number;
	estimated_cost_usd: number;
	notes: string[];
}

export interface CostEstimate {
	spec_id: string;
	spec_chars: number;
	base_input_tokens: number;
	phases: PhaseEstimate[];
	total_cost_usd: number;
	confidence: "high" | "medium" | "low";
	warnings: string[];
}

export async function previewBuildCost(
	specDir: string,
	signal?: AbortSignal,
): Promise<ApiResult<{ estimate: CostEstimate }>> {
	return _post<{ estimate: CostEstimate }>(
		"/api/cost-estimator/preview",
		{ spec_dir: specDir },
		signal,
	);
}

// ---------------------------------------------------------------------------
// Restart Planner

export type RestartMode = "qa" | "coder" | "full";

export interface RestartPlan {
	spec_id: string;
	can_restart_qa: boolean;
	can_restart_coder: boolean;
	can_restart_full: boolean;
	reasons: Record<string, string>;
	next_subtask_for_coder: string | null;
	completed_subtasks: number;
	total_subtasks: number;
	files_to_clean: Record<RestartMode, string[]>;
}

export async function fetchRestartPlan(
	specDir: string,
	signal?: AbortSignal,
): Promise<ApiResult<{ plan: RestartPlan }>> {
	return _get<{ plan: RestartPlan }>(
		"/api/restart/plan",
		{ spec_dir: specDir },
		signal,
	);
}

export interface RestartPrepareResult {
	mode: RestartMode;
	deleted: string[];
	warnings: string[];
}

export async function prepareRestart(
	specDir: string,
	mode: RestartMode,
	signal?: AbortSignal,
): Promise<ApiResult<RestartPrepareResult>> {
	return _post<RestartPrepareResult>(
		"/api/restart/prepare",
		{ spec_dir: specDir, mode },
		signal,
	);
}

// ---------------------------------------------------------------------------
// System Prompt Preview

export interface PromptPreview {
	project_dir: string;
	spec_dir: string;
	agent_type: string;
	model: string;
	provider: string;
	system_prompt: string;
	system_prompt_length: number;
	claude_md_included: boolean;
	domain_addendum_included: boolean;
	domain_addendum_chars: number;
	allowed_tools: string[];
	notes: string[];
}

export async function fetchPromptPreview(
	projectDir: string,
	specDir: string,
	agentType: string = "coder",
	signal?: AbortSignal,
): Promise<ApiResult<{ preview: PromptPreview }>> {
	return _get<{ preview: PromptPreview }>(
		"/api/prompt-preview/",
		{
			project_dir: projectDir,
			spec_dir: specDir,
			agent_type: agentType,
		},
		signal,
	);
}
