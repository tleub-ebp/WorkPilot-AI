/**
 * Preload bridge for the 12 Phase 3-5 backend feature modules.
 *
 * Each method is a thin wrapper around `ipcRenderer.invoke` that returns
 * the BackendResult shape exposed by the backend FastAPI routers.
 *
 * Bundling these in one file keeps the preload index clean — adding a
 * new feature is one line in `Phase35FeaturesAPI` + one wrapper here,
 * not yet another module file.
 */

import { ipcRenderer } from "electron";
import { IPC_CHANNELS } from "../../../shared/constants";
import type { LongevityScoreResult } from "../../../shared/types/longevity";

// ---------------------------------------------------------------------------
// Generic shape for backend success/error responses

export type Phase35Result<T> = ({ success: true } & T) | { success: false; error: string };

// ---------------------------------------------------------------------------
// Per-feature input/output types (mirroring the Python dataclasses)

// #3.11 Agent Health
export interface AgentRunInput {
	agent_name: string;
	success?: boolean;
	duration_s?: number;
	retries?: number;
	error?: string;
}
export interface AgentHealthScoreData {
	agent_name: string;
	score: number;
	status: "healthy" | "degraded" | "failing" | "burned_out";
	success_rate: number;
	error_rate: number;
	retry_rate: number;
	slowness_ratio: number;
	trend: "improving" | "stable" | "degrading";
	runs_in_window: number;
	actions: string[];
	diagnostics: Record<string, number>;
}

// #3.1 Model Routing
export interface ModelChoice {
	provider: string;
	model: string;
	task_class: string;
	tier: "budget" | "balanced" | "premium";
	estimated_cost_usd: number;
	reason: string;
}
export interface RouteRequest {
	prompt?: string;
	hint?: string;
	tier?: "budget" | "balanced" | "premium";
	expected_output_tokens?: number;
	available?: string[];
}

// #3.6 Domain Agents
export interface DomainSummary {
	tag: string;
	label: string;
	description: string;
}
export interface DomainProfile extends DomainSummary {
	guardrails: string[];
	required_skills: string[];
	forbidden_patterns: string[];
	validation_rules: string[];
	suggested_libraries: string[];
}
export interface DomainAgentBundle {
	domain: string;
	role: string;
	profile: DomainProfile;
	prompt_addendum: string;
	required_skills: string[];
	guardrails: string[];
	forbidden_patterns: string[];
	validation_rules: string[];
}

// #3.4 CI/CD Anomaly
export interface AnomalySignal {
	kind: string;
	severity: "critical" | "high" | "medium" | "low";
	matching_line: string;
	line_number: number;
	suggested_fix: string;
	log_label: string;
}
export interface AnomalyReport {
	signals: AnomalySignal[];
	recurring_kinds: string[];
	summary: { samples: number; total_signals: number; by_kind: Record<string, number>; by_severity: Record<string, number> };
	fix_recommendations: string[];
	has_critical: boolean;
}

// #3.7 License Governance
export interface LicenseScanReport {
	dependencies: Array<{
		name: string;
		version: string;
		ecosystem: string;
		declared_license: string | null;
		is_direct: boolean;
	}>;
	conflicts: Array<{
		dependency: { name: string; version: string; ecosystem: string };
		category: string;
		reason: string;
		remediation: string;
	}>;
	by_category: Record<string, number>;
	summary: Record<string, unknown>;
	passed: boolean;
}

// #3.9 Architecture Drift
export interface ArchitectureScanReport {
	status: string;
	violations: unknown[];
	warnings: unknown[];
	violation_count: number;
	warning_count: number;
	summary: string;
	[k: string]: unknown;
}
export interface DriftReport {
	has_baseline: boolean;
	severity: "none" | "low" | "medium" | "high" | "critical";
	new_violations: unknown[];
	resolved_violations: unknown[];
	persistent_violations: unknown[];
	summary: Record<string, number | string>;
}

