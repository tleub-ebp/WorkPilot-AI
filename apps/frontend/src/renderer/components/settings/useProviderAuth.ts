import { useCallback, useState } from "react";

interface AuthTerminalState {
	terminalId: string;
	configDir: string;
	profileName: string;
}

interface WindsurfAccountInfo {
	userName?: string;
	planName?: string;
	usageInfo?: {
		usedMessages: number;
		totalMessages: number;
		usedFlowActions: number;
		totalFlowActions: number;
	};
}

export function useProviderAuth() {
	const [isAuthenticating, setIsAuthenticating] = useState(false);
	const [authTerminal, setAuthTerminal] = useState<AuthTerminalState | null>(
		null,
	);
	const [windsurfSsoToken, setWindsurfSsoToken] = useState("");
	const [windsurfAccountInfo, setWindsurfAccountInfo] =
		useState<WindsurfAccountInfo | null>(null);

	const handleClaudeAuth = useCallback(
		async (_providerId: string, providerName: string) => {
			try {
				const profilesResult = await globalThis.electronAPI.getClaudeProfiles();
				const activeProfileId =
					profilesResult.success && profilesResult.data
						? profilesResult.data.activeProfileId
						: undefined;

				if (!activeProfileId) {
					console.error(
						"[ProviderConfigDialog] No active Claude profile found",
					);
					return {
						success: false,
						error: "No Claude profile found. Please restart the application.",
					};
				}

				const result =
					await globalThis.electronAPI.authenticateClaudeProfile(
						activeProfileId,
					);
				if (result.success && result.data) {
					setAuthTerminal({
						terminalId: result.data.terminalId,
						configDir: result.data.configDir,
						profileName: providerName,
					});
					return { success: true };
				} else {
					console.error(
						"[ProviderConfigDialog] Failed to prepare Claude auth:",
						result.error,
					);
					return {
						success: false,
						error: result.error || "Failed to prepare authentication",
					};
				}
			} catch (error) {
				console.error(
					"[ProviderConfigDialog] Error preparing Claude auth:",
					error,
				);
				return {
					success: false,
					error: error instanceof Error ? error.message : "Unknown error",
				};
			}
		},
		[],
	);

	const handleFallbackAuth = useCallback(
		(providerId: string, providerName: string) => {
			const terminalId = `auth-${providerId}-${Date.now()}`;
			const configDir = `claude-config-${providerId}`;
			setAuthTerminal({ terminalId, configDir, profileName: providerName });
		},
		[],
	);

	const handleOpenAICodexAuth = useCallback(
		(providerId: string, providerName: string) => {
			const terminalId = `auth-codex-${Date.now()}`;
			const configDir = `codex-config-${providerId}`;
			setAuthTerminal({ terminalId, configDir, profileName: providerName });
			return { success: true };
		},
		[],
	);

	const handleOAuthAuth = useCallback(
		async (providerId: string, providerName: string) => {
			setIsAuthenticating(true);

			if (providerId === "anthropic" || providerId === "claude") {
				const result = await handleClaudeAuth(providerId, providerName);
				if (!result.success) {
					setIsAuthenticating(false);
				}
				return result;
			} else if (providerId === "openai") {
				const result = handleOpenAICodexAuth(providerId, providerName);
				return result;
			} else {
				handleFallbackAuth(providerId, providerName);
				return { success: true };
			}
		},
		[handleClaudeAuth, handleOpenAICodexAuth, handleFallbackAuth],
	);

	const handleAuthTerminalClose = useCallback(() => {
		setAuthTerminal(null);
		setIsAuthenticating(false);
	}, []);

	const handleAuthTerminalSuccess = useCallback(
		(
			email?: string,
			onSettingsChange?: (settings: Record<string, unknown>) => void,
			settings?: Record<string, unknown>,
			providerId?: string,
		) => {
			setIsAuthenticating(false);

			// Persist OAuth state in settings so the provider shows as configured
			if (
				onSettingsChange &&
				settings &&
				providerId &&
				(providerId === "anthropic" || providerId === "claude")
			) {
				const newSettings = { ...settings };
				newSettings.globalClaudeOAuthToken = email || "oauth-authenticated";
				onSettingsChange(newSettings);
			}

			// Persist Codex CLI OAuth state for OpenAI
			if (onSettingsChange && settings && providerId === "openai") {
				const newSettings = { ...settings };
				newSettings.globalOpenAICodexOAuthToken =
					email || "codex-authenticated";
				onSettingsChange(newSettings);
			}
		},
		[],
	);

	const handleAuthTerminalError = useCallback((_error: string) => {
		setAuthTerminal(null);
		setIsAuthenticating(false);
	}, []);

	const handleWindsurfDetect = useCallback(async () => {
		setIsAuthenticating(true);
		try {
			const result = await globalThis.electronAPI.detectWindsurfToken();
			if (result.success && result.apiKey) {
				setWindsurfSsoToken(result.apiKey);
				if (result.userName || result.planName) {
					setWindsurfAccountInfo({
						userName: result.userName,
						planName: result.planName,
						usageInfo: result.usageInfo,
					});
				}
				return {
					success: true,
					message: `Token detected for ${result.userName || "user"}`,
					userName: result.userName,
				};
			} else {
				return {
					success: false,
					message: result.error || "Failed to detect Windsurf token",
				};
			}
		} catch {
			return {
				success: false,
				message: "Failed to detect Windsurf token",
			};
		} finally {
			setIsAuthenticating(false);
		}
	}, []);

	const handleWindsurfSave = useCallback(
		(
			windsurfSsoToken: string,
			providerConfig: { apiKey?: string },
			onSettingsChange: (settings: Record<string, unknown>) => void,
			settings: Record<string, unknown>,
			onProviderActivated?: (providerId: string) => void,
			providerId?: string,
			onOpenChange?: (open: boolean) => void,
		) => {
			if (!providerConfig?.apiKey) return;

			const newSettings = { ...settings };
			newSettings[providerConfig.apiKey] = windsurfSsoToken.trim();
			newSettings[`${providerConfig.apiKey}Enabled`] = true;
			onSettingsChange(newSettings);
			onProviderActivated?.(providerId || "");
			onOpenChange?.(false);
		},
		[],
	);

	const loadWindsurfAccountInfo = useCallback(async () => {
		if (globalThis.electronAPI?.detectWindsurfToken) {
			try {
				const result = await globalThis.electronAPI.detectWindsurfToken();
				if (result.success && (result.userName || result.planName)) {
					setWindsurfAccountInfo({
						userName: result.userName,
						planName: result.planName,
						usageInfo: result.usageInfo,
					});
				}
			} catch {
				// silent
			}
		}
	}, []);

	return {
		isAuthenticating,
		authTerminal,
		windsurfSsoToken,
		windsurfAccountInfo,
		handleOAuthAuth,
		handleAuthTerminalClose,
		handleAuthTerminalSuccess,
		handleAuthTerminalError,
		handleWindsurfDetect,
		handleWindsurfSave,
		loadWindsurfAccountInfo,
		setWindsurfSsoToken,
		setWindsurfAccountInfo,
	};
}
