import {
	AlertTriangle,
	Check,
	Download,
	ExternalLink,
	Loader2,
	RefreshCw,
	X,
} from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useCliStatus } from "@/contexts/CliStatusContext";
import { cn } from "@/lib/utils";
import { useProjectStore } from "@/stores/project-store";
import { useTerminalStore } from "@/stores/terminal-store";
import { Button } from "./ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "./ui/popover";
import { Tooltip, TooltipContent, TooltipTrigger } from "./ui/tooltip";

interface CodexCliStatusBadgeProps {
	readonly className?: string;
	readonly onNavigateToTerminals?: () => void;
}

const VERSION_RECHECK_DELAY_MS = 5000;

interface CodexIconProps {
	readonly className?: string;
}

// biome-ignore lint/correctness/noUnusedVariables: variable kept for clarity
type StatusType = "loading" | "installed" | "outdated" | "not-found" | "error";

const _CHECK_INTERVAL_MS = 60 * 1000; // Re-check every 60s

/**
 * OpenAI Codex icon (simplified)
 */
function CodexIcon({ className }: CodexIconProps) {
	return (
		<>
			{/* biome-ignore lint/a11y/noSvgWithoutTitle: SVG is decorative */}
			<svg
				className={className}
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				strokeWidth="2"
				strokeLinecap="round"
				strokeLinejoin="round"
			>
				<path d="M12 2L2 7l10 5 10-5-10-5z" />
				<path d="M2 17l10 5 10-5" />
				<path d="M2 12l10 5 10-5" />
			</svg>
		</>
	);
}

/**
 * Codex CLI status badge for the sidebar.
 * Shows authentication status by checking ~/.codex/auth.json via IPC.
 */
