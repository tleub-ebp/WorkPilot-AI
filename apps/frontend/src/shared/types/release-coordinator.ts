/**
 * Release Train Coordinator — Types for multi-service releases.
 */

export type BumpType = "major" | "minor" | "patch" | "none";

export type ReleaseStatus =
	| "planning"
	| "staging"
	| "gate_check"
	| "releasing"
	| "released"
	| "rolled_back"
	| "failed";

export type GateStatus = "passed" | "failed" | "pending" | "skipped";

export interface SemVer {
	major: number;
	minor: number;
	patch: number;
	prerelease: string;
}

export interface ServiceRelease {
	name: string;
	currentVersion: SemVer;
	nextVersion: SemVer;
	bumpType: BumpType;
	changelogEntries: string[];
	dependencies: string[];
	gates: Record<string, GateStatus>;
}

export interface GateCheck {
	name: string;
	status: GateStatus;
	message: string;
}

export interface ReleaseTrainPlan {
	id: string;
	services: ServiceRelease[];
	status: ReleaseStatus;
	gates: GateCheck[];
	allGatesPassed: boolean;
	summary: string;
	createdAt: string;
}
