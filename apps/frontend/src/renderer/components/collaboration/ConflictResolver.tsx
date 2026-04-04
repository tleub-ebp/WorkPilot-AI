/**
 * ConflictResolver — Dialog for resolving concurrent modification conflicts.
 *
 * Shows two versions side-by-side and allows the user to choose
 * which version to keep, or merge manually.
 *
 * Feature 3.1 — Mode multi-utilisateurs en temps réel.
 */

import { AlertTriangle, Check, X } from "lucide-react";
import { useTranslation } from "react-i18next";
import {
	type ConflictRecord,
	useCollaborationStore,
} from "../../stores/collaboration-store";
import { Button } from "../ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
} from "../ui/dialog";

interface ConflictResolverProps {
	conflict: ConflictRecord | null;
	open: boolean;
	onClose: () => void;
}

export function ConflictResolver({
	conflict,
	open,
	onClose,
}: ConflictResolverProps) {
	const { t } = useTranslation("collaboration");
	const resolveConflict = useCollaborationStore((s) => s.resolveConflict);
	const users = useCollaborationStore((s) => s.users);

	if (!conflict) return null;

	const userBName =
		users.find((u) => u.userId === conflict.userB)?.displayName ??
		conflict.userB;

	const handleResolve = (value: unknown) => {
		resolveConflict(conflict.conflictId, value);
		onClose();
	};

	return (
		<Dialog open={open} onOpenChange={(o) => !o && onClose()}>
			<DialogContent className="sm:max-w-lg">
				<DialogHeader>
					<DialogTitle className="flex items-center gap-2">
						<AlertTriangle className="h-5 w-5 text-amber-500" />
						{t("conflicts.detected")}
					</DialogTitle>
					<DialogDescription>{t("conflicts.description")}</DialogDescription>
				</DialogHeader>

				<div className="space-y-4">
					<div className="rounded-lg border p-3 bg-amber-500/5 border-amber-500/20">
						<p className="text-sm font-medium">
							{t("conflicts.fieldConflict", { field: conflict.fieldName })}
						</p>
					</div>

					<div className="grid grid-cols-2 gap-3">
						{/* Your version */}
						<div className="space-y-2">
							<h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
								{t("conflicts.yourVersion")}
							</h4>
							<div className="rounded-lg border border-primary/30 bg-primary/5 p-3">
								<pre className="text-sm whitespace-pre-wrap wrap-break-word">
									{String(conflict.valueA ?? "")}
								</pre>
							</div>
						</div>

						{/* Their version */}
						<div className="space-y-2">
							<h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
								{t("conflicts.theirVersion", { user: userBName })}
							</h4>
							<div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3">
								<pre className="text-sm whitespace-pre-wrap wrap-break-word">
									{String(conflict.valueB ?? "")}
								</pre>
							</div>
						</div>
					</div>

					<div className="space-y-2">
						<h4 className="text-sm font-medium">
							{t("conflicts.resolution.title")}
						</h4>
						<div className="flex flex-col gap-2">
							<Button
								variant="outline"
								className="justify-start gap-2"
								onClick={() => handleResolve(conflict.valueA)}
							>
								<Check className="h-4 w-4 text-primary" />
								{t("conflicts.resolution.keepMine")}
							</Button>
							<Button
								variant="outline"
								className="justify-start gap-2"
								onClick={() => handleResolve(conflict.valueB)}
							>
								<X className="h-4 w-4 text-destructive" />
								{t("conflicts.resolution.keepTheirs")}
							</Button>
						</div>
					</div>
				</div>
			</DialogContent>
		</Dialog>
	);
}
