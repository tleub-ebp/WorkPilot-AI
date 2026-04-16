/**
 * IPC Handlers for Credential Manager
 *
 * Fournit une interface IPC entre le frontend et le CredentialManager
 */

import { execFile } from "node:child_process";
import { promises as fs } from "node:fs";
import { promisify } from "node:util";
import { app, ipcMain } from "electron";
import path from "node:path";

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

		const cmdExe = process.env.ComSpec || String.raw`C:\Windows\System32\cmd.exe`;
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
 * Cache for the latest @openai/codex version from the npm registry (1 hour TTL).
 */
let cachedCodexLatest: { version: string; timestamp: number } | null = null;
const CODEX_LATEST_CACHE_MS = 60 * 60 * 1000;

async function fetchLatestCodexVersion(): Promise<string | undefined> {
	if (
		cachedCodexLatest &&
		Date.now() - cachedCodexLatest.timestamp < CODEX_LATEST_CACHE_MS
	) {
		return cachedCodexLatest.version;
	}

	try {
		const response = await fetch(
			"https://registry.npmjs.org/@openai/codex/latest",
			{
				headers: {
					Accept: "application/json",
					"User-Agent": "WorkPilot-AI/1.0",
				},
				signal: AbortSignal.timeout(15000),
			},
		);
		if (!response.ok) {
			throw new Error(`HTTP ${response.status}: ${response.statusText}`);
		}
		const data = (await response.json()) as { version?: unknown };
		if (typeof data.version !== "string") {
			throw new TypeError("Invalid version format from npm registry");
		}
		cachedCodexLatest = { version: data.version, timestamp: Date.now() };
		return data.version;
	} catch (error) {
		console.warn("[Codex CLI] Failed to fetch latest version from npm:", error);
		return cachedCodexLatest?.version;
	}
}

/**
 * Compare two semver-like version strings. Returns true if `installed` < `latest`.
 */
function isCodexOutdated(installed: string, latest: string): boolean {
	const parse = (v: string): number[] =>
		v
			.replace(/^v/, "")
			.split(/[.-]/)
			.slice(0, 3)
			.map((n) => {
				const parsed = Number.parseInt(n, 10);
				return Number.isNaN(parsed) ? 0 : parsed;
			});

	try {
		const i = parse(installed);
		const l = parse(latest);
		for (let idx = 0; idx < 3; idx++) {
			const a = i[idx] ?? 0;
			const b = l[idx] ?? 0;
			if (a < b) return true;
			if (a > b) return false;
		}
		return false;
	} catch {
		return false;
	}
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
	 * For windsurf: use API as primary source (contains real-time usage data)
	 * Local cache is only used as fallback if API is unavailable
	 */
	ipcMain.handle(
		"usage:getData",
		async (_event, provider: string): Promise<UsageData | null> => {
			const cached = credentialManager.getUsageData(provider);

			// For windsurf: prefer API (real-time usage data) over local cache (may contain stale/incorrect data)
			// The local cache contains data from the old monthly system which may not reflect actual usage
			if (provider === "windsurf") {
				// Try API first for real-time usage data
				try {
					const apiData = await credentialManager.fetchWindsurfUsage();
					if (apiData) {
						return apiData;
					}
				} catch (error) {
					console.warn("[credential-handlers] Windsurf API fetch failed, using cached data:", error);
				}
				// Fallback to cached data only if API fails
				return cached ?? null;
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
			latest?: string;
			isOutdated?: boolean;
		}> => {
			const authStatus =
				await credentialManager.checkOpenAICodexOAuthStatusPublic();

			const version = await getCodexVersion();
			const latest = version ? await fetchLatestCodexVersion() : undefined;
			const isOutdated =
				version && latest ? isCodexOutdated(version, latest) : false;

			return { ...authStatus, version, latest, isOutdated };
		},
	);

	/**
	 * Installer ou mettre à jour Codex CLI via npm global, en arrière-plan.
	 * Pas de terminal visible : on exécute directement `npm install -g @openai/codex@latest`.
	 */
	ipcMain.handle(
		"credential:updateCodexCli",
		async (): Promise<{
			success: boolean;
			version?: string;
			latest?: string;
			isOutdated?: boolean;
			error?: string;
		}> => {
			const runNpm = async (): Promise<{ stdout: string; stderr: string }> => {
				// Try plain `npm` first, then shell:true fallback (handles npm.cmd on Windows).
				try {
					return await execFileAsync(
						"npm",
						["install", "-g", "@openai/codex@latest"],
						{
							encoding: "utf-8",
							timeout: 5 * 60 * 1000,
							windowsHide: true,
							maxBuffer: 10 * 1024 * 1024,
						},
					);
				} catch (firstErr) {
					try {
						return await execFileAsync(
							"npm",
							["install", "-g", "@openai/codex@latest"],
							{
								encoding: "utf-8",
								timeout: 5 * 60 * 1000,
								windowsHide: true,
								shell: true,
								maxBuffer: 10 * 1024 * 1024,
							},
						);
					} catch {
						throw firstErr;
					}
				}
			};

			try {
				await runNpm();

				// Invalidate caches so the next check sees the fresh version.
				cachedCodexLatest = null;
				const version = await getCodexVersion();
				const latest = await fetchLatestCodexVersion();
				const isOutdated =
					version && latest ? isCodexOutdated(version, latest) : false;

				return { success: true, version, latest, isOutdated };
			} catch (error) {
				const message =
					error instanceof Error ? error.message : String(error);
				console.error("[Codex CLI] Update failed:", message);
				return { success: false, error: message };
			}
		},
	);

	/**
	 * Charger les providers configurés depuis config/configured_providers.json
	 * Ce fichier est maintenant à la racine du projet dans le dossier config/
	 */
	ipcMain.handle(
		"providers:getConfiguredProviders",
		async (): Promise<{ providers?: unknown } | null> => {
			try {
				const appPath = app.getAppPath();
				const cwd = process.cwd();
				const candidates = [
					// Dev mode: process.cwd() is typically apps/frontend
					path.join(cwd, "..", "..", "config", "configured_providers.json"),
					path.join(cwd, "..", "config", "configured_providers.json"),
					path.join(cwd, "config", "configured_providers.json"),
					// app.getAppPath()-based (works in various electron-vite configurations)
					path.join(appPath, "..", "..", "..", "config", "configured_providers.json"),
					path.join(appPath, "..", "..", "config", "configured_providers.json"),
					path.join(appPath, "..", "config", "configured_providers.json"),
					path.join(appPath, "config", "configured_providers.json"),
					// Fallback: src dir
					path.join(appPath, "src", "config", "configured_providers.json"),
				];

				for (const p of candidates) {
					try {
						await fs.access(p);
						const raw = await fs.readFile(p, "utf-8");
						return JSON.parse(raw);
					} catch {
						// try next candidate
					}
				}
				return null;
			} catch (error) {
				console.error(
					"[CredentialHandlers] Failed to load configured_providers.json:",
					error,
				);
				return null;
			}
		},
	);
}