// #3.10 Generational Tests
export interface RegressionReport {
	baseline_label: string;
	current_captured_at: number;
	items: Array<{
		test_id: string;
		kind: string;
		baseline_status: string | null;
		current_status: string | null;
		baseline_duration: number | null;
		current_duration: number | null;
		detail: string;
	}>;
	summary: Record<string, number>;
	regression_count: number;
}

// #3.12 i18n Scaler
export type I18nDict = Record<string, unknown>;
export interface LocaleDiffData {
	source_locale: string;
	target_locale: string;
	missing_keys: string[];
	obsolete_keys: string[];
	placeholder_mismatches: string[];
	totals: { missing: number; obsolete: number; placeholder_mismatches: number };
}
export interface I18nScalingReport {
	source_locale: string;
	diffs: LocaleDiffData[];
	coverage: Array<{
		locale: string;
		total_keys: number;
		translated_keys: number;
		placeholder_keys: number;
		coverage_ratio: number;
	}>;
}

// #3.2 Cognitive Context
export interface OptimizedContext {
	slices: Array<{
		file_path: string;
		content: string;
		full_size_tokens: number;
		included_tokens: number;
		truncated: boolean;
		relevance: {
			file_path: string;
			score: number;
			keyword_hits: number;
			path_score: number;
			explicit_mention: boolean;
			recency_score: number;
			breakdown: Record<string, number>;
		};
	}>;
	token_budget: number;
	tokens_used: number;
	files_skipped: string[];
	summary: Record<string, unknown>;
}

// #3.3 Audit Trail
export interface AuditEvent {
	sequence: number;
	timestamp: number;
	kind: string;
	actor: string;
	correlation_id: string;
	summary: string;
	payload: Record<string, unknown>;
	prev_hash: string;
	event_hash: string;
}

// #3.5 Pair Programming
export type PairOpKind =
	| "edit"
	| "cursor"
	| "chat"
	| "suggestion"
	| "join"
	| "leave"
	| "role_change";
export interface PairOperation {
	op_id: string;
	sequence: number;
	kind: PairOpKind;
	actor: string;
	timestamp: number;
	payload: Record<string, unknown>;
}
export interface PairRoomSnapshot {
	room_id: string;
	created_at: number;
	participants: Array<{
		user_id: string;
		display_name: string;
		role: "driver" | "navigator" | "ai";
		joined_at: number;
		last_seen: number;
	}>;
	op_count: number;
	last_op_sequence: number;
	closed: boolean;
}

// ---------------------------------------------------------------------------
// API surface

export interface Phase35FeaturesAPI {
	// #3.8 Longevity
	scoreLongevity: (projectPath: string) => Promise<LongevityScoreResult>;

	// #3.11 Agent Health
	recordAgentRun: (run: AgentRunInput) => Promise<Phase35Result<{}>>;
	recordAgentRunBatch: (runs: AgentRunInput[]) => Promise<Phase35Result<{ recorded: number }>>;
	scoreAgentHealth: (
		agentName: string,
	) => Promise<Phase35Result<{ score: AgentHealthScoreData | null; reason?: string }>>;
	scoreAllAgentHealth: () => Promise<
		Phase35Result<{ scores: AgentHealthScoreData[]; agents_known: string[] }>
	>;
	resetAgentHealth: (agentName?: string) => Promise<Phase35Result<{}>>;

	// #3.1 Model Router
	routeModel: (req: RouteRequest) => Promise<Phase35Result<{ choice: ModelChoice }>>;
	compareModels: (
		req: RouteRequest,
	) => Promise<Phase35Result<{ by_tier: Record<string, ModelChoice> }>>;

	// #3.6 Domain Agents
	listDomains: () => Promise<Phase35Result<{ domains: DomainSummary[] }>>;
	getDomainProfile: (domain: string) => Promise<Phase35Result<{ profile: DomainProfile }>>;
	buildDomainBundle: (
		domain: string,
		role: string,
	) => Promise<Phase35Result<{ bundle: DomainAgentBundle }>>;

