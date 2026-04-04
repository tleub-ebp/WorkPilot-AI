/**
 * Agent API - Aggregates all agent-related API modules
 *
 * This file serves as the main entry point for agent APIs, combining:
 * - Roadmap operations
 * - Ideation operations
 * - Insights operations
 * - Changelog operations
 * - Linear integration
 * - GitHub integration
 * - GitLab integration
 * - Azure DevOps integration
 * - Shell operations
 */

import {
	type AzureDevOpsAPI,
	createAzureDevOpsAPI,
} from "./modules/azure-devops-api";
import { type ChangelogAPI, createChangelogAPI } from "./modules/changelog-api";
import { createGitHubAPI, type GitHubAPI } from "./modules/github-api";
import { createGitLabAPI, type GitLabAPI } from "./modules/gitlab-api";
import { createIdeationAPI, type IdeationAPI } from "./modules/ideation-api";
import { createInsightsAPI, type InsightsAPI } from "./modules/insights-api";
import { createJiraAPI, type JiraAPI } from "./modules/jira-api";
import { createLinearAPI, type LinearAPI } from "./modules/linear-api";
import {
	createPromptOptimizerAPI,
	type PromptOptimizerAPI,
} from "./modules/prompt-optimizer-api";
import { createRoadmapAPI, type RoadmapAPI } from "./modules/roadmap-api";
import { createShellAPI, type ShellAPI } from "./modules/shell-api";

/**
 * Combined Agent API interface
 * Includes all operations from individual API modules
 */
export interface AgentAPI
	extends RoadmapAPI,
		IdeationAPI,
		InsightsAPI,
		ChangelogAPI,
		LinearAPI,
		GitHubAPI,
		GitLabAPI,
		AzureDevOpsAPI,
		JiraAPI,
		ShellAPI,
		PromptOptimizerAPI {}

/**
 * Creates the complete Agent API by combining all module APIs
 *
 * @returns Complete AgentAPI with all operations available
 */
export const createAgentAPI = (): AgentAPI => {
	const roadmapAPI = createRoadmapAPI();
	const ideationAPI = createIdeationAPI();
	const insightsAPI = createInsightsAPI();
	const changelogAPI = createChangelogAPI();
	const linearAPI = createLinearAPI();
	const githubAPI = createGitHubAPI();
	const gitlabAPI = createGitLabAPI();
	const azureDevOpsAPI = createAzureDevOpsAPI();
	const jiraAPI = createJiraAPI();
	const shellAPI = createShellAPI();
	const promptOptimizerAPI = createPromptOptimizerAPI();

	return {
		// Roadmap API
		...roadmapAPI,

		// Ideation API
		...ideationAPI,

		// Insights API
		...insightsAPI,

		// Changelog API
		...changelogAPI,

		// Linear Integration API
		...linearAPI,

		// GitHub Integration API
		...githubAPI,

		// GitLab Integration API
		...gitlabAPI,

		// Azure DevOps Integration API
		...azureDevOpsAPI,

		// Jira Integration API
		...jiraAPI,

		// Shell Operations API
		...shellAPI,

		// Prompt Optimizer API
		...promptOptimizerAPI,
	};
};

// Re-export individual API interfaces for consumers who need them
export type {
	RoadmapAPI,
	IdeationAPI,
	InsightsAPI,
	ChangelogAPI,
	LinearAPI,
	GitHubAPI,
	GitLabAPI,
	AzureDevOpsAPI,
	JiraAPI,
	ShellAPI,
	PromptOptimizerAPI,
};
