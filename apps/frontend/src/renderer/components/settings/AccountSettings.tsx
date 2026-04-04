/**
 * AccountSettings - Unified account management for Claude Code and Custom Endpoints
 *
 * Consolidates the former "Integrations" and "API Profiles" settings into a single
 * tabbed interface with shared automatic account switching controls.
 *
 * Structure:
 * - Tabs: "Claude Code" (OAuth accounts) | "Custom Endpoints" (API profiles)
 * - Persistent: Automatic Account Switching section (below tabs)
 */

import type { APIProfile } from "@shared/types/profile";
import {
	AlertCircle,
	Check,
	ChevronDown,
	ChevronRight,
	Clock,
	Eye,
	EyeOff,
	Globe,
	Loader2,
	LogIn,
	Pencil,
	Plus,
	RefreshCw,
	Server,
	Star,
	Trash2,
	TrendingUp,
	Users,
	X,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { ProviderService } from "../../../shared/services/providerService";
import type {
	AppSettings,
	ClaudeAutoSwitchSettings,
	ClaudeProfile,
	ProfileUsageSummary,
} from "../../../shared/types";
import {
	API_BASE,
	type CanonicalProvider,
	getStaticProviders,
} from "../../../shared/utils/providers";
import { useToast } from "../../hooks/use-toast";
import { maskApiKey } from "../../lib/profile-utils";
import { cn } from "../../lib/utils";
import { loadClaudeProfiles as loadGlobalClaudeProfiles } from "../../stores/claude-profile-store";
import { useProviderRefreshStore } from "../../stores/provider-refresh-store";
import { useSettingsStore } from "../../stores/settings-store";
import {
	AlertDialog,
	AlertDialogAction,
	AlertDialogCancel,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from "../ui/alert-dialog";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";
import {
	Tooltip,
	TooltipContent,
	TooltipProvider,
	TooltipTrigger,
} from "../ui/tooltip";
import type { UnifiedAccount } from "./AccountPriorityList";
import { AuthTerminal } from "./AuthTerminal";
import { CopilotOAuthAuth } from "./CopilotOAuthAuth";
import { ProfileEditDialog } from "./ProfileEditDialog";
import { SettingsSection } from "./SettingsSection";

interface AccountSettingsProps {
	readonly settings: AppSettings;
	readonly onSettingsChange: (settings: AppSettings) => void;
	readonly isOpen: boolean;
	readonly connector: {
		readonly id: string;
		readonly label: string;
	};
	readonly showAutoSwitching?: boolean;
}

/**
 * Unified account settings with tabs for Claude Code and Custom Endpoints
 */
export function AccountSettings({
	settings,
	onSettingsChange,
	isOpen,
	connector,
	showAutoSwitching: _showAutoSwitching = true,
}: AccountSettingsProps) {
	const { t } = useTranslation("settings");
	const { t: tCommon } = useTranslation("common");
	const { toast } = useToast();
	const { triggerRefresh } = useProviderRefreshStore();

	// Tab state
	const [activeTab, setActiveTab] = useState<
		"claude-code" | "custom-endpoints"
	>("claude-code");

	// ============================================
	// Claude Code (OAuth) state
	// ============================================
	const [claudeProfiles, setClaudeProfiles] = useState<ClaudeProfile[]>([]);
	const [activeClaudeProfileId, setActiveClaudeProfileId] = useState<
		string | null
	>(null);
	const [isLoadingProfiles, setIsLoadingProfiles] = useState(false);
	const [newProfileName, setNewProfileName] = useState("");
	const [isAddingProfile, setIsAddingProfile] = useState(false);
	const [deletingProfileId, setDeletingProfileId] = useState<string | null>(
		null,
	);
	const [editingProfileId, setEditingProfileId] = useState<string | null>(null);
	const [editingProfileName, setEditingProfileName] = useState("");
	const [authenticatingProfileId, setAuthenticatingProfileId] = useState<
		string | null
	>(null);
	const [expandedTokenProfileId, setExpandedTokenProfileId] = useState<
		string | null
	>(null);
	const [manualToken, setManualToken] = useState("");
	const [manualTokenEmail, setManualTokenEmail] = useState("");
	const [showManualToken, setShowManualToken] = useState(false);
	const [savingTokenProfileId, setSavingTokenProfileId] = useState<
		string | null
	>(null);

	// Auth terminal state
	const [authTerminal, setAuthTerminal] = useState<{
		terminalId: string;
		configDir: string;
		profileId: string;
		profileName: string;
	} | null>(null);

	// ============================================
	// Custom Endpoints (API Profiles) state
	// ============================================
	const {
		profiles: apiProfiles,
		activeProfileId: activeApiProfileId,
		deleteProfile: deleteApiProfile,
		setActiveProfile: setActiveApiProfile,
		profilesError,
	} = useSettingsStore();

	const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
	const [editApiProfile, setEditApiProfile] = useState<APIProfile | null>(null);
	const [deleteConfirmProfile, setDeleteConfirmProfile] =
		useState<APIProfile | null>(null);
	const [isDeletingApiProfile, setIsDeletingApiProfile] = useState(false);
	const [isSettingActiveApiProfile, setIsSettingActiveApiProfile] =
		useState(false);

	// ============================================
	// Auto-switch settings state (shared)
	// ============================================
	const [_autoSwitchSettings, setAutoSwitchSettings] =
		useState<ClaudeAutoSwitchSettings | null>(null);
	const [_isLoadingAutoSwitch, setIsLoadingAutoSwitch] = useState(false);

	// ============================================
	// Priority order state
	// ============================================
	const [priorityOrder, setPriorityOrder] = useState<string[]>([]);
	const [_isSavingPriority, setIsSavingPriority] = useState(false);

	// ============================================
	// Usage data state (for priority list visualization)
	// ============================================
	const [profileUsageData, setProfileUsageData] = useState<
		Map<string, ProfileUsageSummary>
	>(new Map());

	// Authenticated providers (Copilot, OpenAI, etc.) for priority list
	const [authenticatedProviders, setAuthenticatedProviders] = useState<
		Array<{
			id: string;
			name: string;
			label: string;
			isAuthenticated: boolean;
			username?: string;
		}>
	>([]);

	// Providers LLM state
	const [_providers, setProviders] = useState<CanonicalProvider[]>([]);

	// Gestion dynamique des connecteurs LLM (hors Claude)
	const [apiKeyVisible, setApiKeyVisible] = useState(false);
	const [authStatus, setAuthStatus] = useState<
		"idle" | "loading" | "success" | "error"
	>("idle");
	const [authMessage, setAuthMessage] = useState<string>("");
	const [showRevokeDialog, setShowRevokeDialog] = useState(false);

	const [apiKeyField, setApiKeyField] = useState<string | null>(null);
	const [apiKeyValue, setApiKeyValue] = useState("");

	// Charge le champ API key depuis le service centralisé
	useEffect(() => {
		const loadApiKeyField = async () => {
			const field = await ProviderService.getApiKeyField(connector.id);
			setApiKeyField(field);
			setApiKeyValue(
				field ? String(settings[field as keyof AppSettings] || "") : "",
			);
		};
		loadApiKeyField();
	}, [connector.id, settings]);

	// Detect authenticated providers for the priority list
	useEffect(() => {
		const detectAuthenticatedProviders = async () => {
			const provs: Array<{
				id: string;
				name: string;
				label: string;
				isAuthenticated: boolean;
				username?: string;
			}> = [];

			// Check Copilot via GitHub CLI
			try {
				const copilotResult = await globalThis.electronAPI.checkCopilotAuth();
				if (copilotResult.success && copilotResult.data?.authenticated) {
					provs.push({
						id: "copilot",
						name: "copilot",
						label: "GitHub Copilot",
						isAuthenticated: true,
						username: copilotResult.data.username,
					});
				}
			} catch {
				/* ignore */
			}

			// Check API-key based providers from settings
			const apiKeyProviders: Array<{
				name: string;
				label: string;
				key: keyof AppSettings;
			}> = [
				{ name: "openai", label: "OpenAI", key: "globalOpenAIApiKey" },
				{
					name: "google",
					label: "Google (Gemini)",
					key: "globalGoogleDeepMindApiKey",
				},
				{ name: "mistral", label: "Mistral AI", key: "globalMistralApiKey" },
				{ name: "grok", label: "Grok (xAI)", key: "globalGrokApiKey" },
				{ name: "deepseek", label: "DeepSeek", key: "globalDeepSeekApiKey" },
				{ name: "aws", label: "AWS (Bedrock)", key: "globalAWSApiKey" },
			];
			for (const p of apiKeyProviders) {
				const val = settings[p.key];
				if (val && typeof val === "string" && val.trim().length > 0) {
					provs.push({
						id: p.name,
						name: p.name,
						label: p.label,
						isAuthenticated: true,
					});
				}
			}

			setAuthenticatedProviders(provs);
		};

		if (isOpen) {
			detectAuthenticatedProviders();
		}
	}, [isOpen, settings]);

	const handleApiKeyChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		if (apiKeyField) {
			onSettingsChange({ ...settings, [apiKeyField]: e.target.value });
			setApiKeyValue(e.target.value);
			setAuthStatus("idle");
			setAuthMessage("");
		}
	};
	const handleApiKeyClear = () => {
		setShowRevokeDialog(true);
	};
	const confirmRevokeApiKey = () => {
		if (apiKeyField) {
			onSettingsChange({ ...settings, [apiKeyField]: "" });
			setAuthStatus("idle");
			setAuthMessage("");
		}
		setShowRevokeDialog(false);
	};

	// Test d'authentification pour chaque provider (API call minimal)
	const handleTestApiKey = async () => {
		if (!apiKeyField || !apiKeyValue) return;
		setAuthStatus("loading");
		setAuthMessage("");
		try {
			// biome-ignore lint/suspicious/noImplicitAnyLet: type inferred from assignment
			let response;
			switch (connector.id) {
				case "openai":
					response = await fetch("https://api.openai.com/v1/models", {
						headers: { Authorization: `Bearer ${apiKeyValue}` },
					});
					if (response.ok) {
						setAuthStatus("success");
						setAuthMessage("Clé valide !");
						await validateApiKeyBackend("openai", apiKeyValue); // Ajout
						triggerRefresh();
					} else {
						setAuthStatus("error");
						setAuthMessage("Clé invalide ou permissions insuffisantes.");
					}
					break;
				case "gemini":
					response = await fetch(
						`https://generativelanguage.googleapis.com/v1/models?key=${apiKeyValue}`,
					);
					if (response.ok) {
						setAuthStatus("success");
						setAuthMessage("Clé valide !");
						await validateApiKeyBackend("google", apiKeyValue);
						triggerRefresh();
					} else {
						setAuthStatus("error");
						setAuthMessage("Clé invalide ou permissions insuffisantes.");
					}
					break;
				case "meta-llama":
					response = await fetch("https://api.together.xyz/v1/models", {
						headers: { Authorization: `Bearer ${apiKeyValue}` },
					});
					if (response.ok) {
						setAuthStatus("success");
						setAuthMessage("Clé valide (provider Together ou compatible) !");
						await validateApiKeyBackend("meta", apiKeyValue);
						triggerRefresh();
					} else {
						setAuthStatus("error");
						setAuthMessage("Clé invalide ou provider non supporté.");
					}
					break;
				case "mistral":
					response = await fetch("https://api.mistral.ai/v1/models", {
						headers: { Authorization: `Bearer ${apiKeyValue}` },
					});
					if (response.ok) {
						setAuthStatus("success");
						setAuthMessage("Clé valide !");
						await validateApiKeyBackend("mistral", apiKeyValue);
						triggerRefresh();
					} else {
						setAuthStatus("error");
						setAuthMessage("Clé invalide ou permissions insuffisantes.");
					}
					break;
				case "deepseek":
					response = await fetch("https://api.deepseek.com/v1/models", {
						headers: { Authorization: `Bearer ${apiKeyValue}` },
					});
					if (response.ok) {
						setAuthStatus("success");
						setAuthMessage("Clé valide !");
						await validateApiKeyBackend("deepseek", apiKeyValue);
						triggerRefresh();
					} else {
						setAuthStatus("error");
						setAuthMessage("Clé invalide ou permissions insuffisantes.");
					}
					break;
				case "grok":
					response = await fetch("https://api.x.ai/v1/models", {
						headers: { Authorization: `Bearer ${apiKeyValue}` },
					});
					if (response.ok) {
						setAuthStatus("success");
						setAuthMessage("Clé xAI valide !");
						await validateApiKeyBackend("grok", apiKeyValue);
						triggerRefresh();
					} else {
						setAuthStatus("error");
						setAuthMessage("Clé xAI invalide ou permissions insuffisantes.");
					}
					break;
				case "azure-openai":
					setAuthStatus("success");
					setAuthMessage("Clé enregistrée (test complet via Azure Portal).");
					await validateApiKeyBackend("azure-openai", apiKeyValue);
					triggerRefresh();
					break;
				case "google":
					response = await fetch(
						`https://generativelanguage.googleapis.com/v1/models?key=${apiKeyValue}`,
					);
					if (response.ok) {
						setAuthStatus("success");
						setAuthMessage("Clé Google DeepMind valide !");
						await validateApiKeyBackend("google", apiKeyValue);
						triggerRefresh();
					} else {
						setAuthStatus("error");
						setAuthMessage(
							"Clé Google DeepMind invalide ou permissions insuffisantes.",
						);
					}
					break;
				case "meta":
					response = await fetch("https://api.meta.ai/v1/models", {
						headers: { Authorization: `Bearer ${apiKeyValue}` },
					});
					if (response.ok) {
						setAuthStatus("success");
						setAuthMessage("Clé Meta valide !");
						await validateApiKeyBackend("meta", apiKeyValue);
						triggerRefresh();
					} else {
						setAuthStatus("error");
						setAuthMessage("Clé Meta invalide ou permissions insuffisantes.");
					}
					break;
				case "aws":
					response = await fetch(
						"https://bedrock-runtime.amazonaws.com/models",
						{
							headers: {
								Authorization: `AWS4-HMAC-SHA256 Credential=${apiKeyValue}`,
							},
						},
					);
					if (response.ok) {
						setAuthStatus("success");
						setAuthMessage("Clé AWS valide !");
						await validateApiKeyBackend("aws", apiKeyValue);
						triggerRefresh();
					} else {
						setAuthStatus("error");
						setAuthMessage("Clé AWS invalide ou permissions insuffisantes.");
					}
					break;
				default:
					setAuthStatus("idle");
					setAuthMessage("");
			}
		} catch (_e) {
			setAuthStatus("error");
			setAuthMessage("Erreur réseau ou clé invalide.");
		}
	};

	const validateApiKeyBackend = async (provider: string, apiKey: string) => {
		try {
			const res = await fetch(`${API_BASE}/providers/validate/${provider}`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ api_key: apiKey }),
			});

			if (!res.ok) {
				throw new Error(`HTTP ${res.status}`);
			}

			await res.json();
		} catch (e) {
			console.error("Failed to validate API key:", e);
			// Optionnel : afficher une erreur toast
		}
	};

	// Fetch all profiles usage data
	// Force refresh to get fresh data when Settings opens (bypasses 1-minute cache)
	const loadProfileUsageData = useCallback(
		async (forceRefresh: boolean = false) => {
			try {
				const result =
					await globalThis.electronAPI.requestAllProfilesUsage?.(forceRefresh);
				if (result?.success && result.data) {
					const usageMap = new Map<string, ProfileUsageSummary>();
					result.data.allProfiles.forEach((profile: ProfileUsageSummary) => {
						usageMap.set(profile.profileId, profile);
					});
					setProfileUsageData(usageMap);
				}
			} catch (err) {
				console.warn(
					"[AccountSettings] Failed to load profile usage data:",
					err,
				);
			}
		},
		[],
	);

	// Build unified accounts list from both OAuth and API profiles
	const buildUnifiedAccounts = useCallback((): UnifiedAccount[] => {
		const unifiedList: UnifiedAccount[] = [];

		// Add OAuth profiles with usage data
		claudeProfiles.forEach((profile) => {
			const usageData = profileUsageData.get(profile.id);
			unifiedList.push({
				id: `oauth-${profile.id}`,
				name: profile.name,
				type: "oauth",
				displayName: profile.name,
				identifier: profile.email || t("accounts.priority.noEmail"),
				isActive: profile.id === activeClaudeProfileId && !activeApiProfileId,
				isNext: false, // Will be computed by AccountPriorityList
				isAvailable: profile.isAuthenticated ?? false,
				hasUnlimitedUsage: false,
				// Use real usage data from the usage monitor
				sessionPercent: usageData?.sessionPercent,
				weeklyPercent: usageData?.weeklyPercent,
				isRateLimited: usageData?.isRateLimited,
				rateLimitType: usageData?.rateLimitType,
				isAuthenticated: profile.isAuthenticated,
				needsReauthentication: usageData?.needsReauthentication,
			});
		});

		// Add API profiles
		apiProfiles.forEach((profile) => {
			unifiedList.push({
				id: `api-${profile.id}`,
				name: profile.name,
				type: "api",
				displayName: profile.name,
				identifier: profile.baseUrl,
				isActive: profile.id === activeApiProfileId,
				isNext: false, // Will be computed by AccountPriorityList
				isAvailable: true, // API profiles are always considered available
				hasUnlimitedUsage: true, // API profiles have no rate limits
				sessionPercent: undefined,
				weeklyPercent: undefined,
			});
		});

		// Add authenticated providers (Copilot, OpenAI, etc.)
		authenticatedProviders.forEach((prov) => {
			const alreadyInList = unifiedList.some(
				(a) => a.name === prov.name || a.id === prov.id,
			);
			if (!alreadyInList) {
				unifiedList.push({
					id: prov.id,
					name: prov.name,
					type: "api",
					displayName: prov.label,
					identifier: prov.username
						? `@${prov.username}`
						: t("accounts.priority.providerAuth"),
					isActive: false,
					isNext: false,
					isAvailable: true,
					hasUnlimitedUsage: prov.name !== "copilot",
					sessionPercent: undefined,
					weeklyPercent: undefined,
					isAuthenticated: true,
				});
			}
		});

		// Sort by priority order if available
		if (priorityOrder.length > 0) {
			unifiedList.sort((a, b) => {
				const aIndex = priorityOrder.indexOf(a.id);
				const bIndex = priorityOrder.indexOf(b.id);
				// Items not in priority order go to the end
				const aPos = aIndex === -1 ? Infinity : aIndex;
				const bPos = bIndex === -1 ? Infinity : bIndex;
				return aPos - bPos;
			});
		}

		return unifiedList;
	}, [
		claudeProfiles,
		apiProfiles,
		activeClaudeProfileId,
		activeApiProfileId,
		priorityOrder,
		profileUsageData,
		authenticatedProviders,
		t,
	]);

	const _unifiedAccounts = buildUnifiedAccounts();

	// Load priority order from settings
	const loadPriorityOrder = async () => {
		try {
			const result = await globalThis.electronAPI.getAccountPriorityOrder();
			if (result.success && result.data) {
				setPriorityOrder(result.data);
			}
		} catch (err) {
			console.warn("[AccountSettings] Failed to load priority order:", err);
		}
	};

	// Save priority order
	const handlePriorityReorder = async (newOrder: string[]) => {
		setPriorityOrder(newOrder);
		setIsSavingPriority(true);
		try {
			await globalThis.electronAPI.setAccountPriorityOrder(newOrder);
		} catch (err) {
			console.warn("[AccountSettings] Failed to save priority order:", err);
			toast({
				variant: "destructive",
				title: t("accounts.toast.settingsUpdateFailed"),
				description: t("accounts.toast.tryAgain"),
			});
		} finally {
			setIsSavingPriority(false);
		}
	};

	// Load data when section is opened
	// eslint-disable-next-line react-hooks/exhaustive-deps
	// biome-ignore lint/correctness/useExhaustiveDependencies: intentional dependency omission
	useEffect(() => {
		if (isOpen) {
			loadClaudeProfiles();
			loadAutoSwitchSettings();
			loadPriorityOrder();
			// Force refresh usage data when Settings opens to get fresh data
			// This bypasses the 1-minute cache to ensure accurate duplicate detection
			loadProfileUsageData(true);
		}
	}, [isOpen, loadProfileUsageData]);

	// Subscribe to usage updates for real-time data
	useEffect(() => {
		const unsubscribe = globalThis.electronAPI.onAllProfilesUsageUpdated?.(
			(allProfilesUsage) => {
				const usageMap = new Map<string, ProfileUsageSummary>();
				allProfilesUsage.allProfiles.forEach((profile) => {
					usageMap.set(profile.profileId, profile);
				});
				setProfileUsageData(usageMap);
			},
		);

		return () => {
			unsubscribe?.();
		};
	}, []);

	// ============================================
	// Claude Code (OAuth) handlers
	// ============================================
	const loadClaudeProfiles = async () => {
		setIsLoadingProfiles(true);
		try {
			const result = await globalThis.electronAPI.getClaudeProfiles();
			if (result.success && result.data) {
				setClaudeProfiles(result.data.profiles);
				setActiveClaudeProfileId(result.data.activeProfileId);
				await loadGlobalClaudeProfiles();
			} else if (!result.success) {
				toast({
					variant: "destructive",
					title: t("accounts.toast.loadProfilesFailed"),
					description: result.error || t("accounts.toast.tryAgain"),
				});
			}
		} catch (err) {
			console.warn("[AccountSettings] Failed to load Claude profiles:", err);
			toast({
				variant: "destructive",
				title: t("accounts.toast.loadProfilesFailed"),
				description: t("accounts.toast.tryAgain"),
			});
		} finally {
			setIsLoadingProfiles(false);
		}
	};

	const handleAddClaudeProfile = async () => {
		if (!newProfileName.trim()) return;

		setIsAddingProfile(true);
		try {
			const profileName = newProfileName.trim();
			const profileSlug = profileName.toLowerCase().replaceAll(/\s+/g, "-");

			const result = await globalThis.electronAPI.saveClaudeProfile({
				id: `profile-${Date.now()}`,
				name: profileName,
				configDir: `~/.claude-profiles/${profileSlug}`,
				isDefault: false,
				createdAt: new Date(),
			});

			if (result.success && result.data) {
				await loadClaudeProfiles();
				setNewProfileName("");

				const authResult =
					await globalThis.electronAPI.authenticateClaudeProfile(
						result.data.id,
					);
				if (authResult.success && authResult.data) {
					setAuthenticatingProfileId(result.data.id);
					setAuthTerminal({
						terminalId: authResult.data.terminalId,
						configDir: authResult.data.configDir,
						profileId: result.data.id,
						profileName,
					});
				} else {
					toast({
						variant: "destructive",
						title: t("accounts.toast.authFailed"),
						description: authResult.error || t("accounts.toast.tryAgain"),
					});
				}
			} else {
				toast({
					variant: "destructive",
					title: t("accounts.toast.addProfileFailed"),
					description: result.error || t("accounts.toast.tryAgain"),
				});
			}
		} catch (err) {
			console.error("Failed to add Claude profile:", err);

			// Handle specific error types
			if (err instanceof Error) {
				if (
					err.message.includes("EACCES") ||
					err.message.includes("permission")
				) {
					toast({
						variant: "destructive",
						title: t("accounts.toast.permissionDenied"),
						description: t("accounts.toast.checkFilePermissions"),
					});
				} else if (
					err.message.includes("ENOENT") ||
					err.message.includes("not found")
				) {
					toast({
						variant: "destructive",
						title: t("accounts.toast.pathNotFound"),
						description: t("accounts.toast.checkPath"),
					});
				} else {
					toast({
						variant: "destructive",
						title: t("accounts.toast.addProfileFailed"),
						description: err.message || t("accounts.toast.tryAgain"),
					});
				}
			} else {
				toast({
					variant: "destructive",
					title: t("accounts.toast.addProfileFailed"),
					description: t("accounts.toast.tryAgain"),
				});
			}
		} finally {
			setIsAddingProfile(false);
		}
	};

	const handleDeleteClaudeProfile = async (profileId: string) => {
		setDeletingProfileId(profileId);
		try {
			const result =
				await globalThis.electronAPI.deleteClaudeProfile(profileId);
			if (result.success) {
				await loadClaudeProfiles();
				// Remove from priority order
				const unifiedId = `oauth-${profileId}`;
				if (priorityOrder.includes(unifiedId)) {
					const newOrder = priorityOrder.filter((id) => id !== unifiedId);
					await handlePriorityReorder(newOrder);
				}
			} else {
				toast({
					variant: "destructive",
					title: t("accounts.toast.deleteProfileFailed"),
					description: result.error || t("accounts.toast.tryAgain"),
				});
			}
		} catch (_err) {
			toast({
				variant: "destructive",
				title: t("accounts.toast.deleteProfileFailed"),
				description: t("accounts.toast.tryAgain"),
			});
		} finally {
			setDeletingProfileId(null);
		}
	};

	const startEditingProfile = (profile: ClaudeProfile) => {
		setEditingProfileId(profile.id);
		setEditingProfileName(profile.name);
	};

	const cancelEditingProfile = () => {
		setEditingProfileId(null);
		setEditingProfileName("");
	};

	const handleRenameProfile = async () => {
		if (!editingProfileId || !editingProfileName.trim()) return;

		try {
			const result = await globalThis.electronAPI.renameClaudeProfile(
				editingProfileId,
				editingProfileName.trim(),
			);
			if (result.success) {
				await loadClaudeProfiles();
			} else {
				toast({
					variant: "destructive",
					title: t("accounts.toast.renameProfileFailed"),
					description: result.error || t("accounts.toast.tryAgain"),
				});
			}
		} catch (_err) {
			toast({
				variant: "destructive",
				title: t("accounts.toast.renameProfileFailed"),
				description: t("accounts.toast.tryAgain"),
			});
		} finally {
			setEditingProfileId(null);
			setEditingProfileName("");
		}
	};

	const handleSetActiveClaudeProfile = async (profileId: string) => {
		try {
			// If an API profile is currently active, clear it first
			// so the OAuth profile becomes the active account
			if (activeApiProfileId) {
				await setActiveApiProfile(null);
			}

			const result =
				await globalThis.electronAPI.setActiveClaudeProfile(profileId);
			if (result.success) {
				setActiveClaudeProfileId(profileId);
				await loadGlobalClaudeProfiles();
			} else {
				toast({
					variant: "destructive",
					title: t("accounts.toast.setActiveProfileFailed"),
					description: result.error || t("accounts.toast.tryAgain"),
				});
			}
		} catch (_err) {
			toast({
				variant: "destructive",
				title: t("accounts.toast.setActiveProfileFailed"),
				description: t("accounts.toast.tryAgain"),
			});
		}
	};

	const handleAuthenticateProfile = async (profileId: string) => {
		const profile = claudeProfiles.find((p) => p.id === profileId);
		const profileName = profile?.name || "Profile";

		setAuthenticatingProfileId(profileId);
		try {
			const result =
				await globalThis.electronAPI.authenticateClaudeProfile(profileId);
			if (!result.success || !result.data) {
				toast({
					variant: "destructive",
					title: t("accounts.toast.authFailed"),
					description: result.error || t("accounts.toast.tryAgain"),
				});
				setAuthenticatingProfileId(null);
				return;
			}

			setAuthTerminal({
				terminalId: result.data.terminalId,
				configDir: result.data.configDir,
				profileId,
				profileName,
			});
		} catch (err) {
			console.error("Failed to authenticate profile:", err);
			toast({
				variant: "destructive",
				title: t("accounts.toast.authFailed"),
				description: t("accounts.toast.tryAgain"),
			});
			setAuthenticatingProfileId(null);
		}
	};

	const handleAuthTerminalClose = useCallback(() => {
		setAuthTerminal(null);
		setAuthenticatingProfileId(null);
	}, []);

	const handleAuthTerminalSuccess = useCallback(async () => {
		setAuthTerminal(null);
		setAuthenticatingProfileId(null);
		await loadClaudeProfiles();
		// biome-ignore lint/correctness/useExhaustiveDependencies: intentional dependency omission
	}, [loadClaudeProfiles]);

	const handleAuthTerminalError = useCallback(() => {
		// Don't auto-close on error
	}, []);

	const toggleTokenEntry = (profileId: string) => {
		if (expandedTokenProfileId === profileId) {
			setExpandedTokenProfileId(null);
			setManualToken("");
			setManualTokenEmail("");
			setShowManualToken(false);
		} else {
			setExpandedTokenProfileId(profileId);
			setManualToken("");
			setManualTokenEmail("");
			setShowManualToken(false);
		}
	};

	const handleSaveManualToken = async (profileId: string) => {
		if (!manualToken.trim()) return;

		setSavingTokenProfileId(profileId);
		try {
			const result = await globalThis.electronAPI.setClaudeProfileToken(
				profileId,
				manualToken.trim(),
				manualTokenEmail.trim() || undefined,
			);
			if (result.success) {
				await loadClaudeProfiles();
				setExpandedTokenProfileId(null);
				setManualToken("");
				setManualTokenEmail("");
				setShowManualToken(false);
				toast({
					title: t("accounts.toast.tokenSaved"),
					description: t("accounts.toast.tokenSavedDescription"),
				});
			} else {
				toast({
					variant: "destructive",
					title: t("accounts.toast.tokenSaveFailed"),
					description: result.error || t("accounts.toast.tryAgain"),
				});
			}
		} catch (_err) {
			toast({
				variant: "destructive",
				title: t("accounts.toast.tokenSaveFailed"),
				description: t("accounts.toast.tryAgain"),
			});
		} finally {
			setSavingTokenProfileId(null);
		}
	};

	// ============================================
	// Custom Endpoints (API Profiles) handlers
	// ============================================
	const handleDeleteApiProfile = async () => {
		if (!deleteConfirmProfile) return;

		setIsDeletingApiProfile(true);
		const success = await deleteApiProfile(deleteConfirmProfile.id);
		setIsDeletingApiProfile(false);

		if (success) {
			toast({
				title: t("apiProfiles.toast.delete.title"),
				description: t("apiProfiles.toast.delete.description", {
					name: deleteConfirmProfile.name,
				}),
			});
			// Remove from priority order
			const unifiedId = `api-${deleteConfirmProfile.id}`;
			if (priorityOrder.includes(unifiedId)) {
				const newOrder = priorityOrder.filter((id) => id !== unifiedId);
				await handlePriorityReorder(newOrder);
			}
			setDeleteConfirmProfile(null);
		} else {
			toast({
				variant: "destructive",
				title: t("apiProfiles.toast.delete.errorTitle"),
				description:
					profilesError || t("apiProfiles.toast.delete.errorFallback"),
			});
		}
	};

	const handleSetActiveApiProfileClick = async (profileId: string | null) => {
		if (profileId !== null && profileId === activeApiProfileId) return;

		setIsSettingActiveApiProfile(true);
		const success = await setActiveApiProfile(profileId);
		setIsSettingActiveApiProfile(false);

		if (success) {
			if (profileId === null) {
				toast({
					title: t("apiProfiles.toast.switch.oauthTitle"),
					description: t("apiProfiles.toast.switch.oauthDescription"),
				});
			} else {
				const activeProfile = apiProfiles.find((p) => p.id === profileId);
				if (activeProfile) {
					toast({
						title: t("apiProfiles.toast.switch.profileTitle"),
						description: t("apiProfiles.toast.switch.profileDescription", {
							name: activeProfile.name,
						}),
					});
				}
			}
		} else {
			toast({
				variant: "destructive",
				title: t("apiProfiles.toast.switch.errorTitle"),
				description:
					profilesError || t("apiProfiles.toast.switch.errorFallback"),
			});
		}
	};

	const getHostFromUrl = (url: string): string => {
		try {
			return new URL(url).host;
		} catch {
			return url;
		}
	};

	// ============================================
	// Auto-switch settings handlers (shared)
	// ============================================
	const loadAutoSwitchSettings = async () => {
		setIsLoadingAutoSwitch(true);
		try {
			const result = await globalThis.electronAPI.getAutoSwitchSettings();
			if (result.success && result.data) {
				setAutoSwitchSettings(result.data);
			}
		} catch (err) {
			console.warn(
				"[AccountSettings] Failed to load auto-switch settings:",
				err,
			);
		} finally {
			setIsLoadingAutoSwitch(false);
		}
	};

	const _handleUpdateAutoSwitch = async (
		updates: Partial<ClaudeAutoSwitchSettings>,
	) => {
		setIsLoadingAutoSwitch(true);
		try {
			const result =
				await globalThis.electronAPI.updateAutoSwitchSettings(updates);
			if (result.success) {
				await loadAutoSwitchSettings();
			} else {
				toast({
					variant: "destructive",
					title: t("accounts.toast.settingsUpdateFailed"),
					description: result.error || t("accounts.toast.tryAgain"),
				});
			}
		} catch (_err) {
			toast({
				variant: "destructive",
				title: t("accounts.toast.settingsUpdateFailed"),
				description: t("accounts.toast.tryAgain"),
			});
		} finally {
			setIsLoadingAutoSwitch(false);
		}
	};

	// Load providers on open
	useEffect(() => {
		if (isOpen) {
			const loadProviders = async () => {
				const response = await getStaticProviders();
				setProviders(response.providers || []);
			};
			loadProviders();
		}
	}, [isOpen]);

	// Affichage dynamique selon le connecteur
	return (
		<TooltipProvider>
			<div className="mb-8">
				<h3 className="text-lg font-semibold mb-2">{connector.label}</h3>
				{connector.id === "anthropic" || connector.id === "claude" ? (
					<SettingsSection
						title={t("accounts.title")}
						description={t("accounts.description")}
					>
						<div className="space-y-6">
							{/* Tabs for Claude Code vs Custom Endpoints */}
							<Tabs
								value={activeTab}
								onValueChange={(v) =>
									setActiveTab(v as "claude-code" | "custom-endpoints")
								}
							>
								<TabsList className="w-full justify-start">
									<TabsTrigger
										value="claude-code"
										className="flex items-center gap-2"
									>
										<Users className="h-4 w-4" />
										{t("accounts.tabs.claudeCode")}
									</TabsTrigger>
									<TabsTrigger
										value="custom-endpoints"
										className="flex items-center gap-2"
									>
										<Server className="h-4 w-4" />
										{t("accounts.tabs.customEndpoints")}
									</TabsTrigger>
								</TabsList>

								{/* Claude Code Tab Content */}
								<TabsContent value="claude-code">
									<div className="rounded-lg bg-muted/30 border border-border p-4">
										<p className="text-sm text-muted-foreground mb-4">
											{t("accounts.claudeCode.description")}
										</p>

										{/* Accounts list */}
										{isLoadingProfiles ? (
											<div className="flex items-center justify-center py-4">
												<Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
											</div>
										) : claudeProfiles.length === 0 ? (
											<div className="rounded-lg border border-dashed border-border p-4 text-center mb-4">
												<p className="text-sm text-muted-foreground">
													{t("accounts.claudeCode.noAccountsYet")}
												</p>
											</div>
										) : (
											<div className="space-y-2 mb-4">
												{claudeProfiles.map((profile) => {
													// Get usage data to check needsReauthentication flag
													const usageData = profileUsageData.get(profile.id);
													const needsReauth =
														usageData?.needsReauthentication ?? false;

													return (
														<div
															key={profile.id}
															className={cn(
																"rounded-lg border transition-colors",
																needsReauth
																	? "border-destructive/50 bg-destructive/5"
																	: profile.id === activeClaudeProfileId &&
																			!activeApiProfileId
																		? "border-primary bg-primary/5"
																		: "border-border bg-background",
															)}
														>
															<div
																className={cn(
																	"flex items-center justify-between p-3",
																	expandedTokenProfileId !== profile.id &&
																		"hover:bg-muted/50",
																)}
															>
																<div className="flex items-center gap-3">
																	<div
																		className={cn(
																			"h-7 w-7 rounded-full flex items-center justify-center text-xs font-medium shrink-0",
																			profile.id === activeClaudeProfileId &&
																				!activeApiProfileId
																				? "bg-primary text-primary-foreground"
																				: "bg-muted text-muted-foreground",
																		)}
																	>
																		{(editingProfileId === profile.id
																			? editingProfileName
																			: profile.name
																		)
																			.charAt(0)
																			.toUpperCase()}
																	</div>
																	<div className="min-w-0">
																		{editingProfileId === profile.id ? (
																			<div className="flex items-center gap-2">
																				<Input
																					value={editingProfileName}
																					onChange={(e) =>
																						setEditingProfileName(
																							e.target.value,
																						)
																					}
																					className="h-7 text-sm w-40"
																					autoFocus
																					onKeyDown={(e) => {
																						if (e.key === "Enter")
																							handleRenameProfile();
																						if (e.key === "Escape")
																							cancelEditingProfile();
																					}}
																				/>
																				<Button
																					variant="ghost"
																					size="icon"
																					onClick={handleRenameProfile}
																					className="h-7 w-7 text-success hover:text-success hover:bg-success/10"
																				>
																					<Check className="h-3 w-3" />
																				</Button>
																				<Button
																					variant="ghost"
																					size="icon"
																					onClick={cancelEditingProfile}
																					className="h-7 w-7 text-muted-foreground hover:text-foreground"
																				>
																					<X className="h-3 w-3" />
																				</Button>
																			</div>
																		) : (
																			<>
																				<div className="flex items-center gap-2 flex-wrap">
																					<span className="text-sm font-medium text-foreground">
																						{profile.name}
																					</span>
																					{profile.isDefault && (
																						<span className="text-xs bg-muted px-1.5 py-0.5 rounded">
																							{t("accounts.claudeCode.default")}
																						</span>
																					)}
																					{profile.id ===
																						activeClaudeProfileId &&
																						!activeApiProfileId && (
																							<span className="text-xs bg-primary/20 text-primary px-1.5 py-0.5 rounded flex items-center gap-1">
																								<Star className="h-3 w-3" />
																								{t(
																									"accounts.claudeCode.active",
																								)}
																							</span>
																						)}
																					{needsReauth ? (
																						<span className="text-xs bg-destructive/20 text-destructive px-1.5 py-0.5 rounded flex items-center gap-1">
																							<AlertCircle className="h-3 w-3" />
																							{t(
																								"accounts.priority.needsReauth",
																							)}
																						</span>
																					) : profile.isAuthenticated ? (
																						<span className="text-xs bg-success/20 text-success px-1.5 py-0.5 rounded flex items-center gap-1">
																							<Check className="h-3 w-3" />
																							{t(
																								"accounts.claudeCode.authenticated",
																							)}
																						</span>
																					) : (
																						<span className="text-xs bg-warning/20 text-warning px-1.5 py-0.5 rounded">
																							{t(
																								"accounts.claudeCode.needsAuth",
																							)}
																						</span>
																					)}
																				</div>
																				{profile.email && (
																					<span className="text-xs text-muted-foreground">
																						{profile.email}
																					</span>
																				)}
																				{/* Usage bars - show if we have usage data */}
																				{usageData &&
																					profile.isAuthenticated &&
																					!needsReauth && (
																						<div className="flex items-center gap-3 mt-1.5">
																							{/* Session usage */}
																							<div className="flex items-center gap-1.5">
																								<Clock className="h-3 w-3 text-muted-foreground" />
																								<div className="w-12 h-1.5 bg-muted rounded-full overflow-hidden">
																									<div
																										className={`h-full rounded-full ${
																											(
																												usageData.sessionPercent ??
																													0
																											) >= 95
																												? "bg-red-500"
																												: (usageData.sessionPercent ??
																															0) >= 91
																													? "bg-orange-500"
																													: (usageData.sessionPercent ??
																																0) >= 71
																														? "bg-yellow-500"
																														: "bg-green-500"
																										}`}
																										style={{
																											width: `${Math.min(usageData.sessionPercent ?? 0, 100)}%`,
																										}}
																									/>
																								</div>
																								<span
																									className={`text-[10px] tabular-nums w-7 ${
																										(
																											usageData.sessionPercent ??
																												0
																										) >= 95
																											? "text-red-500"
																											: (usageData.sessionPercent ??
																														0) >= 91
																												? "text-orange-500"
																												: (usageData.sessionPercent ??
																															0) >= 71
																													? "text-yellow-500"
																													: "text-muted-foreground"
																									}`}
																								>
																									{Math.round(
																										usageData.sessionPercent ??
																											0,
																									)}
																									%
																								</span>
																							</div>
																							{/* Weekly usage */}
																							<div className="flex items-center gap-1.5">
																								<TrendingUp className="h-3 w-3 text-muted-foreground" />
																								<div className="w-12 h-1.5 bg-muted rounded-full overflow-hidden">
																									<div
																										className={`h-full rounded-full ${
																											(
																												usageData.weeklyPercent ??
																													0
																											) >= 95
																												? "bg-red-500"
																												: (usageData.weeklyPercent ??
																															0) >= 91
																													? "bg-orange-500"
																													: (usageData.weeklyPercent ??
																																0) >= 71
																														? "bg-yellow-500"
																														: "bg-green-500"
																										}`}
																										style={{
																											width: `${Math.min(usageData.weeklyPercent ?? 0, 100)}%`,
																										}}
																									/>
																								</div>
																								<span
																									className={`text-[10px] tabular-nums w-7 ${
																										(
																											usageData.weeklyPercent ??
																												0
																										) >= 95
																											? "text-red-500"
																											: (usageData.weeklyPercent ??
																														0) >= 91
																												? "text-orange-500"
																												: (usageData.weeklyPercent ??
																															0) >= 71
																													? "text-yellow-500"
																													: "text-muted-foreground"
																									}`}
																								>
																									{Math.round(
																										usageData.weeklyPercent ??
																											0,
																									)}
																									%
																								</span>
																							</div>
																						</div>
																					)}
																			</>
																		)}
																	</div>
																</div>
																{editingProfileId !== profile.id && (
																	<div className="flex items-center gap-1">
																		{!profile.isAuthenticated ? (
																			<Button
																				variant="outline"
																				size="sm"
																				onClick={() =>
																					handleAuthenticateProfile(profile.id)
																				}
																				disabled={
																					authenticatingProfileId === profile.id
																				}
																				className="gap-1 h-7 text-xs"
																			>
																				{authenticatingProfileId ===
																				profile.id ? (
																					<>
																						<Loader2 className="h-3 w-3 animate-spin" />
																						{t(
																							"accounts.claudeCode.authenticating",
																						)}
																					</>
																				) : (
																					<>
																						<LogIn className="h-3 w-3" />
																						{t(
																							"accounts.claudeCode.authenticate",
																						)}
																					</>
																				)}
																			</Button>
																		) : (
																			<Tooltip>
																				<TooltipTrigger asChild>
																					<Button
																						variant="ghost"
																						size="icon"
																						onClick={() =>
																							handleAuthenticateProfile(
																								profile.id,
																							)
																						}
																						disabled={
																							authenticatingProfileId ===
																							profile.id
																						}
																						className="h-7 w-7 text-muted-foreground hover:text-foreground"
																					>
																						{authenticatingProfileId ===
																						profile.id ? (
																							<Loader2 className="h-3 w-3 animate-spin" />
																						) : (
																							<RefreshCw className="h-3 w-3" />
																						)}
																					</Button>
																				</TooltipTrigger>
																				<TooltipContent>
																					{tCommon(
																						"accessibility.reAuthenticateProfileAriaLabel",
																					)}
																				</TooltipContent>
																			</Tooltip>
																		)}
																		{(profile.id !== activeClaudeProfileId ||
																			activeApiProfileId) && (
																			<Button
																				variant="outline"
																				size="sm"
																				onClick={() =>
																					handleSetActiveClaudeProfile(
																						profile.id,
																					)
																				}
																				className="gap-1 h-7 text-xs"
																			>
																				<Check className="h-3 w-3" />
																				{t("accounts.claudeCode.setActive")}
																			</Button>
																		)}
																		<Tooltip>
																			<TooltipTrigger asChild>
																				<Button
																					variant="ghost"
																					size="icon"
																					onClick={() =>
																						toggleTokenEntry(profile.id)
																					}
																					className="h-7 w-7 text-muted-foreground hover:text-foreground"
																				>
																					{expandedTokenProfileId ===
																					profile.id ? (
																						<ChevronDown className="h-3 w-3" />
																					) : (
																						<ChevronRight className="h-3 w-3" />
																					)}
																				</Button>
																			</TooltipTrigger>
																			<TooltipContent>
																				{expandedTokenProfileId === profile.id
																					? tCommon(
																							"accessibility.hideTokenEntryAriaLabel",
																						)
																					: tCommon(
																							"accessibility.enterTokenManuallyAriaLabel",
																						)}
																			</TooltipContent>
																		</Tooltip>
																		<Tooltip>
																			<TooltipTrigger asChild>
																				<Button
																					variant="ghost"
																					size="icon"
																					onClick={() =>
																						startEditingProfile(profile)
																					}
																					className="h-7 w-7 text-muted-foreground hover:text-foreground"
																				>
																					<Pencil className="h-3 w-3" />
																				</Button>
																			</TooltipTrigger>
																			<TooltipContent>
																				{tCommon(
																					"accessibility.renameProfileAriaLabel",
																				)}
																			</TooltipContent>
																		</Tooltip>
																		{!profile.isDefault && (
																			<Tooltip>
																				<TooltipTrigger asChild>
																					<Button
																						variant="ghost"
																						size="icon"
																						onClick={() =>
																							handleDeleteClaudeProfile(
																								profile.id,
																							)
																						}
																						disabled={
																							deletingProfileId === profile.id
																						}
																						className="h-7 w-7 text-destructive hover:text-destructive hover:bg-destructive/10"
																					>
																						{deletingProfileId ===
																						profile.id ? (
																							<Loader2 className="h-3 w-3 animate-spin" />
																						) : (
																							<Trash2 className="h-3 w-3" />
																						)}
																					</Button>
																				</TooltipTrigger>
																				<TooltipContent>
																					{tCommon(
																						"accessibility.deleteProfileAriaLabel",
																					)}
																				</TooltipContent>
																			</Tooltip>
																		)}
																	</div>
																)}
															</div>

															{/* Expanded token entry section */}
															{expandedTokenProfileId === profile.id && (
																<div className="px-3 pb-3 pt-0 border-t border-border/50 mt-0">
																	<div className="bg-muted/30 rounded-lg p-3 mt-3 space-y-3">
																		<div className="flex items-center justify-between">
																			<Label className="text-xs font-medium text-muted-foreground">
																				{t(
																					"accounts.claudeCode.manualTokenEntry",
																				)}
																			</Label>
																			<span className="text-xs text-muted-foreground">
																				{t("accounts.claudeCode.runSetupToken")}
																			</span>
																		</div>

																		<div className="space-y-2">
																			<div className="relative">
																				<Input
																					type={
																						showManualToken
																							? "text"
																							: "password"
																					}
																					placeholder={t(
																						"accounts.claudeCode.tokenPlaceholder",
																					)}
																					value={manualToken}
																					onChange={(e) =>
																						setManualToken(e.target.value)
																					}
																					className="pr-10 font-mono text-xs h-8"
																				/>
																				<button
																					type="button"
																					onClick={() =>
																						setShowManualToken(!showManualToken)
																					}
																					className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
																				>
																					{showManualToken ? (
																						<EyeOff className="h-3 w-3" />
																					) : (
																						<Eye className="h-3 w-3" />
																					)}
																				</button>
																			</div>

																			<Input
																				type="email"
																				placeholder={t(
																					"accounts.claudeCode.emailPlaceholder",
																				)}
																				value={manualTokenEmail}
																				onChange={(e) =>
																					setManualTokenEmail(e.target.value)
																				}
																				className="text-xs h-8"
																			/>
																		</div>

																		<div className="flex items-center justify-end gap-2">
																			<Button
																				variant="ghost"
																				size="sm"
																				onClick={() =>
																					toggleTokenEntry(profile.id)
																				}
																				className="h-7 text-xs"
																			>
																				{tCommon("buttons.cancel")}
																			</Button>
																			<Button
																				size="sm"
																				onClick={() =>
																					handleSaveManualToken(profile.id)
																				}
																				disabled={
																					!manualToken.trim() ||
																					savingTokenProfileId === profile.id
																				}
																				className="h-7 text-xs gap-1"
																			>
																				{savingTokenProfileId === profile.id ? (
																					<Loader2 className="h-3 w-3 animate-spin" />
																				) : (
																					<Check className="h-3 w-3" />
																				)}
																				{t("accounts.claudeCode.saveToken")}
																			</Button>
																		</div>
																	</div>
																</div>
															)}
														</div>
													);
												})}
											</div>
										)}

										{/* Embedded Auth Terminal */}
										{authTerminal && (
											<div className="mb-4">
												<div
													className="rounded-lg border border-primary/30 overflow-hidden"
													style={{ height: "320px" }}
												>
													<AuthTerminal
														terminalId={authTerminal.terminalId}
														configDir={authTerminal.configDir}
														profileName={authTerminal.profileName}
														onClose={handleAuthTerminalClose}
														onAuthSuccess={handleAuthTerminalSuccess}
														onAuthError={handleAuthTerminalError}
													/>
												</div>
											</div>
										)}

										{/* Add new account */}
										<div className="flex items-center gap-2">
											<Input
												placeholder={t(
													"accounts.claudeCode.accountNamePlaceholder",
												)}
												value={newProfileName}
												onChange={(e) => setNewProfileName(e.target.value)}
												className="flex-1 h-8 text-sm"
												disabled={!!authTerminal}
												onKeyDown={(e) => {
													if (e.key === "Enter" && newProfileName.trim()) {
														handleAddClaudeProfile();
													}
												}}
											/>
											<Button
												onClick={handleAddClaudeProfile}
												disabled={
													!newProfileName.trim() ||
													isAddingProfile ||
													!!authTerminal
												}
												size="sm"
												className="gap-1 shrink-0"
											>
												{isAddingProfile ? (
													<Loader2 className="h-3 w-3 animate-spin" />
												) : (
													<Plus className="h-3 w-3" />
												)}
												{tCommon("buttons.add")}
											</Button>
										</div>
									</div>
								</TabsContent>

								{/* Custom Endpoints Tab Content */}
								<TabsContent value="custom-endpoints">
									<div className="space-y-4">
										{/* Header with Add button */}
										<div className="flex items-center justify-between">
											<p className="text-sm text-muted-foreground">
												{t("accounts.customEndpoints.description")}
											</p>
											<Button
												onClick={() => setIsAddDialogOpen(true)}
												size="sm"
											>
												<Plus className="h-4 w-4 mr-2" />
												{t("accounts.customEndpoints.addButton")}
											</Button>
										</div>

										{/* Empty state */}
										{apiProfiles.length === 0 && (
											<div className="flex flex-col items-center justify-center py-12 px-4 border border-dashed rounded-lg">
												<Server className="h-12 w-12 text-muted-foreground mb-4" />
												<h4 className="text-lg font-medium mb-2">
													{t("accounts.customEndpoints.empty.title")}
												</h4>
												<p className="text-sm text-muted-foreground text-center max-w-sm mb-4">
													{t("accounts.customEndpoints.empty.description")}
												</p>
												<Button
													onClick={() => setIsAddDialogOpen(true)}
													variant="outline"
												>
													<Plus className="h-4 w-4 mr-2" />
													{t("accounts.customEndpoints.empty.action")}
												</Button>
											</div>
										)}

										{/* Profile list */}
										{apiProfiles.length > 0 && (
											<div className="space-y-2">
												{activeApiProfileId && (
													<div className="flex items-center justify-end pb-2">
														<Button
															variant="outline"
															size="sm"
															onClick={() =>
																handleSetActiveApiProfileClick(null)
															}
															disabled={isSettingActiveApiProfile}
														>
															{isSettingActiveApiProfile
																? t(
																		"accounts.customEndpoints.switchToOauth.loading",
																	)
																: t(
																		"accounts.customEndpoints.switchToOauth.label",
																	)}
														</Button>
													</div>
												)}
												{apiProfiles.map((profile) => {
													const isActive = activeApiProfileId === profile.id;
													return (
														<div
															key={profile.id}
															className={cn(
																"flex items-center justify-between p-4 rounded-lg border transition-colors",
																isActive
																	? "border-primary bg-primary/5"
																	: "border-border hover:bg-accent/50",
															)}
														>
															<div className="flex-1 min-w-0">
																<div className="flex items-center gap-2 mb-1">
																	<h4 className="font-medium truncate">
																		{profile.name}
																	</h4>
																	{isActive && (
																		<span className="flex items-center text-xs text-primary">
																			<Check className="h-3 w-3 mr-1" />
																			{t(
																				"accounts.customEndpoints.activeBadge",
																			)}
																		</span>
																	)}
																</div>
																<div className="flex items-center gap-4 text-sm text-muted-foreground">
																	<Tooltip>
																		<TooltipTrigger asChild>
																			<div className="flex items-center gap-1">
																				<Globe className="h-3 w-3" />
																				<span className="truncate max-w-[200px]">
																					{getHostFromUrl(profile.baseUrl)}
																				</span>
																			</div>
																		</TooltipTrigger>
																		<TooltipContent>
																			<p>{profile.baseUrl}</p>
																		</TooltipContent>
																	</Tooltip>
																	<div className="truncate">
																		{maskApiKey(profile.apiKey)}
																	</div>
																</div>
																{profile.models &&
																	Object.keys(profile.models).length > 0 && (
																		<div className="mt-2 text-xs text-muted-foreground">
																			{t(
																				"accounts.customEndpoints.customModels",
																				{
																					models: Object.keys(
																						profile.models,
																					).join(", "),
																				},
																			)}
																		</div>
																	)}
															</div>

															<div className="flex items-center gap-2">
																{!isActive && (
																	<Button
																		variant="ghost"
																		size="sm"
																		onClick={() =>
																			handleSetActiveApiProfileClick(profile.id)
																		}
																		disabled={isSettingActiveApiProfile}
																	>
																		{isSettingActiveApiProfile
																			? t(
																					"accounts.customEndpoints.setActive.loading",
																				)
																			: t(
																					"accounts.customEndpoints.setActive.label",
																				)}
																	</Button>
																)}
																<Tooltip>
																	<TooltipTrigger asChild>
																		<Button
																			variant="ghost"
																			size="sm"
																			onClick={() => setEditApiProfile(profile)}
																		>
																			<Pencil className="h-4 w-4" />
																		</Button>
																	</TooltipTrigger>
																	<TooltipContent>
																		{t(
																			"accounts.customEndpoints.tooltips.edit",
																		)}
																	</TooltipContent>
																</Tooltip>
																<Tooltip>
																	<TooltipTrigger asChild>
																		<Button
																			variant="ghost"
																			size="sm"
																			onClick={() =>
																				setDeleteConfirmProfile(profile)
																			}
																			disabled={isActive}
																			className="text-destructive hover:text-destructive"
																		>
																			<Trash2 className="h-4 w-4" />
																		</Button>
																	</TooltipTrigger>
																	<TooltipContent>
																		{isActive
																			? t(
																					"accounts.customEndpoints.tooltips.deleteActive",
																				)
																			: t(
																					"accounts.customEndpoints.tooltips.deleteInactive",
																				)}
																	</TooltipContent>
																</Tooltip>
															</div>
														</div>
													);
												})}
											</div>
										)}

										{/* Add/Edit Dialog */}
										<ProfileEditDialog
											open={isAddDialogOpen || editApiProfile !== null}
											onOpenChange={(open) => {
												if (!open) {
													setIsAddDialogOpen(false);
													setEditApiProfile(null);
												}
											}}
											onSaved={() => {
												setIsAddDialogOpen(false);
												setEditApiProfile(null);
											}}
											profile={editApiProfile ?? undefined}
										/>

										{/* Delete Confirmation Dialog */}
										<AlertDialog
											open={deleteConfirmProfile !== null}
											onOpenChange={() => setDeleteConfirmProfile(null)}
										>
											<AlertDialogContent>
												<AlertDialogHeader>
													<AlertDialogTitle>
														{t("accounts.customEndpoints.dialog.deleteTitle")}
													</AlertDialogTitle>
													<AlertDialogDescription>
														{t(
															"accounts.customEndpoints.dialog.deleteDescription",
															{
																name: deleteConfirmProfile?.name ?? "",
															},
														)}
													</AlertDialogDescription>
												</AlertDialogHeader>
												<AlertDialogFooter>
													<AlertDialogCancel disabled={isDeletingApiProfile}>
														{t("accounts.customEndpoints.dialog.cancel")}
													</AlertDialogCancel>
													<AlertDialogAction
														onClick={handleDeleteApiProfile}
														disabled={isDeletingApiProfile}
														className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
													>
														{isDeletingApiProfile
															? t("accounts.customEndpoints.dialog.deleting")
															: t("accounts.customEndpoints.dialog.delete")}
													</AlertDialogAction>
												</AlertDialogFooter>
											</AlertDialogContent>
										</AlertDialog>
									</div>
								</TabsContent>
							</Tabs>
						</div>
					</SettingsSection>
				) : apiKeyField ? (
					<div className="flex flex-col gap-4 max-w-md">
						<Label htmlFor={`apikey-${connector.id}`}>API Key</Label>
						<div className="flex gap-2 items-center">
							<Input
								id={`apikey-${connector.id}`}
								type={apiKeyVisible ? "text" : "password"}
								value={apiKeyValue}
								onChange={handleApiKeyChange}
								placeholder="Collez votre clé API ici"
								autoComplete="off"
							/>
							<Button
								type="button"
								variant="ghost"
								size="icon"
								onClick={() => setApiKeyVisible((v) => !v)}
							>
								{apiKeyVisible ? (
									<EyeOff className="w-4 h-4" />
								) : (
									<Eye className="w-4 h-4" />
								)}
							</Button>
							<Button
								type="button"
								variant="secondary"
								size="sm"
								onClick={handleTestApiKey}
								disabled={!apiKeyValue || authStatus === "loading"}
							>
								{authStatus === "loading" ? (
									<Loader2 className="w-4 h-4 animate-spin" />
								) : (
									"Authentifier"
								)}
							</Button>
							<Button
								type="button"
								variant="destructive"
								size="sm"
								onClick={handleApiKeyClear}
								disabled={!apiKeyValue}
							>
								Révoquer
							</Button>
						</div>
						{authStatus === "success" && (
							<div className="text-green-600 text-xs">{authMessage}</div>
						)}
						{authStatus === "error" && (
							<div className="text-destructive text-xs">{authMessage}</div>
						)}
						<div className="text-xs text-muted-foreground">
							{connector.id === "openai" && (
								<>
									Générez une clé sur{" "}
									<a
										href="https://platform.openai.com/api-keys"
										target="_blank"
										rel="noopener noreferrer"
										className="underline"
									>
										platform.openai.com
									</a>
								</>
							)}
							{connector.id === "gemini" && (
								<>
									Générez une clé sur{" "}
									<a
										href="https://aistudio.google.com/app/apikey"
										target="_blank"
										rel="noopener noreferrer"
										className="underline"
									>
										Google AI Studio
									</a>
								</>
							)}
							{connector.id === "meta-llama" && (
								<>
									Utilisez une clé API fournie par un provider compatible OpenAI
									(ex: Together, Perplexity, etc.)
								</>
							)}
							{connector.id === "mistral" && (
								<>
									Générez une clé sur{" "}
									<a
										href="https://docs.mistral.ai/platform/api/#section/Authentication"
										target="_blank"
										rel="noopener noreferrer"
										className="underline"
									>
										Mistral AI
									</a>
								</>
							)}
							{connector.id === "deepseek" && (
								<>
									Générez une clé sur{" "}
									<a
										href="https://platform.deepseek.com/"
										target="_blank"
										rel="noopener noreferrer"
										className="underline"
									>
										DeepSeek
									</a>
								</>
							)}
							{connector.id === "grok" && (
								<>
									Générez une clé sur{" "}
									<a
										href="https://console.x.ai/"
										target="_blank"
										rel="noopener noreferrer"
										className="underline"
									>
										xAI Console
									</a>
								</>
							)}
							{connector.id === "google" && (
								<>
									Générez une clé sur{" "}
									<a
										href="https://aistudio.google.com/app/apikey"
										target="_blank"
										rel="noopener noreferrer"
										className="underline"
									>
										Google AI Studio
									</a>
								</>
							)}
							{connector.id === "meta" && (
								<>
									Générez une clé sur{" "}
									<a
										href="https://developers.meta.com/"
										target="_blank"
										rel="noopener noreferrer"
										className="underline"
									>
										Meta for Developers
									</a>
								</>
							)}
							{connector.id === "aws" && (
								<>
									Configurez AWS Bedrock (voir{" "}
									<a
										href="https://docs.aws.amazon.com/bedrock/"
										target="_blank"
										rel="noopener noreferrer"
										className="underline"
									>
										AWS Bedrock docs
									</a>
									)
								</>
							)}
							{connector.id === "azure-openai" && (
								<>
									Utilisez une clé API Azure OpenAI (voir{" "}
									<a
										href="https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/create-resource"
										target="_blank"
										rel="noopener noreferrer"
										className="underline"
									>
										docs Azure
									</a>
									)
								</>
							)}
							{connector.id === "copilot" && (
								<>
									Installez GitHub CLI et authentifiez-vous avec{" "}
									<code>gh auth login</code> et <code>gh copilot login</code>
								</>
							)}
						</div>
						<AlertDialog
							open={showRevokeDialog}
							onOpenChange={setShowRevokeDialog}
						>
							<AlertDialogContent>
								<AlertDialogHeader>
									<AlertDialogTitle>Révoquer la clé API ?</AlertDialogTitle>
									<AlertDialogDescription>
										Cette action supprimera la clé API enregistrée pour ce
										connecteur.
										<br />
										Voulez-vous continuer ?
									</AlertDialogDescription>
								</AlertDialogHeader>
								<AlertDialogFooter>
									<AlertDialogCancel>Annuler</AlertDialogCancel>
									<AlertDialogAction
										onClick={confirmRevokeApiKey}
										className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
									>
										Révoquer
									</AlertDialogAction>
								</AlertDialogFooter>
							</AlertDialogContent>
						</AlertDialog>
					</div>
				) : connector.id === "ollama" ||
					connector.id === "copilot" ||
					connector.id === "azure-openai" ? (
					connector.id === "ollama" ? (
						<div className="rounded-lg border border-dashed border-border p-4 text-center mb-4 text-muted-foreground">
							<p>
								<b>LLM local (Ollama, LM Studio, etc.)</b>
								<br />
								Connexion locale via Ollama (aucune authentification requise).
								<br />
								Assurez-vous qu'Ollama tourne sur{" "}
								<code>http://localhost:11434</code>.
							</p>
						</div>
					) : connector.id === "copilot" ? (
						<CopilotOAuthAuth
							onAuthSuccess={(username, _profileName) => {
								toast({
									title: "GitHub Copilot Connected",
									description: `Successfully authenticated as ${username}`,
								});
							}}
							onAuthError={(error) => {
								toast({
									title: "Authentication Failed",
									description: error,
									variant: "destructive",
								});
							}}
						/>
					) : connector.id === "azure-openai" ? (
						<div className="rounded-lg border border-dashed border-border p-4 text-center mb-4 text-muted-foreground">
							<p>
								Connexion via <b>Azure OpenAI</b> (authentification Azure
								requise).
								<br />
								Utilisez une clé API Azure OpenAI (voir{" "}
								<a
									href="https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/create-resource"
									target="_blank"
									rel="noopener noreferrer"
									className="underline"
								>
									docs Azure
								</a>
								).
							</p>
						</div>
					) : null
				) : null}
			</div>
		</TooltipProvider>
	);
}
