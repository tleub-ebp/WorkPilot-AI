/**
 * IPC Handlers for GitHub Copilot CLI Service
 *
 * Fournit une interface IPC entre le frontend et le GitHubCopilotService
 */

import { ipcMain } from "electron";
import type {
	CopilotConfig,
	CopilotStatus,
} from "../services/github-copilot-service";
import { gitHubCopilotService } from "../services/github-copilot-service";

/**
 * Enregistrer tous les handlers IPC pour GitHub Copilot
 */
export function registerGitHubCopilotHandlers(): void {
	/**
	 * Obtenir le statut de GitHub Copilot CLI
	 */
	ipcMain.handle("github-copilot:getStatus", (): CopilotStatus => {
		return gitHubCopilotService.getStatus();
	});

	/**
	 * Obtenir la configuration de GitHub Copilot
	 */
	ipcMain.handle("github-copilot:getConfig", (): CopilotConfig => {
		return gitHubCopilotService.getConfig();
	});

	/**
	 * Configurer le token GitHub Copilot
	 */
	ipcMain.handle(
		"github-copilot:setToken",
		async (_event, token: string): Promise<void> => {
			await gitHubCopilotService.setToken(token);
		},
	);

	/**
	 * Supprimer le token GitHub Copilot
	 */
	ipcMain.handle("github-copilot:removeToken", async (): Promise<void> => {
		await gitHubCopilotService.removeToken();
	});

	/**
	 * Authentifier avec GitHub CLI
	 */
	ipcMain.handle("github-copilot:authenticate", async (): Promise<void> => {
		await gitHubCopilotService.authenticate();
	});

	/**
	 * Se déconnecter
	 */
	ipcMain.handle("github-copilot:logout", async (): Promise<void> => {
		await gitHubCopilotService.logout();
	});

	/**
	 * Tester la connexion GitHub Copilot
	 */
	ipcMain.handle(
		"github-copilot:testConnection",
		async (): Promise<{
			success: boolean;
			message: string;
			details?: unknown;
		}> => {
			return await gitHubCopilotService.testConnection();
		},
	);

	/**
	 * Rafraîchir le statut
	 */
	ipcMain.handle("github-copilot:refreshStatus", async (): Promise<void> => {
		await gitHubCopilotService.refreshStatus();
	});

	/**
	 * Obtenir les variables d'environnement
	 */
	ipcMain.handle("github-copilot:getEnv", (): Record<string, string> => {
		return gitHubCopilotService.getEnvironmentVariables();
	});

	/**
	 * S'abonner aux événements de statut
	 */
	ipcMain.on("github-copilot:subscribe", (event) => {
		const statusChannel = "github-copilot:status-updated";
		const configChannel = "github-copilot:config-updated";

		const onStatusUpdated = (status: CopilotStatus) => {
			event.sender.send(statusChannel, status);
		};

		const onConfigUpdated = (config: CopilotConfig) => {
			event.sender.send(configChannel, config);
		};

		gitHubCopilotService.on("status-updated", onStatusUpdated);
		gitHubCopilotService.on("config-updated", onConfigUpdated);

		// Envoyer le statut actuel immédiatement
		event.sender.send(statusChannel, gitHubCopilotService.getStatus());
		event.sender.send(configChannel, gitHubCopilotService.getConfig());

		// Nettoyage quand la fenêtre est fermée
		event.sender.on("destroyed", () => {
			gitHubCopilotService.off("status-updated", onStatusUpdated);
			gitHubCopilotService.off("config-updated", onConfigUpdated);
		});
	});
}
