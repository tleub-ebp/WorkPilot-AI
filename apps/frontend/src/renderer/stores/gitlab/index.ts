/**
 * GitLab Stores - Focused state management for GitLab integration
 *
 * This module exports all GitLab-related stores and their utilities.
 */

// MR Review Store
export {
	initializeMRReviewListeners,
	startFollowupReview,
	startMRReview,
	useMRReviewStore,
} from "./mr-review-store";

import { initializeMRReviewListeners as _initMRReviewListeners } from "./mr-review-store";

/**
 * Initialize all global GitLab listeners.
 * Call this once at app startup.
 */
export function initializeGitLabListeners(): void {
	_initMRReviewListeners();
	// Add other global listeners here as needed
}

// Re-export types for convenience
export type {
	GitLabInvestigationResult,
	GitLabInvestigationStatus,
	GitLabMergeRequest,
	GitLabMRReviewProgress,
	GitLabMRReviewResult,
	GitLabNewCommitsCheck,
	GitLabSyncStatus,
} from "../../../shared/types";
