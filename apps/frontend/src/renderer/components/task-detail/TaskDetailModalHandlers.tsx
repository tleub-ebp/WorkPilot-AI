import { useTranslation } from "react-i18next";
import type { Task, WorktreeCreatePROptions } from "../../../shared/types";
import { useToast } from "../../hooks/use-toast";
import { useProjectStore } from "../../stores/project-store";
import {
	deleteTask,
	recoverStuckTask,
	startTask,
	stopTask,
	submitReview,
	useTaskStore,
} from "../../stores/task-store";

interface TaskDetailHandlersProps {
	readonly task: Task;
	readonly state: ReturnType<
		typeof import("./hooks/useTaskDetail").useTaskDetail
	>;
	readonly onOpenChange: (open: boolean) => void;
}

export function useTaskDetailHandlers({
	task,
	state,
	onOpenChange,
}: TaskDetailHandlersProps) {
	const { t } = useTranslation(["tasks"]);
	const { toast } = useToast();
	const activeProject = useProjectStore((s) => s.getActiveProject());

	const handleStartStop = async () => {
		if (state.isRunning && !state.isStuck) {
			stopTask(task.id);
		} else {
			// If task is incomplete, validate and reload plan before starting
			if (state.isIncomplete) {
				const isValid = await state.reloadPlanForIncompleteTask();
				if (!isValid) {
					toast({
						title: "Cannot Resume Task",
						description:
							"Failed to load implementation plan. Please try again or check the task files.",
						variant: "destructive",
						duration: 5000,
					});
					return;
				}
			}
			// Notify the user if the provider will change when restarting
			const projectProvider = activeProject?.settings?.provider;
			const taskProvider = task.metadata?.provider;
			if (projectProvider && taskProvider && projectProvider !== taskProvider) {
				toast({
					title: t("tasks:providerSwitch.title"),
					description: t("tasks:providerSwitch.description", {
						from: taskProvider,
						to: projectProvider,
					}),
					duration: 4000,
				});
			}
			startTask(task.id);
		}
	};

	const handleRecover = async () => {
		state.setIsRecovering(true);
		const result = await recoverStuckTask(task.id, { autoRestart: true });
		if (result.success) {
			state.setIsStuck(false);
			state.setHasCheckedRunning(false);
		}
		state.setIsRecovering(false);
	};

	const handleReject = async () => {
		// Allow submission if there's text feedback OR images attached
		if (!state.feedback.trim() && state.feedbackImages.length === 0) {
			return;
		}
		state.setIsSubmitting(true);
		await submitReview(task.id, false, state.feedback, state.feedbackImages);
		state.setIsSubmitting(false);
		state.setFeedback("");
		state.setFeedbackImages([]);
	};

	const handleDelete = async () => {
		state.setIsDeleting(true);
		state.setDeleteError(null);
		const result = await deleteTask(task.id);
		if (result.success) {
			state.setShowDeleteDialog(false);
			onOpenChange(false);
		} else {
			state.setDeleteError(result.error || "Failed to delete task");
		}
		state.setIsDeleting(false);
	};

	const handleMerge = async () => {
		state.setIsMerging(true);
		state.setWorkspaceError(null);
		try {
			const result = await globalThis.window.electronAPI.mergeWorktree(
				task.id,
				{ noCommit: state.stageOnly },
			);
			if (result.success && result.data?.success) {
				if (state.stageOnly && result.data.staged) {
					state.setWorkspaceError(null);
					state.setStagedSuccess(
						result.data.message || "Changes staged in main project",
					);
					state.setStagedProjectPath(result.data.projectPath);
					state.setSuggestedCommitMessage(result.data.suggestedCommitMessage);
				} else {
					onOpenChange(false);
				}
			} else {
				state.setWorkspaceError(
					result.data?.message || result.error || "Failed to merge changes",
				);
			}
		} catch (error) {
			state.setWorkspaceError(
				error instanceof Error ? error.message : "Unknown error during merge",
			);
		} finally {
			state.setIsMerging(false);
		}
	};

	const handleDiscard = async () => {
		state.setIsDiscarding(true);
		state.setWorkspaceError(null);
		const result = await globalThis.window.electronAPI.discardWorktree(task.id);
		if (result.success && result.data?.success) {
			state.setShowDiscardDialog(false);
			onOpenChange(false);
		} else {
			state.setWorkspaceError(
				result.data?.message || result.error || "Failed to discard changes",
			);
		}
		state.setIsDiscarding(false);
	};

	const handleCreatePR = async (options: WorktreeCreatePROptions) => {
		state.setIsCreatingPR(true);
		try {
			const result = await globalThis.window.electronAPI.createWorktreePR(
				task.id,
				options,
			);
			if (result.success && result.data) {
				// Update single task in store with new status and prUrl (more efficient than reloading all tasks)
				if (
					result.data.success &&
					result.data.prUrl &&
					!result.data.alreadyExists
				) {
					useTaskStore.getState().updateTask(task.id, {
						status: "done",
						metadata: { ...task.metadata, prUrl: result.data.prUrl },
					});
				}
				return result.data;
			}
			// Propagate IPC error; let CreatePRDialog use its i18n fallback
			return {
				success: false,
				error: result.error,
				prUrl: undefined,
				alreadyExists: false,
			};
		} catch (error) {
			// Propagate actual error message; let CreatePRDialog handle i18n fallback for undefined
			return {
				success: false,
				error: error instanceof Error ? error.message : undefined,
				prUrl: undefined,
				alreadyExists: false,
			};
		} finally {
			state.setIsCreatingPR(false);
		}
	};

	const handleClose = () => {
		// Show toast notification if task is running
		if (state.isRunning && !state.isStuck) {
			toast({
				title: t("tasks:notifications.backgroundTaskTitle"),
				description: t("tasks:notifications.backgroundTaskDescription"),
				duration: 4000,
			});
		}
		onOpenChange(false);
	};

	return {
		handleStartStop,
		handleRecover,
		handleReject,
		handleDelete,
		handleMerge,
		handleDiscard,
		handleCreatePR,
		handleClose,
	};
}
