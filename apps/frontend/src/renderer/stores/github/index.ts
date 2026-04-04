/**
 * GitHub Stores - Focused state management for GitHub integration
 *
 * This module exports all GitHub-related stores and their utilities.
 * Previously managed by a single monolithic store, now split into:
 * - Issues Store: Issue data and filtering
 * - PR Review Store: Pull request review state and progress
 * - Investigation Store: Issue investigation workflow
 * - Sync Status Store: GitHub connection status
 */

// Issues Store
export {
	type IssueFilterState,
	importGitHubIssues,
	loadAllGitHubIssues,
	loadGitHubIssues,
	loadMoreGitHubIssues,
	useIssuesStore,
} from "./issues-store";

// PR Review Store
export {
	initializePRReviewListeners,
	startFollowupReview,
	startPRReview,
	usePRReviewStore,
} from "./pr-review-store";

import { initializePRReviewListeners as _initPRReviewListeners } from "./pr-review-store";

// Investigation Store
export {
	investigateGitHubIssue,
	useInvestigationStore,
} from "./investigation-store";

// Sync Status Store
export {
	checkGitHubConnection,
	useSyncStatusStore,
} from "./sync-status-store";

/**
 * Initialize all global GitHub listeners.
 * Call this once at app startup.
 */
export function initializeGitHubListeners(): void {
	_initPRReviewListeners();
	// Add other global listeners here as needed
}

// Re-export types for convenience
export type {
	PRReviewProgress,
	PRReviewResult,
} from "../../../preload/api/modules/github-api";

export type {
	GitHubInvestigationResult,
	GitHubInvestigationStatus,
	GitHubIssue,
	GitHubSyncStatus,
} from "../../../shared/types";
