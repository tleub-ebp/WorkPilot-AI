/**
 * Usage Indicator Agnostic - Provider-agnostic usage display component
 *
 * This component displays usage data for any provider with any authentication method
 * in a completely unified way, abstracting all provider-specific details.
 */

import { formatTimeRemaining } from "@shared/utils/format-time";
import {
	Activity,
	AlertCircle,
	ChevronRight,
	Clock,
	LogIn,
	RefreshCw,
	TrendingUp,
} from "lucide-react";
import React, { useCallback, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import type { AppSection } from "@/components/settings/AppSettings";
import { useAgnosticUsage } from "../hooks/useAgnosticUsage";
import { Popover, PopoverContent, PopoverTrigger } from "./ui/popover";
import {
	Tooltip,
	TooltipContent,
	TooltipProvider,
	TooltipTrigger,
} from "./ui/tooltip";

// Seuils pour le codage couleur
const THRESHOLD_CRITICAL = 95;
const THRESHOLD_WARNING = 91;
const THRESHOLD_ELEVATED = 71;

/**
 * Obtenir la classe de couleur pour les barres d'usage
 */
function getBarColorClass(percent: number): string {
	if (percent >= THRESHOLD_CRITICAL) return "bg-red-500";
	if (percent >= THRESHOLD_WARNING) return "bg-orange-500";
	if (percent >= THRESHOLD_ELEVATED) return "bg-yellow-500";
	return "bg-green-500";
}

interface UsageIndicatorAgnosticProps {
	selectedProvider?: string;
}

export function UsageIndicatorAgnostic({
	selectedProvider,
}: UsageIndicatorAgnosticProps = {}) {
	const { t } = useTranslation(["common"]);
	const {
		usageData,
		activeCredential,
		isLoading,
		isAvailable,
		error,
		providerConfig,
		getColorClass,
		getInitials,
		needsReauth,
		limitingPercent,
		sessionPercent,
		periodicPercent,
		refreshUsageData,
	} = useAgnosticUsage(selectedProvider);

	// États UI locaux
	const [isOpen, setIsOpen] = useState(false);
	const [isPinned, setIsPinned] = useState(false);
	const [isRefreshing, setIsRefreshing] = useState(false);
	const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null);

	/**
	 * Naviguer vers les paramètres des comptes
	 */
	const handleOpenAccounts = useCallback((e: React.MouseEvent) => {
		e.preventDefault();
		e.stopPropagation();
		setIsOpen(false);
		setIsPinned(false);
		setTimeout(() => {
			const event = new CustomEvent<AppSection>("open-app-settings", {
				detail: "accounts",
			});
			globalThis.dispatchEvent(event);
		}, 100);
	}, []);

	/**
	 * Rafraîchir les données manuellement
	 */
	const handleRefresh = useCallback(
		async (e: React.MouseEvent) => {
			e.preventDefault();
			e.stopPropagation();

			setIsRefreshing(true);
			try {
				await refreshUsageData();
			} catch (err) {
				console.error("[UsageIndicatorAgnostic] Failed to refresh:", err);
			} finally {
				setIsRefreshing(false);
			}
		},
		[refreshUsageData],
	);

	/**
	 * Gérer le survol
	 */
	const handleMouseEnter = useCallback(() => {
		if (isPinned) return;
		if (hoverTimeoutRef.current) {
			clearTimeout(hoverTimeoutRef.current);
			hoverTimeoutRef.current = null;
		}
		hoverTimeoutRef.current = setTimeout(() => setIsOpen(true), 150);
	}, [isPinned]);

	/**
	 * Gérer la sortie de souris
	 */
	const handleMouseLeave = useCallback(() => {
		if (isPinned) return;
		if (hoverTimeoutRef.current) {
			clearTimeout(hoverTimeoutRef.current);
			hoverTimeoutRef.current = null;
		}
		hoverTimeoutRef.current = setTimeout(() => setIsOpen(false), 300);
	}, [isPinned]);

	/**
	 * Gérer le clic
	 */
	const handleTriggerClick = useCallback(
		(e: React.MouseEvent) => {
			e.preventDefault();
			if (isPinned) {
				setIsPinned(false);
				setIsOpen(false);
			} else {
				setIsPinned(true);
				setIsOpen(true);
			}
		},
		[isPinned],
	);

	/**
	 * Gérer le changement de popover
	 */
	const handleOpenChange = useCallback((open: boolean) => {
		if (!open) {
			setIsOpen(false);
			setIsPinned(false);
		}
	}, []);

	/**
	 * Obtenir l'icône à afficher
	 */
	const getIcon = () => {
		if (needsReauth) return AlertCircle;
		if (error) return AlertCircle;
		if (limitingPercent >= THRESHOLD_WARNING) return AlertCircle;
		if (limitingPercent >= THRESHOLD_ELEVATED) return TrendingUp;

		// Use provider-specific icon if available
		const iconMap: Record<string, React.ComponentType<any>> = {
			Activity,
			AlertCircle,
			ChevronRight,
			Clock,
			LogIn,
			RefreshCw,
			TrendingUp,
		};
		const IconComponent = iconMap[providerConfig.icon] || Activity;
		return IconComponent;
	};

	/**
	 * Obtenir le contenu principal du badge
	 */
	const getBadgeContent = () => {
		if (needsReauth) {
			return (
				<span
					className="text-xs font-semibold text-red-500"
					title={t("common:usage.needsReauth")}
				>
					!
				</span>
			);
		}

		if (error) {
			return (
				<span className="text-xs font-semibold text-orange-500" title="Error">
					!
				</span>
			);
		}

		// Use provider-specific formatting
		return (
			<div className="flex items-center gap-0.5 text-xs font-semibold font-mono">
				<span className={getColorClass("text")} title="Session">
					{Math.round(sessionPercent)}
				</span>
				<span className="text-muted-foreground/50">│</span>
				<span className={getColorClass("text")} title="Periodic">
					{Math.round(periodicPercent)}
				</span>
			</div>
		);
	};

	/**
	 * Obtenir le temps de reset formaté
	 */
	const getFormattedResetTime = (timestamp?: string) => {
		if (!timestamp) return undefined;
		return formatTimeRemaining(timestamp, t);
	};

	// Nettoyer le timeout
	React.useEffect(() => {
		return () => {
			if (hoverTimeoutRef.current) {
				clearTimeout(hoverTimeoutRef.current);
			}
		};
	}, []);

	// État de chargement
	if (isLoading) {
		return (
			<div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border bg-muted/50 text-muted-foreground">
				<Activity className="h-3.5 w-3.5 motion-safe:animate-pulse" />
				<span className="text-xs font-semibold">
					{t("common:usage.loading")}
				</span>
			</div>
		);
	}

	// État indisponible
	if (!isAvailable || !usageData) {
		return (
			<TooltipProvider delayDuration={200}>
				<Tooltip>
					<TooltipTrigger asChild>
						<button
							type="button"
							className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border bg-muted/50 text-muted-foreground"
						>
							<Activity className="h-3.5 w-3.5" />
							<span className="text-xs font-semibold">
								{t("common:usage.notAvailable")}
							</span>
						</button>
					</TooltipTrigger>
					<TooltipContent side="bottom" className="text-xs w-64">
						<div className="space-y-1">
							<p className="font-medium">{t("common:usage.dataUnavailable")}</p>
							<p className="text-muted-foreground text-[10px]">
								Usage data is not available for {providerConfig.name}
							</p>
						</div>
					</TooltipContent>
				</Tooltip>
			</TooltipProvider>
		);
	}

	const Icon = getIcon();
	const sessionResetTime = getFormattedResetTime(
		usageData.metrics.sessionResetTimestamp,
	);
	const periodicResetTime = getFormattedResetTime(
		usageData.metrics.periodicResetTimestamp,
	);

	return (
		<Popover open={isOpen} onOpenChange={handleOpenChange}>
			<PopoverTrigger asChild>
				<button
					type="button"
					className={`flex items-center gap-1 px-2 py-1.5 rounded-md border transition-all hover:opacity-80 ${getColorClass("badge")}`}
					aria-label={`${providerConfig.name} usage status`}
					onMouseEnter={handleMouseEnter}
					onMouseLeave={handleMouseLeave}
					onClick={handleTriggerClick}
				>
					<Icon className="h-3.5 w-3.5 shrink-0" />
					{getBadgeContent()}
				</button>
			</PopoverTrigger>
			<PopoverContent
				side="bottom"
				align="end"
				className="text-xs w-80 p-0"
				onMouseEnter={handleMouseEnter}
				onMouseLeave={handleMouseLeave}
			>
				<div className="p-3 space-y-3">
					{/* Header with provider info */}
					<div className="flex items-center gap-1.5 pb-2 border-b">
						<Icon className="h-3.5 w-3.5" />
						<span className="font-semibold text-xs">
							{providerConfig.name} Usage
						</span>
						<button
							type="button"
							onClick={handleRefresh}
							className="ml-auto p-1 hover:bg-muted rounded transition-colors"
							disabled={isRefreshing}
							title="Refresh usage data"
						>
							<RefreshCw
								className={`h-3 w-3 ${isRefreshing ? "animate-spin" : ""}`}
							/>
						</button>
					</div>

					{/* Error alert */}
					{error && (
						<div className="py-2 space-y-3">
							<div className="flex items-start gap-2.5 p-2.5 rounded-lg bg-orange-500/10 border border-orange-500/20">
								<AlertCircle className="h-4 w-4 text-orange-500 shrink-0 mt-0.5" />
								<div className="space-y-1">
									<p className="text-xs font-medium text-orange-500">
										{error.code?.replaceAll("_", " ") || "Error"}
									</p>
									<p className="text-[10px] text-muted-foreground leading-relaxed">
										{error.message || "Unknown error occurred"}
									</p>
									{error.suggestions &&
										error.suggestions.length > 0 && (
											<div className="text-[10px] text-muted-foreground">
												<strong>Suggestions:</strong>
												<ul className="list-disc list-inside space-y-0.5 mt-1">
													{error.suggestions.map(
														(suggestion: string) => (
															<li key={suggestion}>{suggestion}</li>
														),
													)}
												</ul>
											</div>
										)}
								</div>
							</div>
							{error.actionType === "reauth" && (
								<button
									type="button"
									onClick={handleOpenAccounts}
									className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-md bg-destructive text-destructive-foreground hover:bg-destructive/90 transition-colors text-xs font-medium"
								>
									<LogIn className="h-3.5 w-3.5" />
									{t("common:usage.reauthButton")}
								</button>
							)}
						</div>
					)}

					{/* Re-authentication alert */}
					{needsReauth && !error && (
						<div className="py-2 space-y-3">
							<div className="flex items-start gap-2.5 p-2.5 rounded-lg bg-destructive/10 border border-destructive/20">
								<AlertCircle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
								<div className="space-y-1">
									<p className="text-xs font-medium text-destructive">
										{t("common:usage.reauthRequired")}
									</p>
									<p className="text-[10px] text-muted-foreground leading-relaxed">
										{t("common:usage.reauthRequiredDescription")}
									</p>
								</div>
							</div>
							<button
								type="button"
								onClick={handleOpenAccounts}
								className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-md bg-destructive text-destructive-foreground hover:bg-destructive/90 transition-colors text-xs font-medium"
							>
								<LogIn className="h-3.5 w-3.5" />
								{t("common:usage.reauthButton")}
							</button>
						</div>
					)}

					{/* Usage details */}
					{!needsReauth && !error && (
						<div className="py-2 space-y-3">
							{/* Session usage */}
							<div className="space-y-2">
								<div className="flex items-center justify-between">
									<span className="text-[10px] text-muted-foreground flex items-center gap-1">
										<Clock className="h-3 w-3" />
										Session
									</span>
									<span
										className={`text-xs font-semibold ${getColorClass("text")}`}
									>
										{Math.round(sessionPercent)}%
									</span>
								</div>
								<div className="w-full bg-muted rounded-full h-1.5">
									<div
										className={`h-1.5 rounded-full transition-all ${getBarColorClass(sessionPercent)}`}
										style={{ width: `${Math.min(sessionPercent, 100)}%` }}
									/>
								</div>
								{sessionResetTime && (
									<p className="text-[9px] text-muted-foreground">
										Resets in {sessionResetTime}
									</p>
								)}
							</div>

							{/* Periodic usage */}
							<div className="space-y-2">
								<div className="flex items-center justify-between">
									<span className="text-[10px] text-muted-foreground flex items-center gap-1">
										<TrendingUp className="h-3 w-3" />
										Periodic
									</span>
									<span
										className={`text-xs font-semibold ${getColorClass("text")}`}
									>
										{Math.round(periodicPercent)}%
									</span>
								</div>
								<div className="w-full bg-muted rounded-full h-1.5">
									<div
										className={`h-1.5 rounded-full transition-all ${getBarColorClass(periodicPercent)}`}
										style={{ width: `${Math.min(periodicPercent, 100)}%` }}
									/>
								</div>
								{periodicResetTime && (
									<p className="text-[9px] text-muted-foreground">
										Resets in {periodicResetTime}
									</p>
								)}
							</div>

							{/* Provider-specific details */}
							{usageData.details && (
								<div className="bg-muted/30 rounded p-2 text-[11px]">
									<div className="font-semibold mb-1">Details</div>

									{/* Anthropic details */}
									{usageData.details.anthropic && (
										<div className="space-y-1">
											{usageData.details.anthropic.subscriptionType && (
												<div>
													Subscription:{" "}
													{usageData.details.anthropic.subscriptionType}
												</div>
											)}
											{usageData.details.anthropic.opusUsagePercent && (
												<div>
													Opus: {usageData.details.anthropic.opusUsagePercent}%
												</div>
											)}
										</div>
									)}

									{/* OpenAI details */}
									{usageData.details.openai && (
										<div className="space-y-1">
											{usageData.details.openai.estimatedCost && (
												<div>
													Cost: $
													{usageData.details.openai.estimatedCost.toFixed(2)}
												</div>
											)}
										</div>
									)}

									{/* Copilot details */}
									{usageData.details.copilot && (
										<div className="space-y-1">
											{usageData.details.copilot.totalTokens && (
												<div>
													Tokens:{" "}
													{usageData.details.copilot.totalTokens.toLocaleString()}
												</div>
											)}
											{usageData.details.copilot.acceptanceRate && (
												<div>
													Acceptance:{" "}
													{usageData.details.copilot.acceptanceRate.toFixed(1)}%
												</div>
											)}
										</div>
									)}
								</div>
							)}
						</div>
					)}

					{/* Footer with account info */}
					<button
						type="button"
						onClick={handleOpenAccounts}
						className="w-full pt-3 border-t flex items-center gap-2.5 hover:bg-muted/50 -mx-3 px-3 pb-2 transition-colors cursor-pointer group"
					>
						<div className="relative">
							<div
								className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
									needsReauth ? "bg-red-500/10" : providerConfig.bgColor
								}`}
							>
								<span
									className={`text-xs font-semibold ${
										needsReauth ? "text-red-500" : providerConfig.color
									}`}
								>
									{getInitials(
										activeCredential?.credentials?.profileName ||
											usageData.profileName,
									)}
								</span>
							</div>
							{needsReauth && (
								<div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-background" />
							)}
						</div>

						<div className="flex-1 min-w-0 text-left">
							<div className="flex items-center gap-1.5">
								<span className="text-[10px] text-muted-foreground font-medium">
									Active Account
								</span>
								{needsReauth && (
									<span className="text-[9px] px-1.5 py-0.5 bg-red-500/10 text-destructive rounded font-semibold">
										{t("common:usage.needsReauth")}
									</span>
								)}
							</div>
							<p className="text-[10px] text-muted-foreground truncate">
								{activeCredential?.credentials?.profileName ||
									usageData.profileName ||
									usageData.profileEmail ||
									"Unknown Account"}
							</p>
						</div>

						<ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-foreground transition-colors shrink-0" />
					</button>
				</div>
			</PopoverContent>
		</Popover>
	);
}

export default UsageIndicatorAgnostic;
