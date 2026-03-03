import type { GitHubIssue, GitHubInvestigationResult } from '../../../../shared/types';
import type { AutoFixConfig, AutoFixQueueItem } from '../../../../preload/api/modules/github-api';

export type FilterState = 'open' | 'closed' | 'all';

export interface GitHubIssuesProps {
  readonly onOpenSettings?: () => void;
  /** Navigate to view a task in the kanban board */
  readonly onNavigateToTask?: (taskId: string) => void;
}

export interface IssueListItemProps {
  readonly issue: GitHubIssue;
  readonly isSelected: boolean;
  readonly onClick: () => void;
  readonly onInvestigate: () => void;
}

export interface IssueDetailProps {
  readonly issue: GitHubIssue;
  readonly onInvestigate: () => void;
  readonly investigationResult: GitHubInvestigationResult | null;
  /** ID of existing task linked to this issue (from metadata.githubIssueNumber) */
  readonly linkedTaskId?: string;
  /** Handler to navigate to view the linked task */
  readonly onViewTask?: (taskId: string) => void;
  /** Project ID for auto-fix functionality */
  readonly projectId?: string;
  /** Auto-fix configuration */
  readonly autoFixConfig?: AutoFixConfig | null;
  /** Auto-fix queue item for this issue */
  readonly autoFixQueueItem?: AutoFixQueueItem | null;
}

export interface InvestigationDialogProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly selectedIssue: GitHubIssue | null;
  readonly investigationStatus: {
    readonly phase: string;
    readonly progress: number;
    readonly message: string;
    readonly error?: string;
  };
  readonly onStartInvestigation: (selectedCommentIds: number[]) => void;
  readonly onClose: () => void;
  readonly projectId?: string;
}

export interface IssueListHeaderProps {
  readonly repoFullName: string;
  readonly openIssuesCount: number;
  readonly isLoading: boolean;
  readonly searchQuery: string;
  readonly filterState: FilterState;
  readonly onSearchChange: (query: string) => void;
  readonly onFilterChange: (state: FilterState) => void;
  readonly onRefresh: () => void;
  // Auto-fix toggle (reactive - for new issues)
  readonly autoFixEnabled?: boolean;
  readonly autoFixRunning?: boolean;
  readonly autoFixProcessing?: number; // Number of issues being processed
  readonly onAutoFixToggle?: (enabled: boolean) => void;
  // Analyze & Group (proactive - for existing issues)
  readonly onAnalyzeAndGroup?: () => void;
  readonly isAnalyzing?: boolean;
}

export interface IssueListProps {
  readonly issues: GitHubIssue[];
  readonly selectedIssueNumber: number | null;
  readonly isLoading: boolean;
  readonly isLoadingMore?: boolean;
  readonly hasMore?: boolean;
  readonly error: string | null;
  readonly onSelectIssue: (issueNumber: number) => void;
  readonly onInvestigate: (issue: GitHubIssue) => void;
  readonly onLoadMore?: () => void;
}

export interface EmptyStateProps {
  readonly searchQuery?: string;
  readonly icon?: React.ComponentType<{ className?: string }>;
  readonly message: string;
}

export interface NotConnectedStateProps {
  readonly error: string | null;
  readonly onOpenSettings?: () => void;
}
