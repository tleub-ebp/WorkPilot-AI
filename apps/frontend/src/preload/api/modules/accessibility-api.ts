/**
 * Accessibility Agent API
 *
 * Renderer-side bridge to the WCAG accessibility scanner runner.
 */

import type { A11yReport } from "../../../shared/types/accessibility";
import { createIpcListener, invokeIpc } from "./ipc-utils";

export interface AccessibilityRunOptions {
	projectPath: string;
	targetLevel?: "A" | "AA" | "AAA";
}

export interface AccessibilityEvent {
	type: "start" | "progress" | "complete";
	data: { status?: string; violations?: number; filesScanned?: number };
}

export interface AccessibilityAPI {
	runAccessibilityScan: (options: AccessibilityRunOptions) => Promise<A11yReport>;
	cancelAccessibilityScan: () => Promise<boolean>;
	onAccessibilityEvent: (
		callback: (event: AccessibilityEvent) => void,
	) => () => void;
	onAccessibilityResult: (
		callback: (report: A11yReport) => void,
	) => () => void;
	onAccessibilityError: (callback: (error: string) => void) => () => void;
}

export const createAccessibilityAPI = (): AccessibilityAPI => ({
	runAccessibilityScan: (options: AccessibilityRunOptions) =>
		invokeIpc<A11yReport>("accessibility:run", options),

	cancelAccessibilityScan: () => invokeIpc<boolean>("accessibility:cancel"),

	onAccessibilityEvent: (callback) =>
		createIpcListener<[AccessibilityEvent]>(
			"accessibility-event",
			(payload) => callback(payload),
		),

	onAccessibilityResult: (callback) =>
		createIpcListener<[A11yReport]>("accessibility-result", (payload) =>
			callback(payload),
		),

	onAccessibilityError: (callback) =>
		createIpcListener<[string]>("accessibility-error", (payload) =>
			callback(payload),
		),
});
