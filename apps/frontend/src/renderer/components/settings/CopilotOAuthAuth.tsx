/**
 * Copilot OAuth Authentication Component
 *
 * Provides web-based OAuth authentication for GitHub Copilot
 * similar to Claude Code authentication.
 */

import {
	AlertCircle,
	CheckCircle,
	Loader2,
	LogIn,
	LogOut,
	Shield,
	User,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useToast } from "../../hooks/use-toast";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "../ui/card";
import { Separator } from "../ui/separator";

interface CopilotOAuthProfile {
	username: string;
	profileName: string;
	createdAt: string;
}

interface CopilotOAuthAuthProps {
	onAuthSuccess?: (username: string, profileName: string) => void;
	onAuthError?: (error: string) => void;
}

export const CopilotOAuthAuth: React.FC<CopilotOAuthAuthProps> = ({
	onAuthSuccess,
	onAuthError,
}) => {
	const { t } = useTranslation(["settings"]);
	const { toast } = useToast();

	const [isLoading, setIsLoading] = useState(false);
	const [isCheckingStatus, setIsCheckingStatus] = useState(true);
	const [authStatus, setAuthStatus] = useState<{
		authenticated: boolean;
		profiles: CopilotOAuthProfile[];
	} | null>(null);
	const [isStartingOAuth, setIsStartingOAuth] = useState(false);

	const checkAuthStatus = async () => {
		try {
			setIsCheckingStatus(true);

			// 1. Check OAuth token files via IPC
			const statusResponse = await globalThis.electronAPI.copilotOAuthStatus();
			if (statusResponse.success && statusResponse.data?.authenticated) {
				setAuthStatus(statusResponse.data);
				return;
			}

			// 2. Fallback: check GitHub CLI auth (gh auth status)
			const cliAuthResponse = await globalThis.electronAPI.checkCopilotAuth();
			if (cliAuthResponse.success && cliAuthResponse.data?.authenticated) {
				setAuthStatus({
					authenticated: true,
					profiles: [
						{
							username:
								cliAuthResponse.data.username ||
								t("settings:copilotOAuth.defaultUser"),
							profileName: "GitHub CLI",
							createdAt: new Date().toISOString(),
						},
					],
				});
				return;
			}

			// Neither OAuth nor CLI auth found
			setAuthStatus({ authenticated: false, profiles: [] });
		} catch (error) {
			console.error("Auth status check failed:", error);
			setAuthStatus({ authenticated: false, profiles: [] });
		} finally {
			setIsCheckingStatus(false);
		}
	};

	// Check authentication status on mount
	// eslint-disable-next-line react-hooks/exhaustive-deps
	// biome-ignore lint/correctness/useExhaustiveDependencies: intentional dependency omission
	useEffect(() => {
		checkAuthStatus();
	}, []);

	const startOAuth = async (profileName: string = "GitHub Copilot") => {
		try {
			setIsStartingOAuth(true);
			setIsLoading(true);

			// Ensure OAuth server is running
			const serverResponse = await fetch("http://localhost:3000/oauth/status");
			if (!serverResponse.ok) {
				throw new Error("OAuth server not available");
			}

			// Start OAuth flow
			const response =
				await globalThis.electronAPI.copilotOAuthStart(profileName);

			if (response.success) {
				toast({
					title: t("settings:copilotOAuth.toast.oauthStarted"),
					description: t("settings:copilotOAuth.toast.oauthStartedDesc"),
				});

				// Poll for authentication completion
				const pollInterval = setInterval(async () => {
					try {
						const statusResponse =
							await globalThis.electronAPI.copilotOAuthStatus();
						if (statusResponse.success && statusResponse.data.authenticated) {
							clearInterval(pollInterval);
							setIsLoading(false);
							setIsStartingOAuth(false);

							// Get the latest profile
							const latestProfile =
								statusResponse.data.profiles[
									statusResponse.data.profiles.length - 1
								];

							toast({
								title: t("settings:copilotOAuth.toast.authSuccess"),
								description: t("settings:copilotOAuth.toast.authSuccessDesc", {
									username: latestProfile.username,
								}),
							});

							if (onAuthSuccess) {
								onAuthSuccess(
									latestProfile.username,
									latestProfile.profileName,
								);
							}

							await checkAuthStatus();
						}
					} catch (error) {
						console.error("Polling error:", error);
					}
				}, 2000);

				// Stop polling after 5 minutes
				setTimeout(() => {
					clearInterval(pollInterval);
					setIsLoading(false);
					setIsStartingOAuth(false);
				}, 300000);
			} else {
				throw new Error(response.error || "Failed to start OAuth");
			}
		} catch (error) {
			const errorMessage =
				error instanceof Error ? error.message : "Unknown error";
			console.error("OAuth start failed:", errorMessage);

			toast({
				title: t("settings:copilotOAuth.toast.authFailed"),
				description: errorMessage,
				variant: "destructive",
			});

			if (onAuthError) {
				onAuthError(errorMessage);
			}

			setIsLoading(false);
			setIsStartingOAuth(false);
		}
	};

	const revokeAuth = async (username: string) => {
		try {
			setIsLoading(true);

			const response =
				await globalThis.electronAPI.copilotOAuthRevoke(username);

			if (response.success) {
				toast({
					title: t("settings:copilotOAuth.toast.authRevoked"),
					description: t("settings:copilotOAuth.toast.authRevokedDesc", {
						username,
					}),
				});

				await checkAuthStatus();
			} else {
				throw new Error(response.error || "Failed to revoke authentication");
			}
		} catch (error) {
			const errorMessage =
				error instanceof Error ? error.message : "Unknown error";
			console.error("Auth revoke failed:", errorMessage);

			toast({
				title: t("settings:copilotOAuth.toast.revokeFailed"),
				description: errorMessage,
				variant: "destructive",
			});
		} finally {
			setIsLoading(false);
		}
	};

	if (isCheckingStatus) {
		return (
			<Card>
				<CardHeader>
					<CardTitle className="flex items-center gap-2">
						<Shield className="w-5 h-5" />
						{t("settings:copilotOAuth.title")}
					</CardTitle>
					<CardDescription>
						{t("settings:copilotOAuth.description")}
					</CardDescription>
				</CardHeader>
				<CardContent>
					<div className="flex items-center justify-center py-8">
						<Loader2 className="w-6 h-6 animate-spin mr-2" />
						{t("settings:copilotOAuth.checkingStatus")}
					</div>
				</CardContent>
			</Card>
		);
	}

	if (!authStatus) {
		return (
			<Card>
				<CardHeader>
					<CardTitle className="flex items-center gap-2">
						<AlertCircle className="w-5 h-5 text-destructive" />
						{t("settings:copilotOAuth.title")}
					</CardTitle>
					<CardDescription>
						{t("settings:copilotOAuth.description")}
					</CardDescription>
				</CardHeader>
				<CardContent>
					<div className="text-center py-8 text-destructive">
						<AlertCircle className="w-12 h-12 mx-auto mb-4" />
						<p>{t("settings:copilotOAuth.serverUnavailable")}</p>
						<p className="text-sm text-muted-foreground mt-2">
							{t("settings:copilotOAuth.serverUnavailableHint")}
						</p>
					</div>
				</CardContent>
			</Card>
		);
	}

	return (
		<Card>
			<CardHeader>
				<CardTitle className="flex items-center gap-2">
					<Shield className="w-5 h-5" />
					{t("settings:copilotOAuth.title")}
					<Badge variant={authStatus.authenticated ? "default" : "secondary"}>
						{authStatus.authenticated
							? t("settings:copilotOAuth.authenticated")
							: t("settings:copilotOAuth.notAuthenticated")}
					</Badge>
				</CardTitle>
				<CardDescription>
					{t("settings:copilotOAuth.descriptionNoCli")}
				</CardDescription>
			</CardHeader>
			<CardContent className="space-y-4">
				{authStatus.authenticated && authStatus.profiles.length > 0 ? (
					<>
						<div className="space-y-3">
							<h4 className="text-sm font-medium">
								{t("settings:copilotOAuth.authenticatedProfiles")}
							</h4>
							{authStatus.profiles.map((profile) => (
								<div
									key={`${profile.username}-${profile.profileName}`}
									className="flex items-center justify-between p-3 border rounded-lg"
								>
									<div className="flex items-center gap-3">
										<User className="w-4 h-4 text-muted-foreground" />
										<div>
											<p className="font-medium">{profile.username}</p>
											<p className="text-sm text-muted-foreground">
												{profile.profileName}
											</p>
											<p className="text-xs text-muted-foreground">
												{t("settings:copilotOAuth.addedDate", {
													date: new Date(
														profile.createdAt,
													).toLocaleDateString(),
												})}
											</p>
										</div>
									</div>
									<Button
										variant="outline"
										size="sm"
										onClick={() => revokeAuth(profile.username)}
										disabled={isLoading}
									>
										{isLoading ? (
											<Loader2 className="w-4 h-4 animate-spin" />
										) : (
											<LogOut className="w-4 h-4" />
										)}
									</Button>
								</div>
							))}
						</div>
						<Separator />
						<div className="flex items-center justify-between">
							<div className="text-sm text-muted-foreground">
								<CheckCircle className="w-4 h-4 inline mr-1 text-green-500" />
								{t("settings:copilotOAuth.readyToUse")}
							</div>
							<Button
								variant="outline"
								onClick={() => startOAuth("Additional Profile")}
								disabled={isLoading || isStartingOAuth}
							>
								{isLoading || isStartingOAuth ? (
									<Loader2 className="w-4 h-4 animate-spin mr-2" />
								) : (
									<LogIn className="w-4 h-4 mr-2" />
								)}
								{t("settings:copilotOAuth.addProfile")}
							</Button>
						</div>
					</>
				) : (
					<div className="text-center py-8">
						<LogIn className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
						<h4 className="font-medium mb-2">
							{t("settings:copilotOAuth.noAuthFound")}
						</h4>
						<p className="text-sm text-muted-foreground mb-6">
							{t("settings:copilotOAuth.noAuthFoundDesc")}
						</p>
						<Button
							onClick={() => startOAuth("GitHub Copilot")}
							disabled={isLoading || isStartingOAuth}
							className="w-full"
						>
							{isLoading || isStartingOAuth ? (
								<>
									<Loader2 className="w-4 h-4 animate-spin mr-2" />
									{isStartingOAuth
										? t("settings:copilotOAuth.openingBrowser")
										: t("settings:copilotOAuth.authenticating")}
								</>
							) : (
								<>
									<LogIn className="w-4 h-4 mr-2" />
									{t("settings:copilotOAuth.authenticateButton")}
								</>
							)}
						</Button>
					</div>
				)}
			</CardContent>
		</Card>
	);
};
