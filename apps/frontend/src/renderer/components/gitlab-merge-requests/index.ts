/**
 * GitLab Merge Requests UI Components
 *
 * Integrated into sidebar and App.tsx.
 * Accessible via 'gitlab-merge-requests' view with shortcut 'M'.
 */

// Re-export components for external usage if needed
export {
	CreateMergeRequestDialog,
	MergeRequestItem,
	MergeRequestList,
} from "./components";
// Main export for the gitlab-merge-requests module
export { GitLabMergeRequests } from "./GitLabMergeRequests";
