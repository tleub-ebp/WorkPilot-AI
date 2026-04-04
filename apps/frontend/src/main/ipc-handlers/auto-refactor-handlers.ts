import { ipcMain } from "electron";
import {
	type AutoRefactorRequest,
	autoRefactorService,
} from "../auto-refactor-service";

/**
 * Register IPC handlers for Auto-Refactor functionality
 */
export function registerAutoRefactorHandlers(): void {
	// Start auto-refactor analysis
	ipcMain.handle(
		"auto-refactor:start",
		async (_event, request: AutoRefactorRequest) => {
			try {
				await autoRefactorService.analyze(request);
				return { success: true };
			} catch (error) {
				console.error("[AutoRefactor] Start error:", error);
				return {
					success: false,
					error: error instanceof Error ? error.message : "Unknown error",
				};
			}
		},
	);

	// Cancel auto-refactor analysis
	ipcMain.handle("auto-refactor:cancel", async () => {
		try {
			const cancelled = autoRefactorService.cancel();
			return { success: true, cancelled };
		} catch (error) {
			console.error("[AutoRefactor] Cancel error:", error);
			return {
				success: false,
				error: error instanceof Error ? error.message : "Unknown error",
			};
		}
	});

	// Configure service paths
	ipcMain.handle(
		"auto-refactor:configure",
		async (
			_event,
			config: { pythonPath?: string; autoBuildSourcePath?: string },
		) => {
			try {
				autoRefactorService.configure(
					config.pythonPath,
					config.autoBuildSourcePath,
				);
				return { success: true };
			} catch (error) {
				console.error("[AutoRefactor] Configure error:", error);
				return {
					success: false,
					error: error instanceof Error ? error.message : "Unknown error",
				};
			}
		},
	);
}

/**
 * Setup event listeners for Auto-Refactor service events
 * These events are forwarded to the renderer process
 */
export function setupAutoRefactorEventForwarding(): void {
	// Forward status updates
	autoRefactorService.on("status", (status: string) => {
		const mainWindow = global.mainWindow;
		if (mainWindow && !mainWindow.isDestroyed()) {
			mainWindow.webContents.send("auto-refactor:status", status);
		}
	});

	// Forward streaming output
	autoRefactorService.on("stream-chunk", (chunk: string) => {
		const mainWindow = global.mainWindow;
		if (mainWindow && !mainWindow.isDestroyed()) {
			mainWindow.webContents.send("auto-refactor:stream-chunk", chunk);
		}
	});

	// Forward errors
	autoRefactorService.on("error", (error: string) => {
		const mainWindow = global.mainWindow;
		if (mainWindow && !mainWindow.isDestroyed()) {
			mainWindow.webContents.send("auto-refactor:error", error);
		}
	});

	// Forward completion with analysis result
	autoRefactorService.on("complete", (result) => {
		const mainWindow = global.mainWindow;
		if (mainWindow && !mainWindow.isDestroyed()) {
			mainWindow.webContents.send("auto-refactor:complete", result);
		}
	});

	// Forward execution completion (if auto-executed)
	autoRefactorService.on("execution-complete", (result) => {
		const mainWindow = global.mainWindow;
		if (mainWindow && !mainWindow.isDestroyed()) {
			mainWindow.webContents.send("auto-refactor:execution-complete", result);
		}
	});
}