	// #3.4 CI/CD Anomaly
	scanCicdLog: (
		log: string,
		label?: string,
	) => Promise<Phase35Result<{ signal_count: number; signals: AnomalySignal[] }>>;
	analyseCicdLogs: (
		samples: { label: string; text: string }[],
	) => Promise<Phase35Result<{ report: AnomalyReport }>>;

	// #3.7 License Governance
	scanLicenses: (
		projectPath: string,
		policy?: "permissive_only" | "open_source_friendly" | "saas_safe",
		licenseOverrides?: { name: string; license: string | null }[],
	) => Promise<Phase35Result<{ report: LicenseScanReport }>>;
	classifyLicense: (
		license: string,
	) => Promise<
		Phase35Result<{ license: string; category: string; is_permissive: boolean }>
	>;

	// #3.9 Architecture Drift
	scanArchitecture: (
		projectPath: string,
	) => Promise<Phase35Result<{ config_source: string; report: ArchitectureScanReport }>>;
	saveArchBaseline: (
		projectPath: string,
	) => Promise<Phase35Result<{ baseline_path: string; violation_count: number }>>;
	compareArchDrift: (
		projectPath: string,
	) => Promise<Phase35Result<{ drift: DriftReport }>>;

	// #3.10 Generational Tests
	listGenerations: (
		projectPath: string,
	) => Promise<Phase35Result<{ generations: string[] }>>;
	captureGeneration: (
		projectPath: string,
		label: string,
		junitXml: string,
	) => Promise<Phase35Result<{ label: string; outcome_count: number; passing_count: number }>>;
	compareGeneration: (
		projectPath: string,
		baselineLabel: string,
		currentJunitXml: string,
	) => Promise<Phase35Result<{ report: RegressionReport }>>;
	deleteGeneration: (
		projectPath: string,
		label: string,
	) => Promise<Phase35Result<{ deleted: boolean }>>;

	// #3.12 i18n Scaler
	diffI18n: (
		source: I18nDict,
		target: I18nDict,
		sourceLocale?: string,
		targetLocale?: string,
	) => Promise<Phase35Result<{ diff: LocaleDiffData }>>;
	skeletonI18n: (
		source: I18nDict,
		targetLocale: string,
		existingTarget?: I18nDict,
		strategy?: string,
	) => Promise<Phase35Result<{ skeleton: I18nDict }>>;
	reportI18nFromDir: (
		localesDir: string,
		sourceLocale?: string,
		strategy?: string,
	) => Promise<Phase35Result<{ report: I18nScalingReport }>>;

	// #3.2 Cognitive Context
	optimizeContext: (
		prompt: string,
		candidateFiles: string[],
		tokenBudget: number,
		opts?: { projectDir?: string; explicitMentions?: string[]; recentFiles?: string[] },
	) => Promise<Phase35Result<{ context: OptimizedContext }>>;

	// #3.3 Audit Trail
	auditAppend: (input: {
		storageDir: string;
		trailName?: string;
		kind: string;
		actor: string;
		correlationId: string;
		summary?: string;
		payload?: Record<string, unknown>;
	}) => Promise<Phase35Result<{ event: AuditEvent }>>;
	auditAppendDecision: (input: {
		storageDir: string;
		trailName?: string;
		actor: string;
		correlationId: string;
		decisionId: string;
		title: string;
		chosenOption: string;
		rejectedOptions?: string[];
		rationale?: string;
		riskScore?: number;
	}) => Promise<Phase35Result<{ event: AuditEvent }>>;
	auditEvents: (input: {
		storageDir: string;
		trailName?: string;
		actor?: string;
		kind?: string;
		since?: number;
		until?: number;
	}) => Promise<Phase35Result<{ events: AuditEvent[]; count: number }>>;
	auditReplay: (
		correlationId: string,
		storageDir: string,
		trailName?: string,
	) => Promise<
		Phase35Result<{
			bundle: { correlation_id: string; events: AuditEvent[]; event_count: number };
		}>
	>;
	auditVerify: (
		storageDir: string,
		trailName?: string,
	) => Promise<
		Phase35Result<{
			integrity: {
				is_intact: boolean;
				events_checked: number;
				first_broken_sequence: number | null;
				breakage_reason: string | null;
			};
		}>
	>;
	auditListTrails: (
		storageDir: string,
	) => Promise<Phase35Result<{ trails: string[] }>>;

