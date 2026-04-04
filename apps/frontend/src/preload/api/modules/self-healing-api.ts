/**
 * Self-Healing API
 * Exposes the Self-Healing Codebase + Incident Responder functionality to the renderer.
 */

import { ipcRenderer } from "electron";

// Use string literals to avoid import issues in preload context
const CH = {
	DASHBOARD: "selfHealing:getDashboard",
	INCIDENTS: "selfHealing:getIncidents",
	OPERATIONS: "selfHealing:getOperations",
	FRAGILITY: "selfHealing:getFragility",
	CICD_ENABLE: "selfHealing:cicd:enable",
	CICD_DISABLE: "selfHealing:cicd:disable",
	CICD_CONFIG: "selfHealing:cicd:config",
	PROD_CONNECT: "selfHealing:production:connect",
	PROD_DISCONNECT: "selfHealing:production:disconnect",
	PROD_CONFIG: "selfHealing:production:config",
	PROACTIVE_SCAN: "selfHealing:proactive:scan",
	PROACTIVE_CONFIG: "selfHealing:proactive:config",
	TRIGGER_FIX: "selfHealing:triggerFix",
	CANCEL_OP: "selfHealing:cancelOperation",
	DISMISS: "selfHealing:dismissIncident",
	RETRY: "selfHealing:retryIncident",
	EVT_INCIDENT: "selfHealing:incidentDetected",
	EVT_PROGRESS: "selfHealing:operationProgress",
	EVT_COMPLETE: "selfHealing:operationComplete",
} as const;

export interface SelfHealingAPIObject {
	getDashboard(
		projectPath: string,
	): Promise<{ success: boolean; data?: unknown }>;
	getIncidents(
		projectPath: string,
		mode?: string,
	): Promise<{ success: boolean; data?: unknown[] }>;
	getOperations(
		projectPath: string,
	): Promise<{ success: boolean; data?: unknown[] }>;
	getFragility(
		projectPath: string,
	): Promise<{ success: boolean; data?: unknown[] }>;

	cicdEnable(
		projectPath: string,
	): Promise<{ success: boolean; error?: string }>;
	cicdDisable(
		projectPath: string,
	): Promise<{ success: boolean; error?: string }>;
	cicdConfig(
		projectPath: string,
		config: Record<string, unknown>,
	): Promise<{ success: boolean; config?: unknown; error?: string }>;

	productionConnect(
		projectPath: string,
		sourceConfig: Record<string, unknown>,
	): Promise<{ success: boolean; error?: string }>;
	productionDisconnect(
		projectPath: string,
		source: string,
	): Promise<{ success: boolean; error?: string }>;
	productionConfig(
		projectPath: string,
		config: Record<string, unknown>,
	): Promise<{ success: boolean; error?: string }>;

	proactiveScan(
		projectPath: string,
	): Promise<{ success: boolean; error?: string }>;
	proactiveConfig(
		projectPath: string,
		config: Record<string, unknown>,
	): Promise<{ success: boolean; error?: string }>;

	triggerFix(
		projectPath: string,
		incidentId: string,
	): Promise<{ success: boolean; error?: string }>;
	cancelOperation(
		projectPath: string,
		operationId: string,
	): Promise<{ success: boolean; error?: string }>;
	dismissIncident(
		projectPath: string,
		incidentId: string,
	): Promise<{ success: boolean; error?: string }>;
	retryIncident(
		projectPath: string,
		incidentId: string,
	): Promise<{ success: boolean; error?: string }>;

	onIncidentDetected(callback: (data: unknown) => void): () => void;
	onOperationProgress(callback: (data: unknown) => void): () => void;
	onOperationComplete(callback: (data: unknown) => void): () => void;
}

export const createSelfHealingAPI = (): SelfHealingAPIObject => ({
	getDashboard: (projectPath) => ipcRenderer.invoke(CH.DASHBOARD, projectPath),
	getIncidents: (projectPath, mode?) =>
		ipcRenderer.invoke(CH.INCIDENTS, projectPath, mode),
	getOperations: (projectPath) =>
		ipcRenderer.invoke(CH.OPERATIONS, projectPath),
	getFragility: (projectPath) => ipcRenderer.invoke(CH.FRAGILITY, projectPath),

	cicdEnable: (projectPath) => ipcRenderer.invoke(CH.CICD_ENABLE, projectPath),
	cicdDisable: (projectPath) =>
		ipcRenderer.invoke(CH.CICD_DISABLE, projectPath),
	cicdConfig: (projectPath, config) =>
		ipcRenderer.invoke(CH.CICD_CONFIG, projectPath, config),

	productionConnect: (projectPath, sourceConfig) =>
		ipcRenderer.invoke(CH.PROD_CONNECT, projectPath, sourceConfig),
	productionDisconnect: (projectPath, source) =>
		ipcRenderer.invoke(CH.PROD_DISCONNECT, projectPath, source),
	productionConfig: (projectPath, config) =>
		ipcRenderer.invoke(CH.PROD_CONFIG, projectPath, config),

	proactiveScan: (projectPath) =>
		ipcRenderer.invoke(CH.PROACTIVE_SCAN, projectPath),
	proactiveConfig: (projectPath, config) =>
		ipcRenderer.invoke(CH.PROACTIVE_CONFIG, projectPath, config),

	triggerFix: (projectPath, incidentId) =>
		ipcRenderer.invoke(CH.TRIGGER_FIX, projectPath, incidentId),
	cancelOperation: (projectPath, operationId) =>
		ipcRenderer.invoke(CH.CANCEL_OP, projectPath, operationId),
	dismissIncident: (projectPath, incidentId) =>
		ipcRenderer.invoke(CH.DISMISS, projectPath, incidentId),
	retryIncident: (projectPath, incidentId) =>
		ipcRenderer.invoke(CH.RETRY, projectPath, incidentId),

	onIncidentDetected: (callback) => {
		const handler = (_event: Electron.IpcRendererEvent, data: unknown) =>
			callback(data);
		ipcRenderer.on(CH.EVT_INCIDENT, handler);
		return () => ipcRenderer.removeListener(CH.EVT_INCIDENT, handler);
	},
	onOperationProgress: (callback) => {
		const handler = (_event: Electron.IpcRendererEvent, data: unknown) =>
			callback(data);
		ipcRenderer.on(CH.EVT_PROGRESS, handler);
		return () => ipcRenderer.removeListener(CH.EVT_PROGRESS, handler);
	},
	onOperationComplete: (callback) => {
		const handler = (_event: Electron.IpcRendererEvent, data: unknown) =>
			callback(data);
		ipcRenderer.on(CH.EVT_COMPLETE, handler);
		return () => ipcRenderer.removeListener(CH.EVT_COMPLETE, handler);
	},
});
