/**
 * Consensus Arbiter API
 *
 * Renderer-side bridge to the consensus arbiter runner which detects and
 * resolves inter-agent conflicts from persisted opinion payloads.
 */

import type { ConsensusResult } from "../../../shared/types/consensus-arbiter";
import { createIpcListener, invokeIpc } from "./ipc-utils";

export interface ConsensusArbiterRunOptions {
	projectPath: string;
}

export interface ConsensusArbiterScanResult {
	result: ConsensusResult;
}

export interface ConsensusArbiterEvent {
	type: "start" | "progress" | "complete";
	data: { status?: string; results?: number };
}

export interface ConsensusArbiterAPI {
	runConsensusArbiterScan: (
		options: ConsensusArbiterRunOptions,
	) => Promise<ConsensusArbiterScanResult>;
	cancelConsensusArbiterScan: () => Promise<boolean>;
	onConsensusArbiterEvent: (
		callback: (event: ConsensusArbiterEvent) => void,
	) => () => void;
	onConsensusArbiterResult: (
		callback: (result: ConsensusArbiterScanResult) => void,
	) => () => void;
	onConsensusArbiterError: (
		callback: (error: string) => void,
	) => () => void;
}

export const createConsensusArbiterAPI = (): ConsensusArbiterAPI => ({
	runConsensusArbiterScan: (options: ConsensusArbiterRunOptions) =>
		invokeIpc<ConsensusArbiterScanResult>("consensusArbiter:run", options),

	cancelConsensusArbiterScan: () =>
		invokeIpc<boolean>("consensusArbiter:cancel"),

	onConsensusArbiterEvent: (callback) =>
		createIpcListener<[ConsensusArbiterEvent]>(
			"consensus-arbiter-event",
			(payload) => callback(payload),
		),

	onConsensusArbiterResult: (callback) =>
		createIpcListener<[ConsensusArbiterScanResult]>(
			"consensus-arbiter-result",
			(payload) => callback(payload),
		),

	onConsensusArbiterError: (callback) =>
		createIpcListener<[string]>("consensus-arbiter-error", (payload) =>
			callback(payload),
		),
});