export function CodexCliStatusBadge({
	className,
	onNavigateToTerminals,
}: CodexCliStatusBadgeProps) {
	const { t } = useTranslation(["common", "navigation"]);
	const { data, refreshCodex } = useCliStatus();
	const { codex } = data;

	const projects = useProjectStore((state) => state.projects);
	const selectedProjectId = useProjectStore((state) => state.selectedProjectId);
	const currentProject = projects.find((p) => p.id === selectedProjectId);
	const projectPath = currentProject?.path || ".";
	const addExternalTerminal = useTerminalStore(
		(state) => state.addExternalTerminal,
	);

	const [isOpen, setIsOpen] = useState(false);
	const [isUpdating, setIsUpdating] = useState(false);
	const [updateError, setUpdateError] = useState<string | null>(null);

	// Use data from context
	const status = codex.status;
	const versionInfo = codex.versionInfo;
	const lastChecked = codex.lastChecked;

	const handleRefresh = () => {
		refreshCodex();
	};

	const performUpdate = async () => {
		setIsUpdating(true);
		setUpdateError(null);
		try {
			if (!globalThis.electronAPI?.createTerminal) {
				setUpdateError("Terminal not available");
				return;
			}

			const terminalId = `codex-cli-update-${Date.now()}`;
			const terminalResult = await globalThis.electronAPI.createTerminal({
				id: terminalId,
				cwd: projectPath,
				cols: 80,
				rows: 25,
				projectPath: projectPath,
			});

			if (!terminalResult.success) {
				setUpdateError(terminalResult.error || "Failed to open terminal");
				return;
			}

			addExternalTerminal(terminalId, "Codex Update", projectPath, projectPath);

			setIsOpen(false);
			if (onNavigateToTerminals) {
				onNavigateToTerminals();
			}

			await new Promise((resolve) => setTimeout(resolve, 300));
			globalThis.electronAPI.sendTerminalInput(
				terminalId,
				"pnpm install -g @openai/codex@latest\n",
			);

			setTimeout(() => refreshCodex(), VERSION_RECHECK_DELAY_MS);
			setTimeout(() => refreshCodex(), VERSION_RECHECK_DELAY_MS * 3);
			setTimeout(() => refreshCodex(), VERSION_RECHECK_DELAY_MS * 6);
		} catch (err) {
			console.error("Failed to update Codex CLI:", err);
			setUpdateError(err instanceof Error ? err.message : "Update failed");
		} finally {
			setIsUpdating(false);
		}
	};

	const getStatusColor = () => {
		switch (status) {
			case "installed":
				return "bg-green-500";
			case "outdated":
				return "bg-yellow-500";
			case "not-found":
				return "bg-muted-foreground";
			case "error":
				return "bg-destructive";
			default:
				return "bg-muted-foreground";
		}
	};

	const getStatusIcon = () => {
		switch (status) {
			case "installed":
				return <Check className="h-3 w-3" />;
			case "outdated":
				return <AlertTriangle className="h-3 w-3" />;
			case "not-found":
				return <X className="h-3 w-3" />;
			case "error":
				return <AlertTriangle className="h-3 w-3" />;
			default:
				return <Loader2 className="h-3 w-3 animate-spin" />;
		}
	};

	const getTooltipText = () => {
		switch (status) {
			case "loading":
				return "Vérification Codex CLI...";
			case "installed":
				return versionInfo?.installed
					? `Codex CLI (${versionInfo.installed})`
					: "Codex CLI installé";
			case "outdated":
				return `Codex CLI (${versionInfo?.installed}) - mise à jour disponible`;
			case "not-found":
				return "Codex CLI non trouvé";
			case "error":
				return "Erreur Codex CLI";
			default:
				return "Codex CLI";
		}
	};

	return (
		<Popover open={isOpen} onOpenChange={setIsOpen}>
			<Tooltip>
				<TooltipTrigger asChild>
					<PopoverTrigger asChild>
						<Button
							variant="ghost"
							size="sm"
							className={cn(
								"w-full justify-start gap-2 text-xs",
								status === "not-found" || status === "error"
									? "text-muted-foreground"
									: "",
								className,
							)}
						>
							<div className="relative">
								<CodexIcon className="h-4 w-4" />
								<span
									className={cn(
										"absolute -bottom-0.5 -right-0.5 h-2 w-2 rounded-full",
										getStatusColor(),
									)}
								/>
							</div>
							<span className="truncate">
								Codex
								{versionInfo?.installed ? ` (${versionInfo.installed})` : ""}
							</span>
							{status === "not-found" && (
								<span className="ml-auto text-[10px] bg-muted text-muted-foreground px-1.5 py-0.5 rounded">
									N/A
								</span>
							)}
						</Button>
					</PopoverTrigger>
				</TooltipTrigger>
				<TooltipContent side="right">{getTooltipText()}</TooltipContent>
			</Tooltip>

			<PopoverContent side="right" align="end" className="w-64">
				<div className="space-y-3">
					{/* Header */}
					<div className="flex items-center gap-2">
						<div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
							<CodexIcon className="h-4 w-4 text-primary" />
						</div>
						<div>
							<h4 className="text-sm font-medium">OpenAI Codex CLI</h4>
							<p className="text-xs text-muted-foreground flex items-center gap-1">
								{getStatusIcon()}
								{status === "installed" && "Connecté"}
								{status === "not-found" && "Non configuré"}
								{status === "loading" && "Vérification..."}
								{status === "error" && "Erreur"}
							</p>
						</div>
					</div>

					{/* Auth info */}
					{status === "installed" && versionInfo?.installed && (
						<div className="text-xs space-y-1 p-2 bg-muted rounded-md">
							<div className="flex justify-between">
								<span className="text-muted-foreground">Compte :</span>
								<span className="font-medium truncate ml-2">
									{versionInfo?.installed}
								</span>
							</div>
							{lastChecked && (
								<div className="flex justify-between text-muted-foreground">
									<span>Vérifié :</span>
									<span>{lastChecked.toLocaleTimeString()}</span>
								</div>
							)}
						</div>
					)}

					{/* Not configured notice */}
					{status === "not-found" && (
						<div className="text-xs p-2 bg-muted/50 rounded-md text-muted-foreground">
							<p>
								Lancez{" "}
								<code className="font-mono bg-muted px-1 rounded">codex</code>{" "}
								dans un terminal pour vous authentifier via OAuth.
							</p>
							<p className="mt-1">
								Configurez dans Paramètres → OpenAI → OAuth / Codex.
							</p>
						</div>
					)}

					{/* Actions */}
					<div className="flex gap-2">
						{status === "installed" && (
							<Button
								size="sm"
								className="flex-1 gap-1"
								onClick={performUpdate}
								disabled={isUpdating}
							>
								{isUpdating ? (
									<Loader2 className="h-3 w-3 animate-spin" />
								) : (
									<Download className="h-3 w-3" />
								)}
								{t("common:update", "Mettre à jour")}
							</Button>
						)}
						<Button
							variant="outline"
							size="sm"
							className={cn(
								"gap-1",
								status !== "installed" && "flex-1",
							)}
							onClick={() => {
								handleRefresh();
							}}
							disabled={status === "loading"}
						>
							<RefreshCw
								className={cn(
									"h-3 w-3",
									status === "loading" && "animate-spin",
								)}
							/>
							{t("common:refresh", "Rafraîchir")}
						</Button>
					</div>

					{updateError && (
						<div className="text-xs p-2 bg-destructive/10 text-destructive rounded-md flex items-center gap-2">
							<AlertTriangle className="h-3 w-3 shrink-0" />
							<span>{updateError}</span>
						</div>
					)}

					{/* Docs link */}
					<Button
						variant="link"
						size="sm"
						className="w-full text-xs text-muted-foreground gap-1"
						onClick={() =>
							globalThis.electronAPI?.openExternal?.(
								"https://github.com/openai/codex",
							)
						}
					>
						Voir la documentation Codex CLI
						<ExternalLink className="h-3 w-3" />
					</Button>
				</div>
			</PopoverContent>
		</Popover>
	);
}