	// #3.5 Pair Realtime
	createPairRoom: (
		roomId: string,
	) => Promise<Phase35Result<{ room: PairRoomSnapshot }>>;
	listPairRooms: () => Promise<Phase35Result<{ rooms: string[] }>>;
	getPairRoom: (
		roomId: string,
	) => Promise<Phase35Result<{ room: PairRoomSnapshot }>>;
	closePairRoom: (
		roomId: string,
	) => Promise<Phase35Result<{ closed: boolean }>>;
	pairJoin: (
		roomId: string,
		userId: string,
		displayName: string,
		role?: "driver" | "navigator" | "ai",
	) => Promise<Phase35Result<{ op: PairOperation }>>;
	pairLeave: (
		roomId: string,
		userId: string,
	) => Promise<Phase35Result<{ op: PairOperation | null }>>;
	pairChat: (
		roomId: string,
		actor: string,
		text: string,
	) => Promise<Phase35Result<{ op: PairOperation }>>;
	pairCursor: (
		roomId: string,
		actor: string,
		filePath: string,
		line: number,
		column: number,
	) => Promise<Phase35Result<{ op: PairOperation }>>;
	pairEdit: (
		roomId: string,
		actor: string,
		filePath: string,
		startLine: number,
		endLine: number,
		newText: string,
	) => Promise<Phase35Result<{ op: PairOperation }>>;
	pairSuggestion: (
		roomId: string,
		actor: string,
		filePath: string,
		suggestion: string,
		rationale?: string,
	) => Promise<Phase35Result<{ op: PairOperation }>>;
	pairOps: (
		roomId: string,
		sinceSequence?: number,
	) => Promise<Phase35Result<{ ops: PairOperation[]; count: number }>>;
	subscribePairRoom: (
		roomId: string,
		sinceSequence?: number,
	) => Promise<Phase35Result<{ subscriptionId: string }>>;
	unsubscribePairRoom: (
		subscriptionId: string,
	) => Promise<Phase35Result<{ closed: boolean }>>;
	onPairOpEvent: (
		callback: (data: { subscriptionId: string; op: PairOperation }) => void,
	) => () => void;
	onPairStreamError: (
		callback: (data: { subscriptionId: string; error: string }) => void,
	) => () => void;
}

