import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../ui/button";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuLabel,
	DropdownMenuSeparator,
	DropdownMenuTrigger,
} from "../ui/dropdown-menu";
import { CostEstimatorDialog } from "./CostEstimatorDialog";
import { PromptPreviewDialog } from "./PromptPreviewDialog";
import { RestartDialog } from "./RestartDialog";
import type { RestartMode } from "../../lib/agent-tools-api";

export interface AgentToolsButtonProps {
	readonly projectDir: string;
	readonly specDir: string;
	/** "coder" | "planner" | "qa_reviewer" | "qa_fixer" — defaults to coder. */
	readonly agentType?: string;
	/**
	 * Triggered by the cost estimator's "Start build" button. The hosting
	 * Kanban already knows how to spawn agents — this is just the user's
	 * confirmation that the cost is acceptable.
	 */
	readonly onStartBuild?: () => void;
	/**
	 * Triggered after the restart-prepare endpoint cleans up. The hosting
	 * Kanban is responsible for actually re-spawning the agent (via its
	 * existing electronAPI handlers). The mode + deleted files are passed
	 * for logging.
	 */
	readonly onRestart?: (mode: RestartMode, deleted: string[]) => void;
	/**
	 * Subset of tools to show. Defaults to all three. Useful when a card
	 * is in a state where, say, the cost estimator is irrelevant (already
	 * running) or the prompt preview makes no sense (no spec yet).
	 */
	readonly tools?: ReadonlyArray<"cost" | "restart" | "prompt">;
}

const ALL_TOOLS = ["cost", "restart", "prompt"] as const;

export function AgentToolsButton({
	projectDir,
	specDir,
	agentType = "coder",
	onStartBuild,
	onRestart,
	tools = ALL_TOOLS,
}: AgentToolsButtonProps) {
	const { t } = useTranslation("agentTools");
	const [openCost, setOpenCost] = useState(false);
	const [openRestart, setOpenRestart] = useState(false);
	const [openPrompt, setOpenPrompt] = useState(false);

	const showCost = tools.includes("cost");
	const showRestart = tools.includes("restart");
	const showPrompt = tools.includes("prompt");

	if (!showCost && !showRestart && !showPrompt) return null;

	return (
		<>
			<DropdownMenu>
				<DropdownMenuTrigger asChild>
					<Button
						variant="ghost"
						size="sm"
						className="h-7 px-2 text-xs"
						aria-label={t("menuLabel")}
					>
						{t("buttonLabel")}
					</Button>
				</DropdownMenuTrigger>
				<DropdownMenuContent align="end" className="w-56">
					<DropdownMenuLabel>{t("menuLabel")}</DropdownMenuLabel>
					<DropdownMenuSeparator />
					{showCost && (
						<DropdownMenuItem
							onSelect={(e) => {
								e.preventDefault();
								setOpenCost(true);
							}}
						>
							{t("estimateCost")}
						</DropdownMenuItem>
					)}
					{showRestart && (
						<DropdownMenuItem
							onSelect={(e) => {
								e.preventDefault();
								setOpenRestart(true);
							}}
						>
							{t("restartAgent")}
						</DropdownMenuItem>
					)}
					{showPrompt && (
						<DropdownMenuItem
							onSelect={(e) => {
								e.preventDefault();
								setOpenPrompt(true);
							}}
						>
							{t("showActivePrompt")}
						</DropdownMenuItem>
					)}
				</DropdownMenuContent>
			</DropdownMenu>

			{showCost && (
				<CostEstimatorDialog
					open={openCost}
					onOpenChange={setOpenCost}
					specDir={specDir}
					onConfirm={() => onStartBuild?.()}
				/>
			)}
			{showRestart && (
				<RestartDialog
					open={openRestart}
					onOpenChange={setOpenRestart}
					specDir={specDir}
					onRestartReady={(mode, deleted) => onRestart?.(mode, deleted)}
				/>
			)}
			{showPrompt && (
				<PromptPreviewDialog
					open={openPrompt}
					onOpenChange={setOpenPrompt}
					projectDir={projectDir}
					specDir={specDir}
					agentType={agentType}
				/>
			)}
		</>
	);
}
