/**
 * Cross-Agent Consensus Arbiter — Types for inter-agent conflict resolution.
 */

export type AgentDomain =
	| "security"
	| "performance"
	| "qa"
	| "ux"
	| "architecture"
	| "database"
	| "devops"
	| "accessibility"
	| "cost";

export type ConflictSeverity = "low" | "medium" | "high" | "critical";

export type ResolutionStrategy =
	| "highest_confidence"
	| "domain_authority"
	| "majority_vote"
	| "human_escalation"
	| "weighted_merge";

export interface AgentOpinion {
	agentName: string;
	domain: AgentDomain;
	recommendation: string;
	confidence: number;
	reasoning: string;
	affectedFiles: string[];
}

export interface Conflict {
	topic: string;
	opinions: AgentOpinion[];
	severity: ConflictSeverity;
	resolved: boolean;
	resolution: string;
	strategyUsed: ResolutionStrategy | null;
}

export interface ConsensusResult {
	conflicts: Conflict[];
	resolvedCount: number;
	escalatedCount: number;
	consensusSummary: string;
	allResolved: boolean;
}
