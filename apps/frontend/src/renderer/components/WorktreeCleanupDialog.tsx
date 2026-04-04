import {
	AlertCircle,
	CheckCircle2,
	FolderX,
	Loader2,
	RefreshCw,
} from "lucide-react";
import { Trans, useTranslation } from "react-i18next";
import {
	AlertDialog,
	AlertDialogAction,
	AlertDialogCancel,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from "./ui/alert-dialog";

interface WorktreeCleanupDialogProps {
	readonly open: boolean;
	readonly taskTitle: string;
	readonly worktreePath?: string;
	readonly isProcessing: boolean;
	readonly error?: string;
	readonly onOpenChange: (open: boolean) => void;
	readonly onConfirm: () => void;
}

/**
 * Confirmation dialog for cleaning up worktree when marking task as done
 */
export function WorktreeCleanupDialog({
	open,
	taskTitle,
	worktreePath,
	isProcessing,
	error,
	onOpenChange,
	onConfirm,
}: WorktreeCleanupDialogProps) {
	const { t } = useTranslation(["dialogs", "common"]);

	// biome-ignore lint/suspicious/noImplicitAnyLet: type inferred from assignment
	let buttonContent;
	if (isProcessing) {
		buttonContent = (
			<>
				<Loader2 className="mr-2 h-4 w-4 animate-spin" />
				{t("dialogs:worktreeCleanup.completing")}
			</>
		);
	} else if (error) {
		buttonContent = (
			<>
				<RefreshCw className="mr-2 h-4 w-4" />
				{t("dialogs:worktreeCleanup.retry")}
			</>
		);
	} else {
		buttonContent = (
			<>
				<FolderX className="mr-2 h-4 w-4" />
				{t("dialogs:worktreeCleanup.confirm")}
			</>
		);
	}

	return (
		<AlertDialog open={open} onOpenChange={onOpenChange}>
			<AlertDialogContent>
				<AlertDialogHeader>
					<AlertDialogTitle className="flex items-center gap-2">
						{error ? (
							<AlertCircle className="h-5 w-5 text-destructive" />
						) : (
							<CheckCircle2 className="h-5 w-5 text-success" />
						)}
						{error
							? t("dialogs:worktreeCleanup.errorTitle")
							: t("dialogs:worktreeCleanup.title")}
					</AlertDialogTitle>
					<AlertDialogDescription asChild>
						<div className="text-sm text-muted-foreground space-y-3">
							{error ? (
								<p className="text-destructive">{error}</p>
							) : (
								<>
									<p>
										<Trans
											i18nKey="dialogs:worktreeCleanup.hasWorktree"
											values={{ taskTitle }}
											components={{
												strong: <strong className="text-foreground" />,
											}}
										/>
									</p>
									<p>{t("dialogs:worktreeCleanup.willDelete")}</p>
								</>
							)}
							{worktreePath && (
								<div className="bg-muted/50 rounded-lg p-3 font-mono text-xs break-all">
									{worktreePath}
								</div>
							)}
							{!error && (
								<p className="text-amber-600 dark:text-amber-500">
									{t("dialogs:worktreeCleanup.warning")}
								</p>
							)}
						</div>
					</AlertDialogDescription>
				</AlertDialogHeader>
				<AlertDialogFooter>
					<AlertDialogCancel disabled={isProcessing}>
						{t("common:buttons.cancel")}
					</AlertDialogCancel>
					<AlertDialogAction
						onClick={(e) => {
							e.preventDefault();
							onConfirm();
						}}
						disabled={isProcessing}
						className={
							error
								? "bg-primary text-primary-foreground hover:bg-primary/90"
								: "bg-success text-success-foreground hover:bg-success/90"
						}
					>
						{buttonContent}
					</AlertDialogAction>
				</AlertDialogFooter>
			</AlertDialogContent>
		</AlertDialog>
	);
}
