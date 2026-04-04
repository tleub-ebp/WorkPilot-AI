/**
 * Learning Loop IPC handlers registration
 *
 * Handles IPC communication between the renderer process and the
 * Learning Loop backend service for pattern management and analysis.
 */

import type { BrowserWindow } from "electron";
import { ipcMain } from "electron";
import { IPC_CHANNELS } from "../../shared/constants";
import { learningLoopService } from "../learning-loop-service";
import { safeSendToRenderer } from "./utils";

/**
 * Register all learning-loop-related IPC handlers
 */
export function registerLearningLoopHandlers(
	getMainWindow: () => BrowserWindow | null,
): () => void {
	// ============================================
	// Pattern CRUD operations (invoke/handle)
	// ============================================

	ipcMain.handle(
		IPC_CHANNELS.LEARNING_LOOP_GET_PATTERNS,
		async (_event, projectDir: string) => {
			try {
				// Read patterns from the project's learning loop storage
				const { readFileSync, existsSync } = require("node:fs");
				const path = require("node:path");
				const patternsPath = path.join(
					projectDir,
					".workpilot",
					"learning_loop",
					"patterns.json",
				);

				if (!existsSync(patternsPath)) {
					return { success: true, data: [] };
				}

				const raw = readFileSync(patternsPath, "utf-8");
				const data = JSON.parse(raw);
				return { success: true, data: data.patterns || [] };
				// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
			} catch (error: any) {
				console.error("[LearningLoop] Failed to get patterns:", error);
				return { success: false, error: error.message };
			}
		},
	);

	ipcMain.handle(
		IPC_CHANNELS.LEARNING_LOOP_GET_SUMMARY,
		async (_event, projectDir: string) => {
			try {
				const { readFileSync, existsSync } = require("node:fs");
				const path = require("node:path");
				const patternsPath = path.join(
					projectDir,
					".workpilot",
					"learning_loop",
					"patterns.json",
				);

				if (!existsSync(patternsPath)) {
					return {
						success: true,
						data: {
							total_patterns: 0,
							by_category: {},
							by_phase: {},
							by_type: {},
							average_confidence: 0,
							total_builds_analyzed: 0,
							last_analyzed_at: null,
							improvement_metrics: null,
							enabled_count: 0,
							disabled_count: 0,
						},
					};
				}

				const raw = readFileSync(patternsPath, "utf-8");
				const data = JSON.parse(raw);
				const patterns = data.patterns || [];

				// Compute summary from patterns
				const byCategory: Record<string, number> = {};
				const byPhase: Record<string, number> = {};
				const byType: Record<string, number> = {};
				let totalConfidence = 0;
				let enabledCount = 0;
				let disabledCount = 0;

				for (const p of patterns) {
					byCategory[p.category] = (byCategory[p.category] || 0) + 1;
					byPhase[p.agent_phase] = (byPhase[p.agent_phase] || 0) + 1;
					byType[p.pattern_type] = (byType[p.pattern_type] || 0) + 1;
					totalConfidence += p.confidence || 0;
					if (p.enabled !== false) {
						enabledCount++;
					} else {
						disabledCount++;
					}
				}

				return {
					success: true,
					data: {
						total_patterns: patterns.length,
						by_category: byCategory,
						by_phase: byPhase,
						by_type: byType,
						average_confidence:
							patterns.length > 0 ? totalConfidence / patterns.length : 0,
						total_builds_analyzed: data.metadata?.total_builds_analyzed || 0,
						last_analyzed_at: data.metadata?.last_analyzed_at || null,
						improvement_metrics: data.metadata?.improvement_metrics || null,
						enabled_count: enabledCount,
						disabled_count: disabledCount,
					},
				};
				// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
			} catch (error: any) {
				console.error("[LearningLoop] Failed to get summary:", error);
				return { success: false, error: error.message };
			}
		},
	);

	ipcMain.handle(
		IPC_CHANNELS.LEARNING_LOOP_DELETE_PATTERN,
		async (_event, projectDir: string, patternId: string) => {
			try {
				const { readFileSync, writeFileSync, existsSync } = require("node:fs");
				const path = require("node:path");
				const patternsPath = path.join(
					projectDir,
					".workpilot",
					"learning_loop",
					"patterns.json",
				);

				if (!existsSync(patternsPath)) {
					return { success: false, error: "No patterns file found" };
				}

				const raw = readFileSync(patternsPath, "utf-8");
				const data = JSON.parse(raw);
				const before = data.patterns?.length || 0;
				data.patterns = (data.patterns || []).filter(
					(p: any) => p.pattern_id !== patternId,
				);
				const after = data.patterns.length;

				if (before === after) {
					return { success: false, error: "Pattern not found" };
				}

				writeFileSync(patternsPath, JSON.stringify(data, null, 2), "utf-8");
				return { success: true };
				// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
			} catch (error: any) {
				console.error("[LearningLoop] Failed to delete pattern:", error);
				return { success: false, error: error.message };
			}
		},
	);

	ipcMain.handle(
		IPC_CHANNELS.LEARNING_LOOP_TOGGLE_PATTERN,
		async (_event, projectDir: string, patternId: string) => {
			try {
				const { readFileSync, writeFileSync, existsSync } = require("node:fs");
				const path = require("node:path");
				const patternsPath = path.join(
					projectDir,
					".workpilot",
					"learning_loop",
					"patterns.json",
				);

				if (!existsSync(patternsPath)) {
					return { success: false, error: "No patterns file found" };
				}

				const raw = readFileSync(patternsPath, "utf-8");
				const data = JSON.parse(raw);
				const pattern = (data.patterns || []).find(
					(p: any) => p.pattern_id === patternId,
				);

				if (!pattern) {
					return { success: false, error: "Pattern not found" };
				}

				pattern.enabled = !pattern.enabled;
				writeFileSync(patternsPath, JSON.stringify(data, null, 2), "utf-8");
				return { success: true, data: pattern.enabled };
				// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
			} catch (error: any) {
				console.error("[LearningLoop] Failed to toggle pattern:", error);
				return { success: false, error: error.message };
			}
		},
	);

	// ============================================
	// Analysis operations (send/on for streaming)
	// ============================================

	ipcMain.on(
		IPC_CHANNELS.LEARNING_LOOP_RUN_ANALYSIS,
		(_event, projectDir: string, specId?: string) => {
			learningLoopService.analyze({
				projectDir,
				specId,
			});
		},
	);

	ipcMain.handle(IPC_CHANNELS.LEARNING_LOOP_STOP_ANALYSIS, () => {
		const cancelled = learningLoopService.cancel();
		return { success: true, cancelled };
	});

	// ============================================
	// Learning Loop Service Events → Renderer
	// ============================================

	const handleStatus = (status: string): void => {
		safeSendToRenderer(
			getMainWindow,
			IPC_CHANNELS.LEARNING_LOOP_STATUS,
			status,
		);
	};

	const handleStreamChunk = (chunk: string): void => {
		safeSendToRenderer(
			getMainWindow,
			IPC_CHANNELS.LEARNING_LOOP_STREAM_CHUNK,
			chunk,
		);
	};

	const handleError = (error: string): void => {
		safeSendToRenderer(getMainWindow, IPC_CHANNELS.LEARNING_LOOP_ERROR, error);
	};

	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
	const handleComplete = (result: any): void => {
		safeSendToRenderer(
			getMainWindow,
			IPC_CHANNELS.LEARNING_LOOP_COMPLETE,
			result,
		);
	};

	learningLoopService.on("status", handleStatus);
	learningLoopService.on("stream-chunk", handleStreamChunk);
	learningLoopService.on("error", handleError);
	learningLoopService.on("complete", handleComplete);

	// Return cleanup function
	return (): void => {
		learningLoopService.off("status", handleStatus);
		learningLoopService.off("stream-chunk", handleStreamChunk);
		learningLoopService.off("error", handleError);
		learningLoopService.off("complete", handleComplete);
	};
}
