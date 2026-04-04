// Main export for the gitlab-issues module
export { GitLabIssues } from "../GitLabIssues";
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
	useGitLabInvestigation,
	useGitLabIssues,
	useIssueFiltering,
} from "./hooks";
// Re-export types for external usage if needed
export type {
	FilterState,
	GitLabIssuesProps,
	InvestigationDialogProps,
	IssueDetailProps,
	IssueListHeaderProps,
	IssueListItemProps,
	IssueListProps,
} from "./types";

// Re-export utils for external usage if needed
export { filterIssuesBySearch, formatDate } from "./utils";
