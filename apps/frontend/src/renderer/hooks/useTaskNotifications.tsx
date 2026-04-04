import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import type { TaskStatus } from "../../shared/types";
import type { SidebarView } from "../components/Sidebar";
import { ToastAction } from "../components/ui/toast";
import { useTaskStore } from "../stores/task-store";
import { toast } from "./use-toast";

const NOTIFY_STATUSES: Set<TaskStatus> = new Set([
	"human_review",
	"done",
	"pr_created",
	"error",
]);

interface UseTaskNotificationsOptions {
	onNavigate: (view: SidebarView) => void;
}

/**
 * Registers a global listener for task status changes and shows toast
 * notifications when a task reaches a terminal state (human_review, done,
 * pr_created, error). The toast includes a "View" action that navigates to
 * the Kanban board and spotlights the task.
 */
export function useTaskNotifications({
	onNavigate,
}: UseTaskNotificationsOptions): void {
	const { t } = useTranslation(["tasks"]);

	// Refs to avoid stale closures inside the listener
	const tRef = useRef(t);
	const onNavigateRef = useRef(onNavigate);
	tRef.current = t;
	onNavigateRef.current = onNavigate;

	const registerTaskStatusChangeListener = useTaskStore(
		(state) => state.registerTaskStatusChangeListener,
	);

	useEffect(() => {
		const unregister = registerTaskStatusChangeListener(
			(taskId, _oldStatus, newStatus) => {
				if (!NOTIFY_STATUSES.has(newStatus)) return;

				const task = useTaskStore
					.getState()
					.tasks.find((task) => task.id === taskId || task.specId === taskId);
				const taskTitle = task?.title ?? taskId;

				const translate = tRef.current;

				const handleView = () => {
					onNavigateRef.current("kanban");
					useTaskStore.getState().jumpToTask(taskId);
				};

				const viewLabel = translate("statusNotifications.view");

				toast({
					title: translate(`statusNotifications.${newStatus}.title`),
					description: taskTitle,
					variant: newStatus === "error" ? "destructive" : "default",
					onClick: handleView,
					action: (
						<ToastAction
							altText={viewLabel}
							onClick={(e) => {
								e.stopPropagation();
								handleView();
							}}
						>
							{viewLabel}
						</ToastAction>
					),
				});
			},
		);

		return unregister;
	}, [registerTaskStatusChangeListener]);
}
