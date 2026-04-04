/**
 * MCP Server Card
 *
 * Displays a single MCP server in the marketplace catalog grid.
 * Shows name, description, stats, and install/uninstall actions.
 */

import {
	BadgeCheck,
	ChevronDown,
	ChevronUp,
	Download,
	ExternalLink,
	Eye,
	EyeOff,
	Globe,
	Loader2,
	Star,
	Terminal,
	Trash2,
} from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { McpMarketplaceServer } from "../../../shared/types/mcp-marketplace";
import {
	installMarketplaceServer,
	uninstallMarketplaceServer,
	useMcpMarketplaceStore,
} from "../../stores/mcp-marketplace-store";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "../ui/dialog";
import { Input } from "../ui/input";
import { Label } from "../ui/label";

interface McpServerCardProps {
	readonly server: McpMarketplaceServer;
}

function formatDownloads(n: number): string {
	if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
	if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
	return String(n);
}

export function McpServerCard({ server }: McpServerCardProps) {
	const { t } = useTranslation(["common"]);
	const { isServerInstalled, isInstalling } = useMcpMarketplaceStore();

	const installed = isServerInstalled(server.id);
	const installing = isInstalling === server.id;

	const [showInstallDialog, setShowInstallDialog] = useState(false);
	const [showDetails, setShowDetails] = useState(false);
	const [envVars, setEnvVars] = useState<Record<string, string>>({});
	const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});

	const hasRequiredEnvVars = (server.requiredEnvVars?.length ?? 0) > 0;

	const handleInstallClick = () => {
		if (hasRequiredEnvVars) {
			// Initialize env vars with empty values
			const initial: Record<string, string> = {};
			server.requiredEnvVars?.forEach((v) => {
				initial[v.name] = "";
			});
			server.optionalEnvVars?.forEach((v) => {
				initial[v.name] = "";
			});
			setEnvVars(initial);
			setShowInstallDialog(true);
		} else {
			installMarketplaceServer(server.id);
		}
	};

	const handleConfirmInstall = async () => {
		const success = await installMarketplaceServer(server.id, envVars);
		if (success) {
			setShowInstallDialog(false);
		}
	};

	const handleUninstall = () => {
		uninstallMarketplaceServer(server.id);
	};

	const canInstall =
		!hasRequiredEnvVars ||
		server.requiredEnvVars?.every((v) => envVars[v.name]?.trim());

	return (
		<>
			<div className="group relative flex flex-col rounded-xl border border-border bg-card hover:border-primary/40 hover:shadow-md transition-all duration-200 overflow-hidden">
				{/* Card header with color accent */}
				<div
					className="h-1.5 w-full"
					style={{ backgroundColor: server.color }}
				/>

				<div className="flex flex-col flex-1 p-4">
					{/* Top row: icon + name + badges */}
					<div className="flex items-start gap-3 mb-3">
						<div
							className="shrink-0 flex items-center justify-center w-10 h-10 rounded-lg text-white text-sm font-bold"
							style={{ backgroundColor: server.color }}
						>
							{server.name.charAt(0)}
						</div>
						<div className="flex-1 min-w-0">
							<div className="flex items-center gap-1.5">
								<h3 className="font-semibold text-sm truncate">
									{server.name}
								</h3>
								{server.verified && (
									<BadgeCheck className="h-4 w-4 text-blue-500 shrink-0" />
								)}
							</div>
							<p className="text-xs text-muted-foreground truncate mt-0.5">
								{server.tagline}
							</p>
						</div>
					</div>

					{/* Stats row */}
					<div className="flex items-center gap-3 text-xs text-muted-foreground mb-3">
						<span className="flex items-center gap-1">
							<Download className="h-3 w-3" />
							{formatDownloads(server.downloads)}
						</span>
						<span className="flex items-center gap-1">
							<Star className="h-3 w-3 fill-amber-400 text-amber-400" />
							{server.rating.toFixed(1)}
						</span>
						<span className="flex items-center gap-1">
							{server.transport === "stdio" ? (
								<Terminal className="h-3 w-3" />
							) : (
								<Globe className="h-3 w-3" />
							)}
							{server.transport}
						</span>
						<span className="ml-auto text-[10px] opacity-60">
							v{server.version}
						</span>
					</div>

					{/* Tools preview */}
					<div className="flex flex-wrap gap-1 mb-3">
						{server.tools.slice(0, 3).map((tool) => (
							<Badge
								key={tool.name}
								variant="secondary"
								className="text-[10px] px-1.5 py-0"
							>
								{tool.name}
							</Badge>
						))}
						{server.tools.length > 3 && (
							<Badge variant="outline" className="text-[10px] px-1.5 py-0">
								+{server.tools.length - 3}
							</Badge>
						)}
					</div>

					{/* Expandable details */}
					<button
						type="button"
						onClick={() => setShowDetails(!showDetails)}
						className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground mb-2"
					>
						{showDetails ? (
							<ChevronUp className="h-3 w-3" />
						) : (
							<ChevronDown className="h-3 w-3" />
						)}
						{showDetails
							? t("mcpMarketplace.hideDetails")
							: t("mcpMarketplace.showDetails")}
					</button>

					{showDetails && (
						<div className="text-xs text-muted-foreground mb-3 space-y-2">
							<p>{server.description}</p>
							<div className="flex flex-wrap gap-1">
								{server.tags.map((tag) => (
									<span
										key={tag}
										className="text-[10px] bg-muted px-1.5 py-0.5 rounded"
									>
										{tag}
									</span>
								))}
							</div>
							{server.requiredEnvVars && server.requiredEnvVars.length > 0 && (
								<div>
									<span className="font-medium text-foreground">
										{t("mcpMarketplace.requiredConfig")}:
									</span>
									<ul className="list-disc list-inside mt-1">
										{server.requiredEnvVars.map((v) => (
											<li key={v.name}>{v.label}</li>
										))}
									</ul>
								</div>
							)}
							<div className="flex gap-2">
								{server.homepage && (
									<a
										href={server.homepage}
										target="_blank"
										rel="noopener noreferrer"
										className="flex items-center gap-1 text-primary hover:underline"
									>
										<ExternalLink className="h-3 w-3" />
										{t("mcpMarketplace.homepage")}
									</a>
								)}
							</div>
						</div>
					)}

					{/* Action buttons */}
					<div className="mt-auto pt-2">
						{installed ? (
							<div className="flex gap-2">
								<Badge variant="default" className="flex-1 justify-center py-1">
									{t("mcpMarketplace.installedBadge")}
								</Badge>
								<Button
									variant="ghost"
									size="icon"
									className="h-7 w-7 text-destructive hover:text-destructive"
									onClick={handleUninstall}
									title={t("mcpMarketplace.uninstall")}
								>
									<Trash2 className="h-3.5 w-3.5" />
								</Button>
							</div>
						) : (
							<Button
								className="w-full h-8 text-xs"
								onClick={handleInstallClick}
								disabled={installing}
							>
								{installing ? (
									<>
										<Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
										{t("mcpMarketplace.installing")}
									</>
								) : (
									<>
										<Download className="h-3.5 w-3.5 mr-1.5" />
										{t("mcpMarketplace.install")}
									</>
								)}
							</Button>
						)}
					</div>
				</div>
			</div>

			{/* Install Configuration Dialog */}
			<Dialog open={showInstallDialog} onOpenChange={setShowInstallDialog}>
				<DialogContent className="sm:max-w-[500px]">
					<DialogHeader>
						<DialogTitle className="flex items-center gap-2">
							<div
								className="flex items-center justify-center w-8 h-8 rounded-lg text-white text-sm font-bold"
								style={{ backgroundColor: server.color }}
							>
								{server.name.charAt(0)}
							</div>
							{t("mcpMarketplace.installDialog.title", { name: server.name })}
						</DialogTitle>
						<DialogDescription>
							{t("mcpMarketplace.installDialog.description")}
						</DialogDescription>
					</DialogHeader>

					<div className="space-y-4 py-2">
						{/* Required env vars */}
						{server.requiredEnvVars?.map((envVar) => (
							<div key={envVar.name} className="space-y-1.5">
								<Label className="text-sm flex items-center gap-1">
									{envVar.label}
									{envVar.required && (
										<span className="text-destructive">*</span>
									)}
								</Label>
								<p className="text-xs text-muted-foreground">
									{envVar.description}
								</p>
								<div className="flex gap-2">
									<div className="relative flex-1">
										<Input
											type={
												envVar.secret && !showSecrets[envVar.name]
													? "password"
													: "text"
											}
											placeholder={envVar.placeholder}
											value={envVars[envVar.name] || ""}
											onChange={(e) =>
												setEnvVars((prev) => ({
													...prev,
													[envVar.name]: e.target.value,
												}))
											}
											className="h-9 pr-9"
										/>
										{envVar.secret && (
											<button
												type="button"
												onClick={() =>
													setShowSecrets((prev) => ({
														...prev,
														[envVar.name]: !prev[envVar.name],
													}))
												}
												className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
											>
												{showSecrets[envVar.name] ? (
													<EyeOff className="h-4 w-4" />
												) : (
													<Eye className="h-4 w-4" />
												)}
											</button>
										)}
									</div>
									{envVar.helpUrl && (
										<Button
											variant="outline"
											size="icon"
											className="h-9 w-9 shrink-0"
											asChild
										>
											<a
												href={envVar.helpUrl}
												target="_blank"
												rel="noopener noreferrer"
											>
												<ExternalLink className="h-4 w-4" />
											</a>
										</Button>
									)}
								</div>
							</div>
						))}

						{/* Optional env vars */}
						{server.optionalEnvVars && server.optionalEnvVars.length > 0 && (
							<>
								<div className="text-xs font-medium text-muted-foreground uppercase tracking-wider pt-2">
									{t("mcpMarketplace.installDialog.optional")}
								</div>
								{server.optionalEnvVars.map((envVar) => (
									<div key={envVar.name} className="space-y-1.5">
										<Label className="text-sm">{envVar.label}</Label>
										<Input
											type={envVar.secret ? "password" : "text"}
											placeholder={envVar.placeholder}
											value={envVars[envVar.name] || ""}
											onChange={(e) =>
												setEnvVars((prev) => ({
													...prev,
													[envVar.name]: e.target.value,
												}))
											}
											className="h-9"
										/>
									</div>
								))}
							</>
						)}
					</div>

					<DialogFooter>
						<Button
							variant="outline"
							onClick={() => setShowInstallDialog(false)}
						>
							{t("common:cancel")}
						</Button>
						<Button
							onClick={handleConfirmInstall}
							disabled={!canInstall || installing}
						>
							{installing ? (
								<>
									<Loader2 className="h-4 w-4 mr-2 animate-spin" />
									{t("mcpMarketplace.installing")}
								</>
							) : (
								<>
									<Download className="h-4 w-4 mr-2" />
									{t("mcpMarketplace.install")}
								</>
							)}
						</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>
		</>
	);
}
