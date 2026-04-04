// Main export for the github-issues module
export { GitHubIssues } from "../GitHubIssues";
// Re-export components for external usage if needed
export {
	EmptyState,
	InvestigationDialog,
	IssueDetail,
	IssueList,
	IssueListHeader,
	IssueListItem,
	NotConnectedState,
} from "./components";

// Re-export hooks for external usage if needed
export {
	useGitHubInvestigation,
	useGitHubIssues,
	useIssueFiltering,
} from "./hooks";
// Re-export types for external usage if needed
export type {
	FilterState,
	GitHubIssuesProps,
	InvestigationDialogProps,
	IssueDetailProps,
	IssueListHeaderProps,
	IssueListItemProps,
	IssueListProps,
} from "./types";

// Re-export utils for external usage if needed
export { filterIssuesBySearch, formatDate } from "./utils";
