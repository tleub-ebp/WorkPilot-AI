/**
 * Agent Time Travel types — Temporal debugger for AI agents.
 *
 * Provider-agnostic: works with any LLM (Anthropic, OpenAI, Google, Ollama, etc.)
 */

// ---------------------------------------------------------------------------
// Checkpoint
// ---------------------------------------------------------------------------

export type CheckpointType =
	| "auto_decision"
	| "auto_file_change"
	| "auto_tool_call"
	| "manual";

export interface Checkpoint {
	id: string;
	session_id: string;
	step_index: number;
	step_id: string;
	checkpoint_type: CheckpointType;
	label: string;
	description: string;
	created_at: number;
	/** Provider-agnostic conversation history up to this point */
	conversation_history: ConversationMessage[];
	/** File path -> content at this checkpoint */
	file_snapshots: Record<string, string>;
	tokens_at_checkpoint: number;
	cost_at_checkpoint: number;
}

export interface ConversationMessage {
	role: "system" | "assistant" | "assistant_thinking" | "tool" | "user";
	content: string;
	step_type?: string;
	step_index?: number;
	tool_call?: {
		name: string;
		input: Record<string, unknown>;
	};
	tool_name?: string;
	decision?: {
		options: string[];
		chosen: string;
		reasoning: string;
	};
	file_changes?: Array<{
		file_path: string;
		operation: string;
		before_content?: string | null;
		after_content?: string | null;
	}>;
	tokens?: {
		input: number;
		output: number;
	};
}

// ---------------------------------------------------------------------------
// Fork & Re-execute
// ---------------------------------------------------------------------------

export interface ForkRequest {
	checkpoint_id: string;
	session_id: string;
	modified_prompt: string;
	additional_instructions: string;
	/** Target LLM provider (anthropic, openai, google, ollama, etc.) */
	fork_provider: string;
	/** Target model name (e.g. claude-sonnet-4-5-20250514, gpt-4o, gemini-2.0-flash) */
	fork_model: string;
	/** API key for the provider (optional, uses app settings if empty) */
	fork_api_key: string;
	/** Custom base URL (for ollama, custom endpoints) */
	fork_base_url: string;
}

export type ForkStatus = "pending" | "running" | "completed" | "failed";

export interface ForkSession {
	fork_id: string;
	original_session_id: string;
	checkpoint_id: string;
	fork_request: ForkRequest;
	forked_session_id: string;
	created_at: number;
	status: ForkStatus;
}

/**
 * Provider-agnostic context payload for re-executing a fork.
 * Can be consumed by any LLM client.
 */
export interface ForkContext {
	fork_id: string;
	original_session_id: string;
	forked_session_id: string;
	checkpoint_step_index: number;
	conversation_history: ConversationMessage[];
	file_snapshots: Record<string, string>;
	modified_prompt: string;
	additional_instructions: string;
	provider: string;
	model: string;
	api_key: string;
	base_url: string;
}

// ---------------------------------------------------------------------------
// Decision Scoring
// ---------------------------------------------------------------------------

export interface DecisionScore {
	step_id: string;
	step_index: number;
	/** 0.0 (low confidence) to 1.0 (high confidence) */
	confidence_score: number;
	/** 0.0 (low impact) to 1.0 (high impact) */
	impact_score: number;
	factors: string[];
	is_critical: boolean;
}

export interface DecisionHeatmapFileEntry {
	file_path: string;
	impact_score: number;
	intensity: number;
}

export interface DecisionHeatmap {
	session_id: string;
	decision_count: number;
	critical_decisions: number;
	avg_confidence: number;
	avg_impact: number;
	file_impact: DecisionHeatmapFileEntry[];
	scores: DecisionScore[];
}
