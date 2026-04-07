/**
 * IPC Handlers for Credential Manager
 *
 * Fournit une interface IPC entre le frontend et le CredentialManager
 */

import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { ipcMain } from "electron";

const execFileAsync = promisify(execFile);

import type {
	CredentialConfig,
	UsageData,
} from "../services/credential-manager";
import {
	credentialManager,
	detectWindsurfLocalToken,
	readWindsurfCachedPlanInfo,
} from "../services/credential-manager";

/**
 * Extract version from command output using regex
 */
function extractVersionFromOutput(output: string): string | undefined {
	const versionRegex = /(\d+\.\d+\.\d+)/;
	const match = versionRegex.exec(output.trim());
	return match ? match[1] : undefined;
}

/**
 * Try to get codex version using direct execution
 */
async function tryDirectCodexVersion(): Promise<string | undefined> {
	try {
		const result = await execFileAsync("codex", ["--version"], {
			encoding: "utf-8",
			timeout: 5000,
			windowsHide: true,
		});
		return extractVersionFromOutput(result.stdout);
	} catch {
		return undefined;
	}
}

/**
 * Try to get codex version using shell execution
 */
async function tryShellCodexVersion(): Promise<string | undefined> {
	try {
		const result = await execFileAsync("codex", ["--version"], {
			encoding: "utf-8",
			timeout: 5000,
			windowsHide: true,
			shell: true,
		});
		return extractVersionFromOutput(result.stdout);
	} catch {
		return undefined;
	}
}

/**
 * Try to get codex version using Windows npm global path
 */
async function tryWindowsNpmCodexVersion(): Promise<string | undefined> {
	try {
		const os = await import("node:os");
		const path = await import("node:path");
		const codexCmd = path.join(
			os.homedir(),
			"AppData",
			"Roaming",
			"npm",
			"codex.cmd",
		);
		const { existsSync } = await import("node:fs");

		if (!existsSync(codexCmd)) {
			return undefined;
		}

		const cmdExe = process.env.ComSpec || "C:\\Windows\\System32\\cmd.exe";
		const result = await execFileAsync(
			cmdExe,
			["/d", "/s", "/c", `""${codexCmd}" --version"`],
			{
				encoding: "utf-8",
				timeout: 5000,
				windowsHide: true,
			},
		);
		return extractVersionFromOutput(result.stdout);
	} catch {
		return undefined;
	}
}

/**
 * Get codex CLI version using multiple fallback strategies
 */
async function getCodexVersion(): Promise<string | undefined> {
	// Strategy 1: direct exec
	let version = await tryDirectCodexVersion();
	if (version) return version;

	// Strategy 2: shell execution
	version = await tryShellCodexVersion();
	if (version) return version;

	// Strategy 3: Windows npm global path
	return await tryWindowsNpmCodexVersion();
}

/**
 * Enregistrer tous les handlers IPC pour les credentials
 */
