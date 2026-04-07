/**
 * GitHub Copilot CLI Service - Service pour l'intégration GitHub Copilot CLI
 *
 * Similaire à claude-code-service.ts mais pour GitHub Copilot CLI
 */

import { exec, spawn } from "node:child_process";
import { EventEmitter } from "node:events";
import fs from "node:fs/promises";
import path from "node:path";
import { promisify } from "node:util";
import { app } from "electron";

const execAsync = promisify(exec);

export interface CopilotStatus {
	installed: boolean;
	version?: string;
	authenticated: boolean;
	username?: string;
	token?: string;
	error?: string;
}

export interface CopilotConfig {
	enabled: boolean;
	token?: string;
	username?: string;
}

/**
 * Service GitHub Copilot CLI
 */
export class GitHubCopilotService extends EventEmitter {
	private status: CopilotStatus = {
		installed: false,
		authenticated: false,
	};
	private config: CopilotConfig = {
		enabled: false,
	};
	private configPath: string;

	constructor() {
		super();
		this.configPath = path.join(
			app.getPath("userData"),
			"github-copilot-config.json",
		);
		this.loadConfig();
		this.initialize();
	}

	/**
	 * Initialiser le service
	 */
	private async initialize(): Promise<void> {
		await this.checkStatus();
		this.emit("status-updated", this.status);
	}

	/**
	 * Charger la configuration depuis le fichier
	 */
	private async loadConfig(): Promise<void> {
		try {
			const data = await fs.readFile(this.configPath, "utf-8");
			this.config = JSON.parse(data);
		} catch (_error) {
			// Fichier n'existe pas, utiliser la configuration par défaut
			this.config = { enabled: false };
		}
	}

	/**
	 * Sauvegarder la configuration
	 */
	private async saveConfig(): Promise<void> {
		try {
			await fs.writeFile(
				this.configPath,
				JSON.stringify(this.config, null, 2),
				"utf-8",
			);
		} catch (error) {
			console.error("[GitHubCopilotService] Failed to save config:", error);
		}
	}

	/**
	 * Vérifier le statut de GitHub Copilot CLI
	 */
	private async checkStatus(): Promise<void> {
		try {
			// Vérifier si GitHub CLI est installé
			const { stdout: versionOutput } = await execAsync("gh --version", {
				timeout: 5000,
			});
			this.status.installed = true;
			this.status.version = versionOutput.trim();

			// Vérifier l'authentification
			try {
				const { stdout: authOutput } = await execAsync("gh auth status", {
					timeout: 5000,
				});

				// Parser le statut d'authentification
				if (authOutput.includes("Logged in to github.com")) {
					this.status.authenticated = true;

					// Extraire le username
					const usernameMatch = authOutput.match(/as\s+(\w+)/);
					if (usernameMatch) {
						this.status.username = usernameMatch[1];
					}
				} else {
					this.status.authenticated = false;
				}
			} catch (_authError) {
				this.status.authenticated = false;
			}

			// Vérifier si le token Copilot est configuré
			try {
				const { stdout: tokenOutput } = await execAsync("gh auth token", {
					timeout: 5000,
				});
				if (tokenOutput.trim()) {
					this.status.token = tokenOutput.trim();
				}
			} catch (_tokenError) {
				// Pas de token configuré
				this.status.token = undefined;
			}

			this.status.error = undefined;
		} catch (error) {
			this.status.installed = false;
			this.status.authenticated = false;
			this.status.error =
				error instanceof Error ? error.message : "GitHub CLI not available";
		}
	}

	/**
	 * Obtenir le statut actuel
	 */
	getStatus(): CopilotStatus {
		return { ...this.status };
	}

	/**
	 * Obtenir la configuration actuelle
	 */
	getConfig(): CopilotConfig {
		return { ...this.config };
	}

