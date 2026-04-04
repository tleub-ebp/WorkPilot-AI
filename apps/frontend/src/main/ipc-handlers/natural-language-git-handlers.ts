import { BrowserWindow, ipcMain } from "electron";
import type { NaturalLanguageGitRequest } from "../natural-language-git-service";
import { naturalLanguageGitService } from "../natural-language-git-service";

/**
 * Set up IPC handlers for natural language Git functionality
 */
export function setupNaturalLanguageGitHandlers(): void {
	// Execute natural language Git command
	ipcMain.handle(
		"execute-natural-language-git",
		async (event, request: NaturalLanguageGitRequest) => {
			try {
				await naturalLanguageGitService.execute(request);
			} catch (error) {
				console.error("[NaturalLanguageGit] Error executing command:", error);
				const win = BrowserWindow.fromWebContents(event.sender);
				if (win) {
					win.webContents.send(
						"natural-language-git-error",
						error instanceof Error ? error.message : "Unknown error",
					);
				}
			}
		},
	);

	// Cancel natural language Git command
	ipcMain.handle("cancel-natural-language-git", () => {
		return naturalLanguageGitService.cancel();
	});

	// Forward service events to renderer
	naturalLanguageGitService.on("status", (status: string) => {
		const windows = BrowserWindow.getAllWindows();
		windows.forEach((win) => {
			win.webContents.send("natural-language-git-status", status);
		});
	});

	naturalLanguageGitService.on("stream-chunk", (chunk: string) => {
		const windows = BrowserWindow.getAllWindows();
		windows.forEach((win) => {
			win.webContents.send("natural-language-git-stream-chunk", chunk);
		});
	});

	naturalLanguageGitService.on("error", (error: string) => {
		const windows = BrowserWindow.getAllWindows();
		windows.forEach((win) => {
			win.webContents.send("natural-language-git-error", error);
		});
	});

	naturalLanguageGitService.on("complete", (result) => {
		const windows = BrowserWindow.getAllWindows();
		windows.forEach((win) => {
			win.webContents.send("natural-language-git-complete", result);
		});
	});
}