export const createPhase35FeaturesAPI = (): Phase35FeaturesAPI => ({
	// #3.8
	scoreLongevity: (projectPath) =>
		ipcRenderer.invoke(IPC_CHANNELS.LONGEVITY_SCORE, { projectPath }),

	// #3.11
	recordAgentRun: (run) =>
		ipcRenderer.invoke(IPC_CHANNELS.AGENT_HEALTH_RECORD, run),
	recordAgentRunBatch: (runs) =>
		ipcRenderer.invoke(IPC_CHANNELS.AGENT_HEALTH_RECORD_BATCH, { runs }),
	scoreAgentHealth: (agentName) =>
		ipcRenderer.invoke(IPC_CHANNELS.AGENT_HEALTH_SCORE, { agentName }),
	scoreAllAgentHealth: () => ipcRenderer.invoke(IPC_CHANNELS.AGENT_HEALTH_SCORES),
	resetAgentHealth: (agentName) =>
		ipcRenderer.invoke(IPC_CHANNELS.AGENT_HEALTH_RESET, { agentName }),

	// #3.1
	routeModel: (req) => ipcRenderer.invoke(IPC_CHANNELS.MODEL_ROUTER_ROUTE, req),
	compareModels: (req) => ipcRenderer.invoke(IPC_CHANNELS.MODEL_ROUTER_COMPARE, req),

	// #3.6
	listDomains: () => ipcRenderer.invoke(IPC_CHANNELS.DOMAIN_AGENTS_LIST),
	getDomainProfile: (domain) =>
		ipcRenderer.invoke(IPC_CHANNELS.DOMAIN_AGENTS_PROFILE, { domain }),
	buildDomainBundle: (domain, role) =>
		ipcRenderer.invoke(IPC_CHANNELS.DOMAIN_AGENTS_BUILD, { domain, role }),

	// #3.4
	scanCicdLog: (log, label) =>
		ipcRenderer.invoke(IPC_CHANNELS.CICD_ANOMALY_SCAN, { log, label }),
	analyseCicdLogs: (samples) =>
		ipcRenderer.invoke(IPC_CHANNELS.CICD_ANOMALY_ANALYSE, { samples }),

	// #3.7
	scanLicenses: (projectPath, policy, licenseOverrides) =>
		ipcRenderer.invoke(IPC_CHANNELS.LICENSE_GOV_SCAN, {
			projectPath,
			policy,
			licenseOverrides,
		}),
	classifyLicense: (license) =>
		ipcRenderer.invoke(IPC_CHANNELS.LICENSE_GOV_CLASSIFY, { license }),

	// #3.9
	scanArchitecture: (projectPath) =>
		ipcRenderer.invoke(IPC_CHANNELS.ARCH_DRIFT_SCAN, { projectPath }),
	saveArchBaseline: (projectPath) =>
		ipcRenderer.invoke(IPC_CHANNELS.ARCH_DRIFT_SAVE_BASELINE, { projectPath }),
	compareArchDrift: (projectPath) =>
		ipcRenderer.invoke(IPC_CHANNELS.ARCH_DRIFT_COMPARE, { projectPath }),

	// #3.10
	listGenerations: (projectPath) =>
		ipcRenderer.invoke(IPC_CHANNELS.GEN_TESTS_LIST, { projectPath }),
	captureGeneration: (projectPath, label, junitXml) =>
		ipcRenderer.invoke(IPC_CHANNELS.GEN_TESTS_CAPTURE, {
			projectPath,
			label,
			junitXml,
		}),
	compareGeneration: (projectPath, baselineLabel, currentJunitXml) =>
		ipcRenderer.invoke(IPC_CHANNELS.GEN_TESTS_COMPARE, {
			projectPath,
			baselineLabel,
			currentJunitXml,
		}),
	deleteGeneration: (projectPath, label) =>
		ipcRenderer.invoke(IPC_CHANNELS.GEN_TESTS_DELETE, { projectPath, label }),

	// #3.12
	diffI18n: (source, target, sourceLocale, targetLocale) =>
		ipcRenderer.invoke(IPC_CHANNELS.I18N_SCALER_DIFF, {
			source,
			target,
			sourceLocale,
			targetLocale,
		}),
	skeletonI18n: (source, targetLocale, existingTarget, strategy) =>
		ipcRenderer.invoke(IPC_CHANNELS.I18N_SCALER_SKELETON, {
			source,
			targetLocale,
			existingTarget,
			strategy,
		}),
	reportI18nFromDir: (localesDir, sourceLocale, strategy) =>
		ipcRenderer.invoke(IPC_CHANNELS.I18N_SCALER_REPORT_FROM_DIR, {
			localesDir,
			sourceLocale,
			strategy,
		}),

	// #3.2
	optimizeContext: (prompt, candidateFiles, tokenBudget, opts) =>
		ipcRenderer.invoke(IPC_CHANNELS.COGNITIVE_CONTEXT_OPTIMIZE, {
			prompt,
			candidateFiles,
			tokenBudget,
			...opts,
		}),

	// #3.3
	auditAppend: (input) => ipcRenderer.invoke(IPC_CHANNELS.AUDIT_TRAIL_APPEND, input),
	auditAppendDecision: (input) =>
		ipcRenderer.invoke(IPC_CHANNELS.AUDIT_TRAIL_APPEND_DECISION, input),
	auditEvents: (input) => ipcRenderer.invoke(IPC_CHANNELS.AUDIT_TRAIL_EVENTS, input),
	auditReplay: (correlationId, storageDir, trailName) =>
		ipcRenderer.invoke(IPC_CHANNELS.AUDIT_TRAIL_REPLAY, {
			correlationId,
			storageDir,
			trailName,
		}),
	auditVerify: (storageDir, trailName) =>
		ipcRenderer.invoke(IPC_CHANNELS.AUDIT_TRAIL_VERIFY, { storageDir, trailName }),
	auditListTrails: (storageDir) =>
		ipcRenderer.invoke(IPC_CHANNELS.AUDIT_TRAIL_LIST, { storageDir }),

	// #3.5
	createPairRoom: (roomId) =>
		ipcRenderer.invoke(IPC_CHANNELS.PAIR_RT_CREATE_ROOM, { roomId }),
	listPairRooms: () => ipcRenderer.invoke(IPC_CHANNELS.PAIR_RT_LIST_ROOMS),
	getPairRoom: (roomId) =>
		ipcRenderer.invoke(IPC_CHANNELS.PAIR_RT_GET_ROOM, { roomId }),
	closePairRoom: (roomId) =>
		ipcRenderer.invoke(IPC_CHANNELS.PAIR_RT_CLOSE_ROOM, { roomId }),
	pairJoin: (roomId, userId, displayName, role) =>
		ipcRenderer.invoke(IPC_CHANNELS.PAIR_RT_JOIN, {
			roomId,
			userId,
			displayName,
			role,
		}),
	pairLeave: (roomId, userId) =>
		ipcRenderer.invoke(IPC_CHANNELS.PAIR_RT_LEAVE, { roomId, userId }),
	pairChat: (roomId, actor, text) =>
		ipcRenderer.invoke(IPC_CHANNELS.PAIR_RT_CHAT, { roomId, actor, text }),
	pairCursor: (roomId, actor, filePath, line, column) =>
		ipcRenderer.invoke(IPC_CHANNELS.PAIR_RT_CURSOR, {
			roomId,
			actor,
			filePath,
			line,
			column,
		}),
	pairEdit: (roomId, actor, filePath, startLine, endLine, newText) =>
		ipcRenderer.invoke(IPC_CHANNELS.PAIR_RT_EDIT, {
			roomId,
			actor,
			filePath,
			startLine,
			endLine,
			newText,
		}),
	pairSuggestion: (roomId, actor, filePath, suggestion, rationale) =>
		ipcRenderer.invoke(IPC_CHANNELS.PAIR_RT_SUGGESTION, {
			roomId,
			actor,
			filePath,
			suggestion,
			rationale,
		}),
	pairOps: (roomId, sinceSequence) =>
		ipcRenderer.invoke(IPC_CHANNELS.PAIR_RT_OPS, { roomId, sinceSequence }),
	subscribePairRoom: (roomId, sinceSequence) =>
		ipcRenderer.invoke(IPC_CHANNELS.PAIR_RT_SUBSCRIBE, { roomId, sinceSequence }),
	unsubscribePairRoom: (subscriptionId) =>
		ipcRenderer.invoke(IPC_CHANNELS.PAIR_RT_UNSUBSCRIBE, { subscriptionId }),
	onPairOpEvent: (callback) => {
		const listener = (
			_event: unknown,
			data: { subscriptionId: string; op: PairOperation },
		) => callback(data);
		ipcRenderer.on(IPC_CHANNELS.PAIR_RT_OP_EVENT, listener);
		return () => ipcRenderer.removeListener(IPC_CHANNELS.PAIR_RT_OP_EVENT, listener);
	},
	onPairStreamError: (callback) => {
		const listener = (
			_event: unknown,
			data: { subscriptionId: string; error: string },
		) => callback(data);
		ipcRenderer.on(IPC_CHANNELS.PAIR_RT_STREAM_ERROR, listener);
		return () => ipcRenderer.removeListener(IPC_CHANNELS.PAIR_RT_STREAM_ERROR, listener);
	},
});
