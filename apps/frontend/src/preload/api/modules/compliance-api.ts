/**
 * Compliance API
 *
 * Renderer-side bridge to the compliance evidence collector runner.
 */

import type {
	ComplianceFramework,
	ComplianceReport,
} from "../../../shared/types/compliance";
import { createIpcListener, invokeIpc } from "./ipc-utils";

export interface ComplianceRunOptions {
	projectPath: string;
	framework?: ComplianceFramework;
}

export interface ComplianceEvent {
	type: "start" | "progress" | "complete";
	data: { status?: string; collected?: number; missing?: number };
}

export interface ComplianceAPI {
	runComplianceScan: (options: ComplianceRunOptions) => Promise<ComplianceReport>;
	cancelComplianceScan: () => Promise<boolean>;
	onComplianceEvent: (
		callback: (event: ComplianceEvent) => void,
	) => () => void;
	onComplianceResult: (
		callback: (report: ComplianceReport) => void,
	) => () => void;
	onComplianceError: (callback: (error: string) => void) => () => void;
}

export const createComplianceAPI = (): ComplianceAPI => ({
	runComplianceScan: (options: ComplianceRunOptions) =>
		invokeIpc<ComplianceReport>("compliance:run", options),

	cancelComplianceScan: () => invokeIpc<boolean>("compliance:cancel"),

	onComplianceEvent: (callback) =>
		createIpcListener<[ComplianceEvent]>("compliance-event", (payload) =>
			callback(payload),
		),

	onComplianceResult: (callback) =>
		createIpcListener<[ComplianceReport]>("compliance-result", (payload) =>
			callback(payload),
		),

	onComplianceError: (callback) =>
		createIpcListener<[string]>("compliance-error", (payload) =>
			callback(payload),
		),
});
