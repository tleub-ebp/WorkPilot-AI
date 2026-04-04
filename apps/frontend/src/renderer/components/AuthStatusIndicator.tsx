/**
 * AuthStatusIndicator - Dumb display component for authentication status
 *
 * Shows the active authentication method and provider:
 * - OAuth: Shows "Anthropic" with Lock icon (Claude Code subscription)
 * - API Profile: Shows provider name with Key icon and provider-specific colors
 *
 * This component does NOT perform any authentication detection.
 * Auth type is derived purely from selectedProvider + profiles data:
 * - If selectedProvider matches an API profile -> type 'profile'
 * - If selectedProvider is 'anthropic' with no API profile -> type 'oauth'
 * - Otherwise -> type 'provider'
 *
 * Usage data comes from UsageMonitor via IPC push events.
 */

import {
	type ApiProvider,
	detectProvider,
	getProviderBadgeColor,
	getProviderLabel,
} from "@shared/utils/provider-detection";
import {
	ExternalLink,
	Fingerprint,
	Key,
	Lock,
	Server,
	Shield,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useClaudeProfileStore } from "@/stores/claude-profile-store";
import { useSettingsStore } from "@/stores/settings-store";
import { useProviderContext } from "./ProviderContext";
import {
	Tooltip,
	TooltipContent,
	TooltipProvider,
	TooltipTrigger,
} from "./ui/tooltip";

/**
 * Get subscription translation key based on subscription type
 */
function getSubscriptionTranslationKey(subscriptionType?: string): string {
	if (!subscriptionType) return "common:usage.claudeCodeSubscriptionUnknown";

	const normalizedType = subscriptionType.toLowerCase();

	if (normalizedType.includes("pro")) {
		return "common:usage.claudeCodeSubscriptionPro";
	} else if (normalizedType.includes("max")) {
		return "common:usage.claudeCodeSubscriptionMax";
	} else {
		return "common:usage.claudeCodeSubscriptionUnknown";
	}
}

/**
 * OAuth fallback state when no API profile is active (e.g. Claude Code subscription)
 */
const OAUTH_FALLBACK = {
	type: "oauth" as const,
	name: "OAuth",
	provider: "anthropic" as const,
	providerLabel: "Anthropic",
	badgeColor:
		"bg-orange-500/10 text-orange-500 border-orange-500/20 hover:bg-orange-500/15",
} as const;

