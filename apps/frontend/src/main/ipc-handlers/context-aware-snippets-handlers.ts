import { ipcMain } from "electron";
import type { ContextAwareSnippetRequest } from "../context-aware-snippets-service";
import { contextAwareSnippetsService } from "../context-aware-snippets-service";

/**
 * Setup IPC handlers for context-aware snippets functionality
 * Call this once when the app initializes
 */
export function setupContextAwareSnippetsHandlers(): void {
	// Handle snippet generation request
	ipcMain.handle(
		"context-aware-snippets:generate",
		async (_, request: ContextAwareSnippetRequest) => {
			try {
				await contextAwareSnippetsService.generateSnippet(request);
				return { success: true };
			} catch (error) {
				console.error("[ContextAwareSnippets] Generate error:", error);
				return {
					success: false,
					error: error instanceof Error ? error.message : "Unknown error",
				};
			}
		},
	);

	// Handle cancel request
	ipcMain.handle("context-aware-snippets:cancel", async () => {
		try {
			const cancelled = contextAwareSnippetsService.cancel();
			return { success: true, cancelled };
		} catch (error) {
			console.error("[ContextAwareSnippets] Cancel error:", error);
			return {
				success: false,
				error: error instanceof Error ? error.message : "Unknown error",
			};
		}
	});

	// Handle service configuration
	ipcMain.handle(
		"context-aware-snippets:configure",
		async (
			_,
			config: { pythonPath?: string; autoBuildSourcePath?: string },
		) => {
			try {
				contextAwareSnippetsService.configure(
					config.pythonPath,
					config.autoBuildSourcePath,
				);
				return { success: true };
			} catch (error) {
				console.error("[ContextAwareSnippets] Configure error:", error);
				return {
					success: false,
					error: error instanceof Error ? error.message : "Unknown error",
				};
			}
		},
	);
}

/**
 * Cleanup IPC handlers for context-aware snippets
 * Call this during app shutdown
 */
export function cleanupContextAwareSnippetsHandlers(): void {
	// Remove all handlers
	ipcMain.removeHandler("context-aware-snippets:generate");
	ipcMain.removeHandler("context-aware-snippets:cancel");
	ipcMain.removeHandler("context-aware-snippets:configure");

	// Cancel any active generation
	contextAwareSnippetsService.cancel();
}