	/**
	 * Configurer le token GitHub Copilot
	 */
	async setToken(token: string): Promise<void> {
		try {
			// Valider le format du token (commence par ghp_)
			if (
				!token.startsWith("ghp_") &&
				!token.startsWith("gho_") &&
				!token.startsWith("ghu_")
			) {
				throw new Error(
					"Invalid GitHub token format. Token should start with ghp_, gho_, or ghu_",
				);
			}

			// Mettre à jour la configuration
			this.config.token = token;
			this.config.enabled = true;
			await this.saveConfig();

			// Mettre à jour le statut
			this.status.token = token;
			this.emit("config-updated", this.config);
			this.emit("status-updated", this.status);
		} catch (error) {
			console.error("[GitHubCopilotService] Failed to set token:", error);
			throw error;
		}
	}

	/**
	 * Supprimer le token
	 */
	async removeToken(): Promise<void> {
		try {
			this.config.token = undefined;
			this.config.enabled = false;
			await this.saveConfig();

			this.status.token = undefined;
			this.emit("config-updated", this.config);
			this.emit("status-updated", this.status);
		} catch (error) {
			console.error("[GitHubCopilotService] Failed to remove token:", error);
			throw error;
		}
	}

	/**
	 * Authentifier avec GitHub CLI
	 */
	async authenticate(): Promise<void> {
		return new Promise((resolve, reject) => {
			try {
				const authProcess = spawn("gh", ["auth", "login"], {
					stdio: "inherit",
					shell: true,
				});

				authProcess.on("close", async (code) => {
					if (code === 0) {
						// Authentification réussie, mettre à jour le statut
						await this.checkStatus();
						this.emit("status-updated", this.status);
						resolve();
					} else {
						reject(new Error("GitHub authentication failed"));
					}
				});

				authProcess.on("error", (error) => {
					reject(error);
				});
			} catch (error) {
				reject(error);
			}
		});
	}

	/**
	 * Se déconnecter
	 */
	async logout(): Promise<void> {
		try {
			await execAsync("gh auth logout", { timeout: 10000 });
			await this.checkStatus();
			this.emit("status-updated", this.status);
		} catch (error) {
			console.error("[GitHubCopilotService] Failed to logout:", error);
			throw error;
		}
	}

	/**
	 * Tester la connexion GitHub Copilot
	 */
	async testConnection(): Promise<{
		success: boolean;
		message: string;
		details?: unknown;
	}> {
		try {
			if (!this.status.installed) {
				return {
					success: false,
					message: "GitHub CLI is not installed",
				};
			}

			if (!this.status.authenticated) {
				return {
					success: false,
					message: 'GitHub CLI is not authenticated. Run "gh auth login"',
				};
			}

			// Tester une commande GitHub simple
			const { stdout } = await execAsync("gh api user", { timeout: 10000 });
			const userData = JSON.parse(stdout);

			return {
				success: true,
				message: "GitHub Copilot connection successful",
				details: {
					username: userData.login,
					authenticated: true,
					hasToken: !!this.status.token,
				},
			};
		} catch (error) {
			return {
				success: false,
				message:
					error instanceof Error ? error.message : "Connection test failed",
			};
		}
	}

	/**
	 * Rafraîchir le statut
	 */
	async refreshStatus(): Promise<void> {
		await this.checkStatus();
		this.emit("status-updated", this.status);
	}

	/**
	 * Obtenir les variables d'environnement pour le processus Python
	 */
	getEnvironmentVariables(): Record<string, string> {
		const env: Record<string, string> = {};

		if (this.config.enabled && this.config.token) {
			env.GITHUB_TOKEN = this.config.token;
		}

		if (this.status.username) {
			env.GITHUB_USERNAME = this.status.username;
		}

		return env;
	}

	/**
	 * Nettoyage
	 */
	cleanup(): void {
		this.removeAllListeners();
	}
}

// Instance singleton
export const gitHubCopilotService = new GitHubCopilotService();
