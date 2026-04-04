/**
 * Streaming Session Button - Open the streaming viewer for a running task.
 *
 * IMPORTANT: This button must NOT send TASK_START. The task is already running
 * and streaming is enabled by default (enableStreaming ?? true in execution-handlers).
 * Sending TASK_START again would kill the running backend process and spawn a new
 * one, causing a cascade of process restarts where no process survives long enough
 * to produce output.
 *
 * This button simply opens the StreamingSession dialog which connects to the
 * existing WebSocket stream for the running task.
 */

import { Film } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogTitle,
} from "../ui/dialog";
import { StreamingSession } from "./StreamingSession";

interface StreamingSessionButtonProps {
	readonly taskId: string;
	readonly projectPath: string;
}

export function StreamingSessionButton({
	taskId,
	projectPath,
}: StreamingSessionButtonProps) {
	const [isOpen, setIsOpen] = useState(false);
	const { t } = useTranslation(["tasks", "streaming"]);

	const handleWatchLive = () => {
		setIsOpen(true);
	};

	return (
		<>
			<Button
				variant="outline"
				size="sm"
				onClick={handleWatchLive}
				className="gap-2"
			>
				<Film className="w-4 h-4" />
				{t("tasks:modal.actions.watchLive")}
			</Button>

			<Dialog open={isOpen} onOpenChange={setIsOpen}>
				<DialogContent
					className="max-w-[95vw] h-[95vh] max-h-[95vh] p-0 overflow-hidden"
					aria-describedby={undefined}
				>
					<DialogTitle className="sr-only">
						{t("streaming:dialogTitle")}
					</DialogTitle>
					<DialogDescription className="sr-only">
						{t("streaming:dialogDescription")}
					</DialogDescription>
					<StreamingSession
						sessionId={taskId}
						projectPath={projectPath}
						onClose={() => setIsOpen(false)}
					/>
				</DialogContent>
			</Dialog>
		</>
	);
}