export function registerCredentialHandlers(): void {
	/**
	 * Obtenir le credential actif
	 */
	ipcMain.handle("credential:getActive", (): CredentialConfig | null => {
		return credentialManager.getActiveCredential();
	});

	/**
	 * Définir le provider actif
	 */
	ipcMain.handle(
		"credential:setActive",
		async (
			_event,
			provider: string,
			type: "oauth" | "api_key",
			profileId?: string,
		): Promise<void> => {
			await credentialManager.setActiveProvider(provider, type, profileId);
		},
	);

	/**
	 * Obtenir les données d'usage pour un provider
	 * For windsurf: fetches on-demand from Codeium API if no cached data or stale (>5 min)
	 */
	ipcMain.handle(
		"usage:getData",
		async (_event, provider: string): Promise<UsageData | null> => {
			const cached = credentialManager.getUsageData(provider);

			// For windsurf: fetch on-demand if no data or stale (>5 minutes)
			if (provider === "windsurf") {
				const WINDSURF_TTL_MS = 5 * 60 * 1000; // 5 minutes
				const isStale =
					cached && Date.now() - cached.timestamp > WINDSURF_TTL_MS;
				if (!cached || isStale) {
					return await credentialManager.fetchWindsurfUsage();
				}
			}

			return cached ?? null;
		},
	);

	/**
	 * Obtenir toutes les données d'usage
	 */
	ipcMain.handle("usage:getAllData", (): Record<string, UsageData> => {
		const allData = credentialManager.getAllUsageData();
		// Convertir Map en objet pour la sérialisation JSON
		return Object.fromEntries(allData.entries());
	});

	/**
	 * Mettre à jour les données d'usage (appelé par les services d'usage)
	 */
	ipcMain.handle(
		"usage:updateData",
		(_event, provider: string, usageData: Partial<UsageData>): void => {
			credentialManager.updateUsageData(provider, usageData);
		},
	);

	/**
	 * Valider les credentials actifs
	 */
	ipcMain.handle("credential:validate", async (): Promise<boolean> => {
		return await credentialManager.validateActiveCredentials();
	});

	/**
	 * Tester un provider (incluant les cas spéciaux)
	 */
	ipcMain.handle(
		"credential:testProvider",
		async (
			_event,
			provider: string,
		): Promise<{ success: boolean; message: string; details?: unknown }> => {
			return await credentialManager.testProvider(provider);
		},
	);

	/**
	 * Obtenir les variables d'environnement pour le processus Python
	 */
	ipcMain.handle("credential:getEnv", (): Record<string, string> => {
		return credentialManager.getEnvironmentVariables();
	});

	/**
	 * S'abonner aux événements de credentials
	 */
	ipcMain.on("credential:subscribe", (event) => {
		const channel = "credential:updated";

		const onUpdate = (credential: CredentialConfig | null) => {
			event.sender.send(channel, credential);
		};

		credentialManager.on("credential:updated", onUpdate);

		// Nettoyage quand la fenêtre est fermée
		event.sender.on("destroyed", () => {
			credentialManager.off("credential:updated", onUpdate);
		});
	});

	/**
	 * S'abonner aux événements d'usage
	 */
	ipcMain.on("usage:subscribe", (event) => {
		const channel = "usage:changed";

		const onUpdate = (data: UsageData) => {
			event.sender.send(channel, data);
		};

		credentialManager.on("usage:changed", onUpdate);

		// Nettoyage quand la fenêtre est fermée
		event.sender.on("destroyed", () => {
			credentialManager.off("usage:changed", onUpdate);
		});
	});

	/**
	 * S'abonner aux événements de switch de provider
	 */
	ipcMain.on("provider:subscribe", (event) => {
		const channel = "provider:switched";

		const onSwitch = (data: {
			provider: string;
			type: "oauth" | "api_key";
		}) => {
			event.sender.send(channel, data);
		};

		credentialManager.on("provider:switched", onSwitch);

		// Nettoyage quand la fenêtre est fermée
		event.sender.on("destroyed", () => {
			credentialManager.off("provider:switched", onSwitch);
		});
	});

	/**
	 * Détecter le token Windsurf depuis l'installation IDE locale
	 * Lit le state.vscdb de Windsurf pour extraire la clé API sk-ws-...
	 * Enrichit la réponse avec les infos du plan (planName, usage) si disponibles.
	 */
	ipcMain.handle(
		"credential:detectWindsurfToken",
		async (): Promise<{
			success: boolean;
			apiKey?: string;
			userName?: string;
			planName?: string;
			usageInfo?: {
				usedMessages: number;
				totalMessages: number;
				usedFlowActions: number;
				totalFlowActions: number;
			};
			error?: string;
		}> => {
			const tokenResult = await detectWindsurfLocalToken();
			if (!tokenResult.success) return tokenResult;

			// Enrich with plan info (planName, usage) from cached plan data
			try {
				const planResult = await readWindsurfCachedPlanInfo();
				if (planResult.success && planResult.planInfo) {
					return {
						...tokenResult,
						userName: planResult.userName || tokenResult.userName,
						planName: planResult.planInfo.planName,
						usageInfo: {
							usedMessages: planResult.planInfo.usage.usedMessages,
							totalMessages: planResult.planInfo.usage.messages,
							usedFlowActions: planResult.planInfo.usage.usedFlowActions,
							totalFlowActions: planResult.planInfo.usage.flowActions,
						},
					};
				}
			} catch (e) {
				console.warn(
					"[CredentialHandlers] Failed to enrich Windsurf token with plan info:",
					e,
				);
			}

			return tokenResult;
		},
	);

	/**
	 * Vérifier le statut OAuth Claude (vérifie les fichiers config CLI sur le disque)
	 * Retourne si l'utilisateur est authentifié via OAuth Claude Code
	 */
	ipcMain.handle(
		"credential:checkClaudeOAuth",
		async (): Promise<{ isAuthenticated: boolean; profileName?: string }> => {
			return await credentialManager.checkClaudeOAuthStatusPublic();
		},
	);

	/**
	 * Vérifier le statut OAuth OpenAI Codex CLI (vérifie les fichiers config CLI sur le disque)
	 * Retourne si l'utilisateur est authentifié via OpenAI Codex CLI, avec la version CLI
	 */
	ipcMain.handle(
		"credential:checkOpenAICodexOAuth",
		async (): Promise<{
			isAuthenticated: boolean;
			profileName?: string;
			version?: string;
		}> => {
			const authStatus =
				await credentialManager.checkOpenAICodexOAuthStatusPublic();

			const version = await getCodexVersion();
			return { ...authStatus, version };
		},
	);
}
