import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import type { BrowserWindow } from "electron";
import { app, ipcMain } from "electron";
import {
	DEFAULT_APP_SETTINGS,
	DEFAULT_FEATURE_MODELS,
	DEFAULT_FEATURE_THINKING,
	IPC_CHANNELS,
} from "../../shared/constants";
import type { AppSettings } from "../../shared/types";
import { debugError } from "../../shared/utils/debug-logger";
import { projectStore } from "../project-store";
import type {
	PromptOptimizeRequest,
	PromptOptimizerResult,
} from "../prompt-optimizer-service";
import { promptOptimizerService } from "../prompt-optimizer-service";
import { safeSendToRenderer } from "./utils";

/**
 * Read prompt optimizer feature settings from the settings file
 */
function getPromptOptimizerSettings(): {
	model: string;
	thinkingLevel: string;
} {
	const settingsPath = path.join(app.getPath("userData"), "settings.json");

	try {
		if (existsSync(settingsPath)) {
			const content = readFileSync(settingsPath, "utf-8");
			const settings: AppSettings = {
				...DEFAULT_APP_SETTINGS,
				...JSON.parse(content),
			};

			const featureModels = settings.featureModels ?? DEFAULT_FEATURE_MODELS;
			const featureThinking =
				settings.featureThinking ?? DEFAULT_FEATURE_THINKING;

			return {
				model:
					featureModels.promptOptimizer ??
					DEFAULT_FEATURE_MODELS.promptOptimizer,
				thinkingLevel:
					featureThinking.promptOptimizer ??
					DEFAULT_FEATURE_THINKING.promptOptimizer,
			};
		}
	} catch (error) {
		debugError(
			"[PromptOptimizer Handler] Failed to read feature settings:",
			error,
		);
	}

	return {
		model: DEFAULT_FEATURE_MODELS.promptOptimizer,
		thinkingLevel: DEFAULT_FEATURE_THINKING.promptOptimizer,
	};
}

/**
 * Register all prompt optimizer IPC handlers
 */
export function registerPromptOptimizerHandlers(
	getMainWindow: () => BrowserWindow | null,
): void {
	// ============================================
	// Prompt Optimizer Operations
	// ============================================

	/**
	 * Handle optimization request from renderer
	 * Receives: projectId, prompt, agentType
	 * Fires and forgets — results come back via events
	 */
	ipcMain.on(
		IPC_CHANNELS.PROMPT_OPTIMIZER_OPTIMIZE,
		async (
			_,
			projectId: string,
			prompt: string,
			agentType: "analysis" | "coding" | "verification" | "general",
		) => {
			const project = projectStore.getProject(projectId);
			if (!project) {
				safeSendToRenderer(
					getMainWindow,
					IPC_CHANNELS.PROMPT_OPTIMIZER_ERROR,
					"Project not found",
				);
				return;
			}

			// Get feature settings from Agent Settings
			const featureSettings = getPromptOptimizerSettings();

			// Configure service with Python path from settings
			try {
				const settingsPath = path.join(
					app.getPath("userData"),
					"settings.json",
				);
				if (existsSync(settingsPath)) {
					const content = readFileSync(settingsPath, "utf-8");
					const settings: AppSettings = {
						...DEFAULT_APP_SETTINGS,
						...JSON.parse(content),
					};
					promptOptimizerService.configure(
						settings.pythonPath,
						settings.autoBuildPath,
					);
				}
			} catch (error) {
				debugError(
					"[PromptOptimizer Handler] Failed to read settings for configuration:",
					error,
				);
			}

			// Build optimization request
			const request: PromptOptimizeRequest = {
				projectDir: project.path,
				prompt,
				agentType,
				model: featureSettings.model,
				thinkingLevel: featureSettings.thinkingLevel,
			};

			// Start optimization (async, results come via events)
			promptOptimizerService.optimize(request).catch((error) => {
				debugError("[PromptOptimizer Handler] Optimization error:", error);
				safeSendToRenderer(
					getMainWindow,
					IPC_CHANNELS.PROMPT_OPTIMIZER_ERROR,
					error instanceof Error ? error.message : "Unknown optimization error",
				);
			});
		},
	);

	// ============================================
	// Prompt Optimizer Event Forwarding (Service -> Renderer)
	// ============================================

	// Forward streaming chunks to renderer
	promptOptimizerService.on("stream-chunk", (chunk: string) => {
		safeSendToRenderer(
			getMainWindow,
			IPC_CHANNELS.PROMPT_OPTIMIZER_STREAM_CHUNK,
			chunk,
		);
	});

	// Forward status updates to renderer
	promptOptimizerService.on("status", (status: string) => {
		safeSendToRenderer(
			getMainWindow,
			IPC_CHANNELS.PROMPT_OPTIMIZER_STATUS,
			status,
		);
	});

	// Forward errors to renderer
	promptOptimizerService.on("error", (error: string) => {
		safeSendToRenderer(
			getMainWindow,
			IPC_CHANNELS.PROMPT_OPTIMIZER_ERROR,
			error,
		);
	});

	// Forward completion to renderer with structured result
	promptOptimizerService.on("complete", (result: PromptOptimizerResult) => {
		safeSendToRenderer(
			getMainWindow,
			IPC_CHANNELS.PROMPT_OPTIMIZER_COMPLETE,
			result,
		);
	});
}
