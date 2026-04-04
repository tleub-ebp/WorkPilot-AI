/**
 * Renderer Log IPC Handler
 * =======================
 *
 * Handler IPC pour recevoir les logs du renderer et les traiter
 * avec le système de logs colorés du main process.
 */

import { ipcMain } from "electron";
import { frontendLog } from "../colored-logs";

function getLogFunction(level: string, module?: string) {
	const logTarget = module === "renderer" ? frontendLog.renderer : frontendLog;

	switch (level) {
		case "debug":
			return logTarget.debug;
		case "info":
			return logTarget.info;
		case "success":
			return logTarget.success;
		case "warning":
			return logTarget.warn;
		case "error":
			return logTarget.error;
		default:
			return frontendLog.info;
	}
}

// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
function processLogMessage(logMessage: any): void {
	const { level, message, module = "renderer", args = [] } = logMessage;
	const logFunction = getLogFunction(level, module);
	logFunction(message, ...args);
}

export function setupRendererLogHandler(): void {
	// Handler pour les logs du renderer
	ipcMain.handle("renderer-log", (_event, logMessage) => {
		try {
			processLogMessage(logMessage);
			return { success: true };
		} catch (error) {
			console.error("Failed to handle renderer log:", error);
			const errorMessage =
				error instanceof Error ? error.message : String(error);
			return { success: false, error: errorMessage };
		}
	});

	// Alternative: utiliser .on au lieu de .handle pour les logs unidirectionnels
	ipcMain.on("renderer-log", (_event, logMessage) => {
		try {
			processLogMessage(logMessage);
		} catch (error) {
			console.error("Failed to handle renderer log:", error);
		}
	});
}
