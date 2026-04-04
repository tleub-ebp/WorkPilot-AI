/**
 * Agent Decision Logger IPC Handlers (Feature 30)
 *
 * Exposes two request-response channels:
 *   agentDecision:getLog   — read decision_log.json from a spec directory
 *   agentDecision:clearLog — delete decision_log.json
 *
 * Live entry forwarding (Main → Renderer) is wired in agent-events-handlers.ts
 * by listening for DECISION_LOG_ENTRY task events.
 */

import { existsSync, readFileSync, unlinkSync } from "node:fs";
import path from "node:path";
import { ipcMain } from "electron";
import { IPC_CHANNELS } from "../../shared/constants/ipc";
import type {
	DecisionEntry,
	DecisionLog,
} from "../../shared/types/decision-logger";

const DECISION_LOG_FILE = "decision_log.json";

function getDecisionLogPath(specDirPath: string): string {
	return path.join(specDirPath, DECISION_LOG_FILE);
}

export function registerDecisionLoggerHandlers(): void {
	// ── Load persisted log ────────────────────────────────────────────────────
	ipcMain.handle(
		IPC_CHANNELS.AGENT_DECISION_LOG_GET,
		(
			_,
			specDirPath: string,
			taskId: string,
			specId: string,
		): { success: boolean; data?: DecisionLog; error?: string } => {
			try {
				const logPath = getDecisionLogPath(specDirPath);
				if (!existsSync(logPath)) {
					return {
						success: true,
						data: {
							taskId,
							specId,
							entries: [],
							loaded_at: new Date().toISOString(),
						},
					};
				}

				const raw = readFileSync(logPath, "utf-8");
				const entries: DecisionEntry[] = JSON.parse(raw);

				return {
					success: true,
					data: {
						taskId,
						specId,
						entries: Array.isArray(entries) ? entries : [],
						loaded_at: new Date().toISOString(),
					},
				};
			} catch (err) {
				return { success: false, error: String(err) };
			}
		},
	);

	// ── Clear log ─────────────────────────────────────────────────────────────
	ipcMain.handle(
		IPC_CHANNELS.AGENT_DECISION_LOG_CLEAR,
		(_, specDirPath: string): { success: boolean; error?: string } => {
			try {
				const logPath = getDecisionLogPath(specDirPath);
				if (existsSync(logPath)) {
					unlinkSync(logPath);
				}
				return { success: true };
			} catch (err) {
				return { success: false, error: String(err) };
			}
		},
	);
}
