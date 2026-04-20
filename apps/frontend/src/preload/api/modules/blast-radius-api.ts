/**
 * Blast Radius API — renderer-side bridge.
 *
 * Provider-agnostic: deterministic import-graph scan, no LLM usage.
 */

import { invokeIpc } from "./ipc-utils";

export interface BlastRadiusDependent {
	source: string;
	target: string;
	kind: string;
}

export interface BlastRadiusReport {
	targets: string[];
	dependents: BlastRadiusDependent[];
	tests: string[];
	flags: string[];
	score: "low" | "medium" | "high";
	total_dependents: number;
	explanation: string[];
}

export interface BlastRadiusAPI {
	analyzeBlastRadius: (
		projectRoot: string,
		targets: string[],
	) => Promise<BlastRadiusReport>;
}

export const createBlastRadiusAPI = (): BlastRadiusAPI => ({
	analyzeBlastRadius: (projectRoot, targets) =>
		invokeIpc("blastRadius:analyze", { projectRoot, targets }),
});
