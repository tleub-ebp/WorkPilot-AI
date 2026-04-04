/**
 * GitHub repository-related IPC handlers
 */

import { ipcMain } from "electron";
import { IPC_CHANNELS } from "../../../shared/constants";
import type {
	GitHubRepository,
	GitHubSyncStatus,
	IPCResult,
} from "../../../shared/types";
import { projectStore } from "../../project-store";
import type { GitHubAPIRepository } from "./types";
import { getGitHubConfig, githubFetch, normalizeRepoReference } from "./utils";

/**
 * Check GitHub connection status
 */
export function registerCheckConnection(): void {
	ipcMain.handle(
		IPC_CHANNELS.GITHUB_CHECK_CONNECTION,
		async (_, projectId: string): Promise<IPCResult<GitHubSyncStatus>> => {
			const project = projectStore.getProject(projectId);
			if (!project) {
				return { success: false, error: "Project not found" };
			}

			const config = getGitHubConfig(project);
			if (!config) {
				return {
					success: true,
					data: {
						connected: false,
						error: "No GitHub token or repository configured",
					},
				};
			}

			try {
				// Normalize repo reference (handles full URLs, git URLs, etc.)
				const normalizedRepo = normalizeRepoReference(config.repo);
				if (!normalizedRepo) {
					return {
						success: true,
						data: {
							connected: false,
							error: "Invalid repository format. Use owner/repo or GitHub URL.",
						},
					};
				}

				// Fetch repo info
				const repoData = (await githubFetch(
					config.token,
					`/repos/${normalizedRepo}`,
				)) as { full_name: string; description?: string };

				// Count open issues
				const issuesData = (await githubFetch(
					config.token,
					`/repos/${normalizedRepo}/issues?state=open&per_page=1`,
				)) as unknown[];

				const openCount = Array.isArray(issuesData) ? issuesData.length : 0;

				return {
					success: true,
					data: {
						connected: true,
						repoFullName: repoData.full_name,
						repoDescription: repoData.description,
						issueCount: openCount,
						lastSyncedAt: new Date().toISOString(),
					},
				};
			} catch (error) {
				return {
					success: true,
					data: {
						connected: false,
						error:
							error instanceof Error
								? error.message
								: "Failed to connect to GitHub",
					},
				};
			}
		},
	);
}

/**
 * Get list of GitHub repositories (personal + organization)
 */
export function registerGetRepositories(): void {
	ipcMain.handle(
		IPC_CHANNELS.GITHUB_GET_REPOSITORIES,
		async (_, projectId: string): Promise<IPCResult<GitHubRepository[]>> => {
			const project = projectStore.getProject(projectId);
			if (!project) {
				return { success: false, error: "Project not found" };
			}

			const config = getGitHubConfig(project);
			if (!config) {
				return { success: false, error: "No GitHub token configured" };
			}

			try {
				// Fetch user's personal + organization repos
				// affiliation parameter includes: owner, collaborator, organization_member
				const repos = (await githubFetch(
					config.token,
					"/user/repos?per_page=100&sort=updated&affiliation=owner,collaborator,organization_member",
				)) as GitHubAPIRepository[];

				const result: GitHubRepository[] = repos.map((repo) => ({
					id: repo.id,
					name: repo.name,
					fullName: repo.full_name,
					description: repo.description,
					url: repo.html_url,
					defaultBranch: repo.default_branch,
					private: repo.private,
					owner: {
						login: repo.owner.login,
						avatarUrl: repo.owner.avatar_url,
					},
				}));

				return { success: true, data: result };
			} catch (error) {
				return {
					success: false,
					error:
						error instanceof Error
							? error.message
							: "Failed to fetch repositories",
				};
			}
		},
	);
}

/**
 * Test GitHub connection for remote configuration modal
 */
export function registerTestConnection(): void {
	ipcMain.handle(
		"github:testConnection",
		async (
			_,
			config: { repo: string; token: string },
		): Promise<{ success: boolean; status?: number; error?: string }> => {
			if (!config.repo || !config.token) {
				return { success: false, error: "Repository and token are required" };
			}

			try {
				// Normalize repo reference (handles full URLs, git URLs, etc.)
				const normalizedRepo = normalizeRepoReference(config.repo);
				if (!normalizedRepo) {
					return {
						success: false,
						error: "Invalid repository format. Use owner/repo or GitHub URL.",
					};
				}

				// Test connection by fetching repo info
				const response = await fetch(
					`https://api.github.com/repos/${normalizedRepo}`,
					{
						headers: {
							Authorization: `token ${config.token}`,
							Accept: "application/vnd.github.v3+json",
						},
					},
				);

				if (response.ok) {
					return { success: true };
				} else {
					// Return status code for specific error handling in frontend
					return {
						success: false,
						status: response.status,
						error: response.statusText || "Connection failed",
					};
				}
			} catch (error) {
				return {
					success: false,
					error:
						error instanceof Error
							? error.message
							: "Network error during connection test",
				};
			}
		},
	);
}

/**
 * Register all repository-related handlers
 */
export function registerRepositoryHandlers(): void {
	registerCheckConnection();
	registerGetRepositories();
	registerTestConnection();
}