export function AuthStatusIndicator() {
	const { profiles, activeProfileId } = useSettingsStore();
	const { t } = useTranslation(["common"]);
	const { selectedProvider } = useProviderContext();

	// Track GitHub CLI status for Copilot provider
	const [githubStatus, setGithubStatus] = useState<{
		available: boolean;
		isAuth?: boolean;
		username?: string;
	} | null>(null);
	const [isLoadingGithubStatus, setIsLoadingGithubStatus] = useState(false);

	// Track Windsurf account info
	const [windsurfAccount, setWindsurfAccount] = useState<{
		userName?: string;
		planName?: string;
		usageInfo?: {
			usedMessages: number;
			totalMessages: number;
			usedFlowActions: number;
			totalFlowActions: number;
		};
	} | null>(null);
	const [isLoadingWindsurfAccount, setIsLoadingWindsurfAccount] =
		useState(false);

	// Get Claude subscription info from the profile store (populated from Keychain credentials)
	const { profiles: claudeProfiles, activeProfileId: activeClaudeProfileId } =
		useClaudeProfileStore();
	const activeClaudeProfile = claudeProfiles.find(
		(p) => p.id === activeClaudeProfileId,
	);
	const claudeSubscriptionType = activeClaudeProfile?.subscriptionType;

	// Subscribe to provider/profile change events
	useEffect(() => {
		// This effect can be used for future provider/profile change handling
	}, []);

	// Fetch GitHub CLI status when Copilot provider is selected
	useEffect(() => {
		if (selectedProvider === "copilot") {
			setIsLoadingGithubStatus(true);

			globalThis.electronAPI
				.getGithubCliStatus?.()
				.then(
					(result: {
						success: boolean;
						data: { available: boolean; isAuth?: boolean; username?: string };
					}) => {
						if (result.success && result.data) {
							setGithubStatus(result.data);
						} else {
							setGithubStatus({ available: false });
						}
					},
				)
				.catch((error: Error) => {
					console.warn(
						"[AuthStatusIndicator] Failed to fetch GitHub CLI status:",
						error,
					);
					setGithubStatus({ available: false });
				})
				.finally(() => {
					setIsLoadingGithubStatus(false);
				});
		} else {
			setGithubStatus(null);
			setIsLoadingGithubStatus(false);
		}
	}, [selectedProvider]);

	// Fetch Windsurf account info when Windsurf provider is selected
	useEffect(() => {
		if (selectedProvider === "windsurf") {
			setIsLoadingWindsurfAccount(true);

			globalThis.electronAPI
				.detectWindsurfToken?.()
				.then(
					(result: {
						success: boolean;
						userName?: string;
						planName?: string;
						usageInfo?: {
							usedMessages: number;
							totalMessages: number;
							usedFlowActions: number;
							totalFlowActions: number;
						};
					}) => {
						if (result.success) {
							setWindsurfAccount({
								userName: result.userName,
								planName: result.planName,
								usageInfo: result.usageInfo,
							});
						} else {
							setWindsurfAccount(null);
						}
					},
				)
				.catch((error: Error) => {
					console.warn(
						"[AuthStatusIndicator] Failed to fetch Windsurf account info:",
						error,
					);
					setWindsurfAccount(null);
				})
				.finally(() => {
					setIsLoadingWindsurfAccount(false);
				});
		} else {
			setWindsurfAccount(null);
			setIsLoadingWindsurfAccount(false);
		}
	}, [selectedProvider]);

	// Derive auth status purely from selectedProvider + profiles (no IPC calls)
	const authStatus = useMemo(() => {
		if (selectedProvider) {
			const providerProfile = profiles.find(
				(p) => detectProvider(p.baseUrl) === selectedProvider,
			);
			const provider = selectedProvider as ApiProvider;
			const providerLabel = getProviderLabel(provider);

			if (providerProfile) {
				return {
					type: "profile" as const,
					name: providerProfile.name,
					id: providerProfile.id,
					baseUrl: providerProfile.baseUrl,
					createdAt: providerProfile.createdAt,
					provider,
					providerLabel,
					badgeColor: getProviderBadgeColor(provider),
				};
			}

			// No matching API profile — for anthropic, assume OAuth (Claude Code subscription)
			if (provider === "anthropic") {
				return OAUTH_FALLBACK;
			}

			return {
				type: "provider" as const,
				name: providerLabel,
				provider,
				providerLabel,
				badgeColor: getProviderBadgeColor(provider),
			};
		}

		if (activeProfileId) {
			const activeProfile = profiles.find((p) => p.id === activeProfileId);
			if (activeProfile) {
				const provider = detectProvider(activeProfile.baseUrl);
				const providerLabel = getProviderLabel(provider);
				return {
					type: "profile" as const,
					name: activeProfile.name,
					id: activeProfile.id,
					baseUrl: activeProfile.baseUrl,
					createdAt: activeProfile.createdAt,
					provider,
					providerLabel,
					badgeColor: getProviderBadgeColor(provider),
				};
			}
		}

		// Final fallback — use OAUTH_FALLBACK only for Anthropic, generic provider otherwise
		return OAUTH_FALLBACK;
	}, [selectedProvider, profiles, activeProfileId]);

	const isOAuth = authStatus.type === "oauth";
	const Icon = isOAuth ? Lock : Key;
	const badgeLabel = getProviderLabel(authStatus.provider);

	// Render provider-specific content based on selected provider
	const providerSpecificContent = useMemo(() => {
		if (selectedProvider === "copilot") {
			return (
				<div className="pt-2 border-t space-y-2">
					<div className="text-[10px] text-muted-foreground">
						{t("common:usage.copilotAuthNote", { provider: "GitHub Copilot" })}
					</div>

					{/* GitHub CLI Status */}
					{(() => {
						if (isLoadingGithubStatus) {
							return (
								<div className="text-[10px] text-muted-foreground italic">
									{t("common:usage.checkingGithubStatus")}
								</div>
							);
						}

						if (!githubStatus) {
							return (
								<div className="text-[10px] text-muted-foreground italic">
									{t("common:usage.cannotCheckGithubStatus")}
								</div>
							);
						}

						if (githubStatus.available) {
							return (
								<div className="space-y-1">
									<div className="flex items-center justify-between">
										<div className="flex items-center gap-1.5 text-muted-foreground">
											<Shield className="h-3 w-3" />
											<span className="text-[10px]">
												{t("common:usage.githubStatus")}
											</span>
										</div>
										<span
											className={`text-[10px] font-medium ${githubStatus.isAuth ? "text-green-500" : "text-red-500"}`}
										>
											{githubStatus.isAuth
												? t("common:usage.connected")
												: t("common:usage.notConnected")}
										</span>
									</div>
									{githubStatus.username && (
										<div className="flex items-center justify-between">
											<div className="flex items-center gap-1.5 text-muted-foreground">
												<Key className="h-3 w-3" />
												<span className="text-[10px]">
													{t("common:usage.activeAccount")}
												</span>
											</div>
											<span className="text-[10px] font-medium text-blue-500">
												@{githubStatus.username}
											</span>
										</div>
									)}
								</div>
							);
						}

						return (
							<div className="text-[10px] text-red-500">
								{t("common:usage.githubCliNotAvailable")}{" "}
								<code className="bg-muted px-1 rounded">gh auth login</code>
							</div>
						);
					})()}

					{/* Note about missing usage data */}
					<div className="pt-1 border-t">
						<div className="text-[10px] text-muted-foreground italic">
							{t("common:usage.dataUnavailable")}
						</div>
						<div className="text-[10px] text-muted-foreground italic">
							{t("common:usage.dataUnavailableDescription")}
						</div>
						<div className="text-[10px] text-muted-foreground mt-1">
							<a
								href="https://github.com/settings/copilot"
								target="_blank"
								rel="noopener noreferrer"
								className="text-blue-500 underline"
							>
								{t("common:usage.copilotDashboardLink")}
							</a>
						</div>
					</div>
				</div>
			);
		}

		if (selectedProvider === "windsurf") {
			return (
				<div className="pt-2 border-t space-y-2">
					<div className="text-[10px] text-muted-foreground">
						{t("common:usage.windsurfAuthNote")}
					</div>

					{/* Windsurf Account Info */}
					{(() => {
						if (isLoadingWindsurfAccount) {
							return (
								<div className="text-[10px] text-muted-foreground italic">
									{t("common:usage.checkingWindsurfStatus")}
								</div>
							);
						}

						if (!windsurfAccount) {
							return (
								<div className="text-[10px] text-muted-foreground italic">
									{t("common:usage.windsurfNotDetected")}
								</div>
							);
						}

						return (
							<div className="space-y-1">
								{/* User name */}
								{windsurfAccount.userName && (
									<div className="flex items-center justify-between">
										<div className="flex items-center gap-1.5 text-muted-foreground">
											<Key className="h-3 w-3" />
											<span className="text-[10px]">
												{t("common:usage.activeAccount")}
											</span>
										</div>
										<span className="text-[10px] font-medium text-teal-500">
											{windsurfAccount.userName}
										</span>
									</div>
								)}
								{/* Plan */}
								{windsurfAccount.planName && (
									<div className="flex items-center justify-between">
										<div className="flex items-center gap-1.5 text-muted-foreground">
											<Shield className="h-3 w-3" />
											<span className="text-[10px]">
												{t("common:usage.windsurfPlan")}
											</span>
										</div>
										<span className="text-[10px] font-medium">
											{windsurfAccount.planName}
										</span>
									</div>
								)}
								{/* Usage info */}
								{windsurfAccount.usageInfo && (
									<div className="space-y-1 pt-1 border-t">
										<div className="flex items-center justify-between">
											<span className="text-[10px] text-muted-foreground">
												{t("common:usage.windsurfCredits")}
											</span>
											<span className="text-[10px] font-medium">
												{Math.round(
													windsurfAccount.usageInfo.usedMessages / 100,
												)}
												/
												{Math.round(
													windsurfAccount.usageInfo.totalMessages / 100,
												)}
											</span>
										</div>
										<div className="flex items-center justify-between">
											<span className="text-[10px] text-muted-foreground">
												{t("common:usage.windsurfFlowActions")}
											</span>
											<span className="text-[10px] font-medium">
												{Math.round(
													windsurfAccount.usageInfo.usedFlowActions / 100,
												)}
												/
												{Math.round(
													windsurfAccount.usageInfo.totalFlowActions / 100,
												)}
											</span>
										</div>
									</div>
								)}
							</div>
						);
					})()}

					{/* Dashboard link */}
					<div className="pt-1 border-t">
						<div className="text-[10px] text-muted-foreground mt-1">
							<a
								href="https://windsurf.com/subscription/usage"
								target="_blank"
								rel="noopener noreferrer"
								className="text-teal-500 underline"
							>
								{t("common:usage.windsurfDashboardLink")}
							</a>
						</div>
					</div>
				</div>
			);
		}

		// Fallback when no profile configured for this provider
		return (
			<div className="pt-2 border-t text-[10px] text-muted-foreground">
				{t("common:usage.noProfileForProvider", { provider: badgeLabel })}
			</div>
		);
	}, [
		selectedProvider,
		isLoadingGithubStatus,
		githubStatus,
		isLoadingWindsurfAccount,
		windsurfAccount,
		t,
		badgeLabel,
	]);

	// Helper function to get full ID for display
	const getFullId = (id: string | undefined): string => {
		if (!id) return "";
		return id;
	};

	return (
		<div className="flex items-center gap-2">
			{/* Provider Badge + Tooltip */}
			<TooltipProvider delayDuration={200}>
				<Tooltip>
					<TooltipTrigger asChild>
						<button
							type="button"
							className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border transition-all hover:opacity-80 ${authStatus.badgeColor}`}
							aria-label={t("common:usage.authenticationAriaLabel", {
								provider: badgeLabel,
							})}
						>
							<Icon className="h-3.5 w-3.5" />
							<span className="text-xs font-semibold">{badgeLabel}</span>
						</button>
					</TooltipTrigger>
					<TooltipContent side="bottom" className="text-xs max-w-xs p-0">
						<div className="p-3 space-y-3">
							{/* Header section */}
							<div className="flex items-center justify-between pb-2 border-b">
								<div className="flex items-center gap-1.5">
									<Shield className="h-3.5 w-3.5" />
									<span className="font-semibold text-xs">
										{t("common:usage.authenticationDetails")}
									</span>
								</div>
								<div
									className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
										isOAuth
											? "bg-orange-500/15 text-orange-500"
											: "bg-primary/15 text-primary"
									}`}
								>
									{isOAuth ? t("common:usage.oauth") : t("common:usage.apiKey")}
								</div>
							</div>

							{/* Provider info */}
							<div className="flex items-center justify-between">
								<div className="flex items-center gap-1.5 text-muted-foreground">
									<Server className="h-3.5 w-3.5" />
									<span className="font-medium text-[11px]">
										{t("common:usage.provider")}
									</span>
								</div>
								<span className="font-semibold text-xs">{badgeLabel}</span>
							</div>

							{/* Claude Code subscription label for OAuth */}
							{isOAuth && (
								<div className="flex items-center justify-between pt-2 border-t">
									<div className="flex items-center gap-1.5 text-muted-foreground">
										<Lock className="h-3 w-3" />
										<span className="text-[10px]">
											{t("common:usage.subscription")}
										</span>
									</div>
									<span className="font-medium text-[10px]">
										{t(getSubscriptionTranslationKey(claudeSubscriptionType))}
									</span>
								</div>
							)}

							{/* Profile details for API profiles */}
							{authStatus.type === "profile" ? (
								<div className="pt-2 border-t space-y-2">
									{/* Profile name */}
									<div className="flex items-center justify-between">
										<div className="flex items-center gap-1.5 text-muted-foreground">
											<Key className="h-3 w-3" />
											<span className="text-[10px]">
												{t("common:usage.profile")}
											</span>
										</div>
										<span className="font-medium text-[10px]">
											{authStatus.name}
										</span>
									</div>
									{/* Profile ID */}
									<div className="flex items-center justify-between">
										<div className="flex items-center gap-1.5 text-muted-foreground">
											<Fingerprint className="h-3 w-3" />
											<span className="text-[10px]">
												{t("common:usage.id")}
											</span>
										</div>
										{authStatus.id && (
											<span className="text-xs text-muted-foreground ml-2">
												{getFullId(authStatus.id)}
											</span>
										)}
									</div>
									{/* API Endpoint */}
									{authStatus.baseUrl && (
										<div className="pt-1">
											<div className="flex items-center gap-1.5 text-[10px] text-muted-foreground mb-1">
												<ExternalLink className="h-3 w-3" />
												<span>{t("common:usage.apiEndpoint")}</span>
											</div>
											<div className="text-[10px] font-mono bg-muted px-2 py-1.5 rounded break-all border">
												{authStatus.baseUrl}
											</div>
										</div>
									)}
								</div>
							) : (
								providerSpecificContent
							)}
						</div>
					</TooltipContent>
				</Tooltip>
			</TooltipProvider>
		</div>
	);
}
