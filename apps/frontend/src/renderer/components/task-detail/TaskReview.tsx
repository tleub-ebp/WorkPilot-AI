import type { Task, WorktreeStatus, WorktreeDiff, MergeConflict, MergeStats, GitConflictInfo, ImageAttachment, WorktreeCreatePRResult } from '../../../shared/types';
import {
  StagedSuccessMessage,
  WorkspaceStatus,
  QAFeedbackSection,
  DiscardDialog,
  DiffViewDialog,
  ConflictDetailsDialog,
  LoadingMessage,
  NoWorkspaceMessage,
  StagedInProjectMessage,
  CreatePRDialog
} from './task-review';

interface TaskReviewProps {
  readonly task: Task;
  readonly feedback: string;
  readonly isSubmitting: boolean;
  readonly worktreeStatus: WorktreeStatus | null;
  readonly worktreeDiff: WorktreeDiff | null;
  readonly isLoadingWorktree: boolean;
  readonly isMerging: boolean;
  readonly isDiscarding: boolean;
  readonly showDiscardDialog: boolean;
  readonly showDiffDialog: boolean;
  readonly workspaceError: string | null;
  readonly stageOnly: boolean;
  readonly stagedSuccess: string | null;
  readonly stagedProjectPath: string | undefined;
  readonly suggestedCommitMessage: string | undefined;
  readonly mergePreview: { files: string[]; conflicts: MergeConflict[]; summary: MergeStats; gitConflicts?: GitConflictInfo; uncommittedChanges?: { hasChanges: boolean; files: string[]; count: number } | null } | null;
  readonly isLoadingPreview: boolean;
  readonly showConflictDialog: boolean;
  readonly onFeedbackChange: (value: string) => void;
  readonly onReject: () => void;
  /** Image attachments for visual feedback */
  readonly images?: ImageAttachment[];
  /** Callback when images change */
  readonly onImagesChange?: (images: ImageAttachment[]) => void;
  readonly onMerge: () => void;
  readonly onDiscard: () => void;
  readonly onShowDiscardDialog: (show: boolean) => void;
  readonly onShowDiffDialog: (show: boolean) => void;
  readonly onStageOnlyChange: (value: boolean) => void;
  readonly onShowConflictDialog: (show: boolean) => void;
  readonly onLoadMergePreview: () => void;
  readonly onClose?: () => void;
  readonly onReviewAgain?: () => void;
  // PR creation
  readonly showPRDialog: boolean;
  readonly isCreatingPR: boolean;
  readonly onShowPRDialog: (show: boolean) => void;
  readonly onCreatePR: (options: { targetBranch?: string; title?: string; draft?: boolean }) => Promise<WorktreeCreatePRResult | null>;
}

/**
 * TaskReview Component
 *
 * Main component for reviewing task completion, displaying workspace status,
 * merge previews, and providing options to merge, stage, or discard changes.
 *
 * This component has been refactored into smaller, focused sub-components for better
 * maintainability. See ./task-review/ directory for individual component implementations.
 */
export function TaskReview({
  task,
  feedback,
  isSubmitting,
  worktreeStatus,
  worktreeDiff,
  isLoadingWorktree,
  isMerging,
  isDiscarding,
  showDiscardDialog,
  showDiffDialog,
  workspaceError,
  stageOnly,
  stagedSuccess,
  stagedProjectPath,
  suggestedCommitMessage,
  mergePreview,
  isLoadingPreview,
  showConflictDialog,
  onFeedbackChange,
  onReject,
  images,
  onImagesChange,
  onMerge,
  onDiscard,
  onShowDiscardDialog,
  onShowDiffDialog,
  onStageOnlyChange,
  onShowConflictDialog,
  onLoadMergePreview,
  onClose,
  onReviewAgain,
  showPRDialog,
  isCreatingPR,
  onShowPRDialog,
  onCreatePR
}: TaskReviewProps) {
  // Extract nested ternary into a clear variable
  const workspaceStatusComponent = (() => {
    if (isLoadingWorktree) {
      return <LoadingMessage />;
    }
    
    if (stagedSuccess) {
      /* Fresh staging just completed - StagedSuccessMessage is rendered above */
      return null;
    }
    
    if (task.stagedInMainProject) {
      /* Task was previously staged (persisted state) - show even if worktree still exists */
      return (
        <StagedInProjectMessage
          task={task}
          projectPath={stagedProjectPath}
          hasWorktree={worktreeStatus?.exists || false}
          onClose={onClose}
          onReviewAgain={onReviewAgain}
        />
      );
    }
    
    if (worktreeStatus?.exists) {
      /* Worktree exists but not yet staged - show staging UI */
      return (
        <WorkspaceStatus
          taskId={task.id}
          worktreeStatus={worktreeStatus}
          workspaceError={workspaceError}
          stageOnly={stageOnly}
          mergePreview={mergePreview}
          isLoadingPreview={isLoadingPreview}
          isMerging={isMerging}
          isDiscarding={isDiscarding}
          isCreatingPR={isCreatingPR}
          onShowDiffDialog={onShowDiffDialog}
          onShowDiscardDialog={onShowDiscardDialog}
          onShowConflictDialog={onShowConflictDialog}
          onLoadMergePreview={onLoadMergePreview}
          onStageOnlyChange={onStageOnlyChange}
          onMerge={onMerge}
          onShowPRDialog={onShowPRDialog}
        />
      );
    }
    
    return <NoWorkspaceMessage task={task} onClose={onClose} />;
  })();

  return (
    <div className="space-y-4">
      {/* Section divider */}
      <div className="section-divider-gradient" />

      {/* Staged Success Message */}
      {stagedSuccess && (
        <StagedSuccessMessage
          stagedSuccess={stagedSuccess}
          suggestedCommitMessage={suggestedCommitMessage}
        />
      )}

      {/* Workspace Status Section */}
      {workspaceStatusComponent}

      {/* QA Feedback Section */}
      <QAFeedbackSection
        feedback={feedback}
        isSubmitting={isSubmitting}
        onFeedbackChange={onFeedbackChange}
        onReject={onReject}
        images={images}
        onImagesChange={onImagesChange}
      />

      {/* Discard Confirmation Dialog */}
      <DiscardDialog
        open={showDiscardDialog}
        task={task}
        worktreeStatus={worktreeStatus}
        isDiscarding={isDiscarding}
        onOpenChange={onShowDiscardDialog}
        onDiscard={onDiscard}
      />

      {/* Diff View Dialog */}
      <DiffViewDialog
        open={showDiffDialog}
        worktreeDiff={worktreeDiff}
        onOpenChange={onShowDiffDialog}
      />

      {/* Conflict Details Dialog */}
      <ConflictDetailsDialog
        open={showConflictDialog}
        mergePreview={mergePreview}
        stageOnly={stageOnly}
        onOpenChange={onShowConflictDialog}
        onMerge={onMerge}
      />

      {/* Create PR Dialog */}
      <CreatePRDialog
        open={showPRDialog}
        task={task}
        worktreeStatus={worktreeStatus}
        onOpenChange={onShowPRDialog}
        onCreatePR={onCreatePR}
      />
    </div>
  );
}
