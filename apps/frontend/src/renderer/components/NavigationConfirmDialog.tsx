import type { Task } from "@shared/types/task";
import { PauseCircle, PlayCircle, Square } from "lucide-react";
import { useTranslation } from "react-i18next";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
} from "@/components/ui";

interface NavigationConfirmDialogProps {
	open: boolean;
	runningTask: Task | null;
	onContinue: () => void;
	onStop: () => void;
	onPause: () => void;
}

export function NavigationConfirmDialog({
	open,
	runningTask,
	onContinue,
	onStop,
	onPause,
}: NavigationConfirmDialogProps) {
	const { t } = useTranslation("common");

	return (
		<Dialog
			open={open}
			onOpenChange={(isOpen) => {
				if (!isOpen) onContinue();
			}}
		>
			<DialogContent hideCloseButton className="max-w-md">
				<DialogHeader>
					<DialogTitle>{t("navigationConfirm.title")}</DialogTitle>
					<DialogDescription>
						{t("navigationConfirm.description")}
					</DialogDescription>
				</DialogHeader>

				{runningTask && (
					<p className="text-sm font-medium text-foreground mt-2 px-1">
						{t("navigationConfirm.taskLabel", { taskTitle: runningTask.title })}
					</p>
				)}

				<div className="flex flex-col gap-2 mt-4">
					<button
						type="button"
						onClick={onContinue}
						className="flex items-start gap-3 rounded-lg border border-border p-3 text-left hover:bg-accent transition-colors"
					>
						<PlayCircle className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
						<div>
							<p className="text-sm font-medium text-foreground">
								{t("navigationConfirm.continueTask")}
							</p>
							<p className="text-xs text-muted-foreground">
								{t("navigationConfirm.continueTaskDescription")}
							</p>
						</div>
					</button>

					<button
						type="button"
						onClick={onPause}
						className="flex items-start gap-3 rounded-lg border border-border p-3 text-left hover:bg-accent transition-colors"
					>
						<PauseCircle className="mt-0.5 h-5 w-5 shrink-0 text-amber-500" />
						<div>
							<p className="text-sm font-medium text-foreground">
								{t("navigationConfirm.pauseTask")}
							</p>
							<p className="text-xs text-muted-foreground">
								{t("navigationConfirm.pauseTaskDescription")}
							</p>
						</div>
					</button>

					<button
						type="button"
						onClick={onStop}
						className="flex items-start gap-3 rounded-lg border border-border p-3 text-left hover:bg-accent transition-colors"
					>
						<Square className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
						<div>
							<p className="text-sm font-medium text-destructive">
								{t("navigationConfirm.stopTask")}
							</p>
							<p className="text-xs text-muted-foreground">
								{t("navigationConfirm.stopTaskDescription")}
							</p>
						</div>
					</button>
				</div>
			</DialogContent>
		</Dialog>
	);
}
