/**
 * GitHub Copilot Configuration Component
 *
 * Composant pour configurer GitHub Copilot CLI (similaire à ClaudeCodeConfig)
 */

import {
	AlertCircle,
	CheckCircle,
	Key,
	Loader2,
	LogIn,
	LogOut,
	Settings,
	XCircle,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useToast } from "@/hooks/use-toast";
import { Globe } from "@/lib/icons";
import { useGitHubCopilot } from "../../hooks/useGitHubCopilot";
import { Alert, AlertDescription } from "../ui/alert";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "../ui/card";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../ui/select";
import { GitHubCopilotAuthTerminal } from "./GitHubCopilotAuthTerminal";

export function GitHubCopilotConfig() {
	const { t } = useTranslation("settings");

	// Auth terminal state
	const [authTerminal, setAuthTerminal] = useState<{
		terminalId: string;
		profileName: string;
	} | null>(null);

	const {
		status,
		config,
		isLoading,
		error,
		setToken,
		removeToken,
		logout,
		testConnection,
		refreshStatus,
		clearError,
	} = useGitHubCopilot();

	const [tokenInput, setTokenInput] = useState("");
	const [isTesting, setIsTesting] = useState(false);
	const [authMethod, setAuthMethod] = useState<"terminal" | "token">(
		"terminal",
	);
	const { toast } = useToast();

	// Synchroniser le token input avec la configuration
	useEffect(() => {
		setTokenInput(config.token || "");
	}, [config.token]);

	// Effacer l'erreur quand le token change
	useEffect(() => {
		if (tokenInput) {
			clearError();
		}
	}, [tokenInput, clearError]);

	/**
	 * Gérer la sauvegarde du token
	 */
	const handleSaveToken = async () => {
		if (!tokenInput.trim()) {
			toast({
				variant: "destructive",
				title: t("githubCopilot.errors.tokenRequired"),
				description: t("githubCopilot.errors.tokenRequiredDescription"),
			});
			return;
		}

		try {
			await setToken(tokenInput.trim());
			toast({
				title: t("githubCopilot.tokenSaved"),
				description: t("githubCopilot.tokenSavedDescription"),
			});
			// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
		} catch (error: any) {
			toast({
				variant: "destructive",
				title: t("githubCopilot.errors.saveFailed"),
				description:
					error instanceof Error
						? error.message
						: t("githubCopilot.errors.unknownError"),
			});
		}
	};

	/**
	 * Gérer la suppression du token
	 */
	const handleRemoveToken = async () => {
		try {
			await removeToken();
			setTokenInput("");
			toast({
				title: t("githubCopilot.tokenRemoved"),
				description: t("githubCopilot.tokenRemovedDescription"),
			});
			// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
		} catch (error: any) {
			toast({
				variant: "destructive",
				title: t("githubCopilot.errors.removeFailed"),
				description:
					error instanceof Error
						? error.message
						: t("githubCopilot.errors.unknownError"),
			});
		}
	};

	/**
	 * Gérer l'authentification GitHub CLI avec terminal intégré
	 */
	const handleAuthenticate = async () => {
		try {
			// Create a terminal ID for integrated authentication
			const terminalId = `copilot-auth-${Date.now()}`;

			setAuthTerminal({
				terminalId,
				profileName: "GitHub Copilot",
			});
			// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
		} catch (error: any) {
			toast({
				variant: "destructive",
				title: t("githubCopilot.errors.authFailed"),
				description:
					error instanceof Error
						? error.message
						: t("githubCopilot.errors.unknownError"),
			});
		}
	};

	/**
	 * Handle terminal auth success
	 */
	const handleAuthTerminalSuccess = async (username?: string) => {
		setAuthTerminal(null);
		toast({
			title: t("githubCopilot.authSuccess"),
			description: username
				? `${t("githubCopilot.authSuccessDescription")} (${username})`
				: t("githubCopilot.authSuccessDescription"),
		});
		await refreshStatus();
	};

	/**
	 * Handle terminal auth error
	 */
	const handleAuthTerminalError = (error: string) => {
		setAuthTerminal(null);
		toast({
			variant: "destructive",
			title: t("githubCopilot.errors.authFailed"),
			description: error,
		});
	};

	/**
	 * Handle terminal close
	 */
	const handleAuthTerminalClose = () => {
		setAuthTerminal(null);
	};

	/**
	 * Gérer la déconnexion
	 */
	const handleLogout = async () => {
		try {
			await logout();
			toast({
				title: t("githubCopilot.logoutSuccess"),
				description: t("githubCopilot.logoutSuccessDescription"),
			});
			// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
		} catch (error: any) {
			toast({
				variant: "destructive",
				title: t("githubCopilot.errors.logoutFailed"),
				description:
					error instanceof Error
						? error.message
						: t("githubCopilot.errors.unknownError"),
			});
		}
	};

	/**
	 * Gérer le test de connexion
	 */
	const handleTestConnection = async () => {
		setIsTesting(true);
		try {
			const result = await testConnection();

			if (result.success) {
				toast({
					title: t("githubCopilot.testSuccess"),
					description: result.message,
				});
			} else {
				toast({
					variant: "destructive",
					title: t("githubCopilot.testFailed"),
					description: result.message,
				});
			}
			// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
		} catch (error: any) {
			toast({
				variant: "destructive",
				title: t("githubCopilot.testError"),
				description:
					error instanceof Error
						? error.message
						: t("githubCopilot.errors.unknownError"),
			});
		} finally {
			setIsTesting(false);
		}
	};

	/**
	 * Obtenir le badge de statut
	 */
	const getStatusBadge = () => {
		if (isLoading) {
			return (
				<Badge variant="outline">
					<Loader2 className="w-3 h-3 animate-spin" />
				</Badge>
			);
		}

		if (!status.installed) {
			return (
				<Badge variant="destructive">
					{t("githubCopilot.status.notInstalled")}
				</Badge>
			);
		}

		if (!status.authenticated) {
			return (
				<Badge variant="secondary">
					{t("githubCopilot.status.notAuthenticated")}
				</Badge>
			);
		}

		return (
			<Badge variant="default">{t("githubCopilot.status.authenticated")}</Badge>
		);
	};

	/**
	 * Obtenir l'icône de statut
	 */
	const getStatusIcon = () => {
		if (isLoading) return <Loader2 className="w-4 h-4 animate-spin" />;
		if (!status.installed) return <XCircle className="w-4 h-4" />;
		if (!status.authenticated) return <AlertCircle className="w-4 h-4" />;
		return <CheckCircle className="w-4 h-4" />;
	};

	const renderTerminalActions = () => {
		if (status.authenticated) {
			return (
				<Button
					variant="outline"
					size="sm"
					onClick={handleLogout}
					disabled={isLoading}
				>
					<LogOut className="w-4 h-4 mr-1" />
					{t("githubCopilot.logout")}
				</Button>
			);
		}

		return (
			<Button size="sm" onClick={handleAuthenticate} disabled={isLoading}>
				<LogIn className="w-4 h-4 mr-1" />
				{isLoading ? t("common.loading") : t("githubCopilot.authenticate")}
			</Button>
		);
	};

	return (
		<div className="space-y-4">
			<div>
				<h3 className="text-lg font-medium">{t("githubCopilot.title")}</h3>
			</div>

			{/* Header */}
			<Card>
				<CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
					<div className="flex items-center space-x-2">
						<Globe className="w-5 h-5" />
						<CardTitle className="text-lg">
							{t("githubCopilot.title")}
						</CardTitle>
					</div>
					<div className="flex items-center space-x-2">{getStatusBadge()}</div>
				</CardHeader>
				<CardContent>
					<CardDescription>{t("githubCopilot.description")}</CardDescription>

					{/* Statut détaillé */}
					<div className="mt-4 flex items-center space-x-2 text-sm">
						{getStatusIcon()}
						<span>
							{status.installed
								? t("githubCopilot.status.installed", {
										version: status.version,
									})
								: t("githubCopilot.status.notInstalled")}
							{status.installed && (
								<span className="text-muted-foreground">
									•{" "}
									{status.authenticated
										? t("githubCopilot.status.authenticatedAs", {
												username: status.username,
											})
										: t("githubCopilot.status.notAuthenticated")}
								</span>
							)}
						</span>
					</div>

					{/* Actions rapides */}
					<div className="mt-4 flex flex-wrap gap-2">
						{status.installed && (
							<>
								{authMethod === "terminal"
									? // Actions pour la méthode terminal
										renderTerminalActions()
									: // Actions pour la méthode token (gérées dans la section token)
										null}
								<Button
									variant="outline"
									size="sm"
									onClick={handleTestConnection}
									disabled={isTesting}
								>
									{isTesting ? t("common.testing") : t("common.test")}
								</Button>
							</>
						)}
						<Button
							variant="outline"
							size="sm"
							onClick={refreshStatus}
							disabled={isLoading}
						>
							{t("common.refresh")}
						</Button>
					</div>
				</CardContent>
			</Card>

			{/* Erreur */}
			{error && (
				<Alert variant="destructive">
					<XCircle className="h-4 w-4" />
					<AlertDescription>{error}</AlertDescription>
				</Alert>
			)}

			{/* Auth Terminal */}
			{authTerminal && (
				<Card>
					<CardContent className="p-0">
						<div className="h-80">
							<GitHubCopilotAuthTerminal
								terminalId={authTerminal.terminalId}
								profileName={authTerminal.profileName}
								onClose={handleAuthTerminalClose}
								onAuthSuccess={handleAuthTerminalSuccess}
								onAuthError={handleAuthTerminalError}
							/>
						</div>
					</CardContent>
				</Card>
			)}

			{/* Sélecteur de méthode d'authentification */}
			<Card>
				<CardHeader>
					<CardTitle className="flex items-center space-x-2">
						<Settings className="w-5 h-5" />
						<span>{t("githubCopilot.authMethod.title")}</span>
					</CardTitle>
					<CardDescription>
						{t("githubCopilot.authMethod.description")}
					</CardDescription>
				</CardHeader>
				<CardContent>
					<div className="space-y-4">
						<div className="w-full max-w-sm">
							<Label
								htmlFor="auth-method-select"
								className="text-sm font-medium"
							>
								{t("githubCopilot.authMethod.selectLabel")}
							</Label>
							<Select
								value={authMethod}
								onValueChange={(value: "terminal" | "token") =>
									setAuthMethod(value)
								}
							>
								<SelectTrigger>
									<SelectValue
										placeholder={t(
											"githubCopilot.authMethod.selectPlaceholder",
										)}
									/>
								</SelectTrigger>
								<SelectContent>
									<SelectItem value="terminal">
										<div className="flex items-center space-x-2">
											<LogIn className="w-4 h-4" />
											<span>{t("githubCopilot.authMethod.terminal")}</span>
										</div>
									</SelectItem>
									<SelectItem value="token">
										<div className="flex items-center space-x-2">
											<Key className="w-4 h-4" />
											<span>{t("githubCopilot.authMethod.token")}</span>
										</div>
									</SelectItem>
								</SelectContent>
							</Select>
						</div>

						{/* Interface pour la méthode token */}
						{authMethod === "token" && (
							<div className="space-y-4 p-4 border rounded-lg bg-muted/50">
								<div className="space-y-2">
									<Label htmlFor="token-input" className="text-sm font-medium">
										{t("githubCopilot.token.inputLabel")}
									</Label>
									<Input
										id="token-input"
										type="password"
										value={tokenInput}
										onChange={(e) => setTokenInput(e.target.value)}
										placeholder={t("githubCopilot.token.inputPlaceholder")}
										className="font-mono text-sm"
									/>
								</div>
								<div className="flex flex-wrap gap-2">
									<Button
										size="sm"
										onClick={handleSaveToken}
										disabled={!tokenInput.trim() || isLoading}
									>
										<Key className="w-4 h-4 mr-1" />
										{t("githubCopilot.token.save")}
									</Button>
									{config.token && (
										<Button
											variant="outline"
											size="sm"
											onClick={handleRemoveToken}
											disabled={isLoading}
										>
											<LogOut className="w-4 h-4 mr-1" />
											{t("githubCopilot.token.remove")}
										</Button>
									)}
								</div>
								{config.token && (
									<div className="text-sm text-muted-foreground">
										{t("githubCopilot.token.currentStatus")}{" "}
										<Badge variant="outline" className="text-xs">
											{t("githubCopilot.token.configured")}
										</Badge>
									</div>
								)}
							</div>
						)}
					</div>
				</CardContent>
			</Card>

			{/* Instructions */}
			<Card>
				<CardHeader>
					<CardTitle>{t("githubCopilot.instructions.title")}</CardTitle>
				</CardHeader>
				<CardContent>
					<div className="space-y-4 text-sm">
						{authMethod === "terminal" ? (
							<div>
								<h4 className="font-medium">
									{t("githubCopilot.instructions.authentication.title")}
								</h4>
								<ol className="list-decimal list-inside space-y-1 ml-4">
									<li>
										{t("githubCopilot.instructions.authentication.step1")}
									</li>
									<li>
										{t("githubCopilot.instructions.authentication.step2")}
									</li>
									<li>
										{t("githubCopilot.instructions.authentication.step3")}
									</li>
								</ol>
							</div>
						) : (
							<div>
								<h4 className="font-medium">
									{t("githubCopilot.instructions.token.title")}
								</h4>
								<ol className="list-decimal list-inside space-y-1 ml-4">
									<li>{t("githubCopilot.instructions.token.step1")}</li>
									<li>{t("githubCopilot.instructions.token.step2")}</li>
									<li>{t("githubCopilot.instructions.token.step3")}</li>
								</ol>
							</div>
						)}
					</div>
				</CardContent>
			</Card>
		</div>
	);
}

export default GitHubCopilotConfig;
