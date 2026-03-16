import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import {
  Check,
  AlertTriangle,
  X,
  Loader2,
  Download,
  RefreshCw,
  ExternalLink,
  FolderOpen,
  LogIn,
} from "lucide-react";
import { Button } from "./ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "./ui/popover";
import { Tooltip, TooltipContent, TooltipTrigger } from "./ui/tooltip";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "./ui/alert-dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { cn } from "@/lib/utils";
import type { CopilotCliVersionInfo, CopilotInstallationInfo } from "@shared/types";
import { useProjectStore } from "@/stores/project-store";

interface CopilotCliStatusBadgeProps {
  readonly className?: string;
  readonly onNavigateToTerminals?: () => void;
}

interface CopilotIconProps {
  readonly className?: string;
}

type StatusType = "loading" | "installed" | "outdated" | "not-found" | "gh-missing" | "error";

const CHECK_INTERVAL_MS = 24 * 60 * 60 * 1000;
const VERSION_RECHECK_DELAY_MS = 5000;

/**
 * GitHub Copilot icon (simplified SVG)
 */
function CopilotIcon({ className }: CopilotIconProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" />
      <path d="M8 14s1.5 2 4 2 4-2 4-2" />
      <circle cx="9" cy="10" r="1.25" fill="currentColor" stroke="none" />
      <circle cx="15" cy="10" r="1.25" fill="currentColor" stroke="none" />
    </svg>
  );
}

/**
 * Copilot CLI status badge for the sidebar.
 * Shows installation status and provides quick access to install/update/auth.
 * Mirrors ClaudeCodeStatusBadge pattern but adapted for gh copilot extension.
 */
export function CopilotCliStatusBadge({ className, onNavigateToTerminals }: CopilotCliStatusBadgeProps) {
  const { t } = useTranslation(["common", "navigation"]);
  const projects = useProjectStore((state) => state.projects);
  const selectedProjectId = useProjectStore((state) => state.selectedProjectId);
  const currentProject = projects.find((p) => p.id === selectedProjectId);
  const projectPath = currentProject?.path || ".";
  const [status, setStatus] = useState<StatusType>("loading");
  const [versionInfo, setVersionInfo] = useState<CopilotCliVersionInfo | null>(null);
  const [isInstalling, setIsInstalling] = useState(false);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [showInstallWarning, setShowInstallWarning] = useState(false);
  const [installError, setInstallError] = useState<string | null>(null);

  // Auth state
  const [authStatus, setAuthStatus] = useState<{ authenticated: boolean; username?: string } | null>(null);

  // CLI path selection state
  const [installations, setInstallations] = useState<CopilotInstallationInfo[]>([]);
  const [isLoadingInstallations, setIsLoadingInstallations] = useState(false);
  const [installationsError, setInstallationsError] = useState<string | null>(null);
  const [selectedInstallation, setSelectedInstallation] = useState<string | null>(null);
  const [showPathChangeWarning, setShowPathChangeWarning] = useState(false);

  // Check Copilot CLI version
  const checkVersion = useCallback(async () => {
    try {
      if (!globalThis.electronAPI?.checkCopilotCliVersion) {
        setStatus("error");
        return;
      }

      const result = await globalThis.electronAPI.checkCopilotCliVersion();

      if (result.success && result.data) {
        setVersionInfo(result.data);
        setLastChecked(new Date());

        // Determine status based on gh availability and copilot extension
        if (!result.data.ghVersion && !result.data.installed) {
          setStatus("gh-missing");
        } else if (!result.data.installed) {
          setStatus("not-found");
        } else if (result.data.isOutdated) {
          setStatus("outdated");
        } else {
          setStatus("installed");
        }
      } else {
        setStatus("error");
      }
    } catch (err) {
      console.error("Failed to check Copilot CLI version:", err);
      setStatus("error");
    }
  }, []);

  // Check auth status
  const checkAuth = useCallback(async () => {
    try {
      if (!globalThis.electronAPI?.checkCopilotAuth) return;
      const result = await globalThis.electronAPI.checkCopilotAuth();
      if (result.success && result.data) {
        setAuthStatus(result.data);
      }
    } catch (err) {
      console.error("Failed to check Copilot auth:", err);
    }
  }, []);

  // Fetch CLI installations
  const fetchInstallations = useCallback(async () => {
    if (!globalThis.electronAPI?.getCopilotCliInstallations) return;

    setIsLoadingInstallations(true);
    setInstallationsError(null);

    try {
      const result = await globalThis.electronAPI.getCopilotCliInstallations();
      if (result.success && result.data) {
        setInstallations(result.data.installations);
      } else {
        setInstallationsError(result.error || "Failed to load installations");
      }
    } catch (err) {
      console.error("Failed to fetch installations:", err);
      setInstallationsError("Failed to load installations");
    } finally {
      setIsLoadingInstallations(false);
    }
  }, []);

  // Initial check and periodic re-check
  useEffect(() => {
    checkVersion();
    checkAuth();

    const interval = setInterval(() => {
      checkVersion();
    }, CHECK_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [checkVersion, checkAuth]);

  // Fetch installations when popover opens
  useEffect(() => {
    if (isOpen && installations.length === 0) {
      fetchInstallations();
    }
  }, [isOpen, installations.length, fetchInstallations]);

  // Helper function for delay
  const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

  // Helper function to send terminal commands with delays
  const sendTerminalCommandsWithDelay = async (terminalId: string, commands: Array<{cmd: string; delay: number}>) => {
    if (!globalThis.electronAPI?.sendTerminalInput) return;
    
    for (const {cmd, delay: ms} of commands) {
      await delay(ms);
      globalThis.electronAPI.sendTerminalInput(terminalId, cmd);
    }
  };

  // Helper function to execute terminal installation
  const executeTerminalInstallation = async (terminalId: string, isUpdate: boolean) => {
    const commands = [
      { cmd: "clear\n", delay: 0 },
      { cmd: "echo 'Installing Copilot CLI extension...'\n", delay: 50 },
      { 
        cmd: isUpdate ? "gh extension upgrade gh-copilot\n" : "gh extension install github/gh-copilot\n", 
        delay: 50 
      }
    ];
    
    await sendTerminalCommandsWithDelay(terminalId, commands);
  };

  // Helper function to execute terminal auth
  const executeTerminalAuth = async (terminalId: string) => {
    const commands = [
      { cmd: "gh auth login\n", delay: 0 }
    ];
    
    await sendTerminalCommandsWithDelay(terminalId, commands);
  };

  // Perform install/update
  const performInstall = async () => {
    setIsInstalling(true);
    setShowInstallWarning(false);
    setInstallError(null);
    try {
      if (!globalThis.electronAPI?.installCopilotCli) {
        setInstallError("Installation not available");
        setIsInstalling(false);
        return;
      }

      // Create a terminal in the app
      if (globalThis.electronAPI?.createTerminal) {
        const terminalId = `copilot-cli-install-${Date.now()}`;
        const terminalResult = await globalThis.electronAPI.createTerminal({
          id: terminalId,
          cwd: projectPath,
          cols: 80,
          rows: 25,
          projectPath: projectPath,
        });

        if (terminalResult.success) {
          await delay(100);
          
          const isUpdate = status === "outdated";
          await executeTerminalInstallation(terminalId, isUpdate);
          
          await delay(200);
          setIsOpen(false);
          if (onNavigateToTerminals) {
            onNavigateToTerminals();
          }
        }
      }

      // Don't call the external installCopilotCli - we're using the internal terminal
      await delay(VERSION_RECHECK_DELAY_MS);
      checkVersion();
    } catch (err) {
      console.error("Failed to install Copilot CLI:", err);
      setInstallError(err instanceof Error ? err.message : "Installation failed");
    } finally {
      setIsInstalling(false);
    }
  };

  // Start gh auth login
  const startAuth = async () => {
    try {
      if (!globalThis.electronAPI?.startCopilotAuth) return;

      if (globalThis.electronAPI?.createTerminal) {
        const terminalId = `copilot-auth-${Date.now()}`;
        const terminalResult = await globalThis.electronAPI.createTerminal({
          id: terminalId,
          cwd: projectPath,
          cols: 80,
          rows: 25,
          projectPath: projectPath,
        });

        if (terminalResult.success) {
          await delay(100);
          await executeTerminalAuth(terminalId);
          
          await delay(200);
          setIsOpen(false);
          if (onNavigateToTerminals) {
            onNavigateToTerminals();
          }
        }
      }

      await globalThis.electronAPI.startCopilotAuth();
    } catch (err) {
      console.error("Failed to start Copilot auth:", err);
    }
  };

  // Perform CLI path switch
  const performPathSwitch = async () => {
    if (!selectedInstallation) return;

    setIsInstalling(true);
    setShowPathChangeWarning(false);
    setInstallError(null);

    try {
      if (!globalThis.electronAPI?.setCopilotCliActivePath) {
        setInstallError("Path switching not available");
        return;
      }

      const result = await globalThis.electronAPI.setCopilotCliActivePath(selectedInstallation);

      if (result.success) {
        setTimeout(() => {
          checkVersion();
          fetchInstallations();
        }, VERSION_RECHECK_DELAY_MS);
      } else {
        setInstallError(result.error || "Failed to switch CLI path");
      }
    } catch (err) {
      console.error("Failed to switch Copilot CLI path:", err);
      setInstallError(err instanceof Error ? err.message : "Failed to switch CLI path");
    } finally {
      setIsInstalling(false);
      setSelectedInstallation(null);
    }
  };

  // Handle install button click
  const handleInstall = () => {
    if (status === "outdated") {
      setShowInstallWarning(true);
    } else {
      performInstall();
    }
  };

  // Handle installation selection
  const handleInstallationSelect = (cliPath: string) => {
    const installation = installations.find(i => i.path === cliPath);
    if (installation?.isActive) return;
    setInstallError(null);
    setSelectedInstallation(cliPath);
    setShowPathChangeWarning(true);
  };

  // Get status indicator color
  const getStatusColor = () => {
    switch (status) {
      case "installed":
        return "bg-green-500";
      case "outdated":
        return "bg-yellow-500";
      case "not-found":
      case "gh-missing":
      case "error":
        return "bg-destructive";
      default:
        return "bg-muted-foreground";
    }
  };

  // Get status icon
  const getStatusIcon = () => {
    switch (status) {
      case "loading":
        return <Loader2 className="h-3 w-3 animate-spin" />;
      case "installed":
        return <Check className="h-3 w-3" />;
      case "outdated":
        return <AlertTriangle className="h-3 w-3" />;
      case "not-found":
      case "gh-missing":
        return <X className="h-3 w-3" />;
      case "error":
        return <AlertTriangle className="h-3 w-3" />;
    }
  };

  // Get tooltip text
  const getTooltipText = () => {
    switch (status) {
      case "loading":
        return "Checking Copilot CLI...";
      case "installed":
        return "Copilot CLI is up to date";
      case "outdated":
        return "Copilot CLI update available";
      case "not-found":
        return "Copilot CLI extension not installed";
      case "gh-missing":
        return "GitHub CLI (gh) not found — required for Copilot";
      case "error":
        return "Error checking Copilot CLI";
    }
  };

  // Get select placeholder text
  const getSelectPlaceholder = () => {
    if (isLoadingInstallations) {
      return "Loading installations...";
    }
    if (installationsError) {
      return "Failed to load installations";
    }
    return "Select installation";
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
                status === "not-found" || status === "gh-missing" || status === "error" ? "text-destructive" : "",
                status === "outdated" ? "text-yellow-600 dark:text-yellow-500" : "",
                className
              )}
            >
              <div className="relative">
                <CopilotIcon className="h-4 w-4" />
                <span
                  className={cn(
                    "absolute -bottom-0.5 -right-0.5 h-2 w-2 rounded-full",
                    getStatusColor()
                  )}
                />
              </div>
              <span className="truncate">Copilot</span>
              {status === "outdated" && (
                <span className="ml-auto text-[10px] bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 px-1.5 py-0.5 rounded">
                  {t("common:update", "Update")}
                </span>
              )}
              {(status === "not-found" || status === "gh-missing") && (
                <span className="ml-auto text-[10px] bg-destructive/20 text-destructive px-1.5 py-0.5 rounded">
                  {status === "gh-missing" ? "gh missing" : t("common:install", "Install")}
                </span>
              )}
            </Button>
          </PopoverTrigger>
        </TooltipTrigger>
        <TooltipContent side="right">{getTooltipText()}</TooltipContent>
      </Tooltip>

      <PopoverContent side="right" align="end" className="w-72">
        <div className="space-y-3">
          {/* Header */}
          <div className="flex items-center gap-2 justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
                <CopilotIcon className="h-4 w-4 text-primary" />
              </div>
              <div>
                <h4 className="text-sm font-medium">Copilot CLI</h4>
                <p className="text-xs text-muted-foreground flex items-center gap-1">
                  {getStatusIcon()}
                  {status === "installed" && "Installed"}
                  {status === "outdated" && "Update available"}
                  {status === "not-found" && "Extension not installed"}
                  {status === "gh-missing" && "GitHub CLI not found"}
                  {status === "loading" && "Checking..."}
                  {status === "error" && "Error"}
                </p>
              </div>
            </div>
          </div>

          {/* gh-missing notice */}
          {status === "gh-missing" && (
            <div className="text-xs p-2 bg-destructive/10 text-destructive rounded-md">
              <p className="font-medium">Requires GitHub CLI (gh)</p>
              <p className="mt-1 text-muted-foreground">
                Install from{" "}
                <button
                  className="underline text-primary"
                  onClick={() => globalThis.electronAPI?.openExternal?.("https://cli.github.com")}
                >
                  cli.github.com
                </button>
              </p>
            </div>
          )}

          {/* Version info */}
          {versionInfo && status !== "loading" && status !== "gh-missing" && (
            <div className="text-xs space-y-1 p-2 bg-muted rounded-md">
              {versionInfo.installed && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Copilot:</span>
                  <span className="font-mono">{versionInfo.installed}</span>
                </div>
              )}
              {versionInfo.ghVersion && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">gh CLI:</span>
                  <span className="font-mono">{versionInfo.ghVersion}</span>
                </div>
              )}
              {versionInfo.path && (
                <div className="flex justify-between items-center gap-2">
                  <span className="text-muted-foreground flex items-center gap-1">
                    <FolderOpen className="h-3 w-3" />
                    Path:
                  </span>
                  <span
                    className="font-mono text-[10px] truncate max-w-[140px]"
                    title={versionInfo.path}
                  >
                    {versionInfo.path}
                  </span>
                </div>
              )}
              {authStatus && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Auth:</span>
                  <span className={authStatus.authenticated ? "text-green-600" : "text-destructive"}>
                    {authStatus.authenticated
                      ? authStatus.username || "Authenticated"
                      : "Not authenticated"}
                  </span>
                </div>
              )}
              {lastChecked && (
                <div className="flex justify-between text-muted-foreground">
                  <span>Last checked:</span>
                  <span>{lastChecked.toLocaleTimeString()}</span>
                </div>
              )}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-2">
            {(status === "not-found" || status === "outdated") && (
              <Button
                size="sm"
                className="flex-1 gap-1"
                onClick={handleInstall}
                disabled={isInstalling}
              >
                {isInstalling ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <Download className="h-3 w-3" />
                )}
                {status === "outdated"
                  ? t("common:update", "Update")
                  : t("common:install", "Install")}
              </Button>
            )}
            {authStatus && !authStatus.authenticated && status !== "gh-missing" && (
              <Button
                size="sm"
                variant="outline"
                className="gap-1"
                onClick={startAuth}
              >
                <LogIn className="h-3 w-3" />
                Login
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              className="gap-1"
              onClick={() => {
                checkVersion();
                checkAuth();
              }}
              disabled={status === "loading"}
            >
              <RefreshCw className={cn("h-3 w-3", status === "loading" && "animate-spin")} />
              {t("common:refresh", "Refresh")}
            </Button>
          </div>

          {/* Install error display */}
          {installError && (
            <div className="text-xs p-2 bg-destructive/10 text-destructive rounded-md flex items-center gap-2">
              <AlertTriangle className="h-3 w-3 shrink-0" />
              <span>{installError}</span>
            </div>
          )}

          {/* CLI Installation selector - show when multiple installations are found */}
          {installations.length > 1 && (
            <div className="space-y-1.5">
              <div className="text-xs text-muted-foreground">
                {t("copilot:switchInstallation", "Switch Installation")}
              </div>
              <Select
                value={selectedInstallation || ""}
                onValueChange={handleInstallationSelect}
                disabled={isLoadingInstallations || isInstalling}
              >
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue
                    placeholder={getSelectPlaceholder()}
                  />
                </SelectTrigger>
                <SelectContent>
                  {installations.map((installation) => (
                    <SelectItem
                      key={installation.path}
                      value={installation.path}
                      className="text-xs"
                      disabled={installation.isActive}
                    >
                      <div className="flex flex-col">
                        <span className="font-mono text-[10px] truncate max-w-[180px]" title={installation.path}>
                          {installation.path.split(/[/\\]/).slice(-2).join('/') || installation.path}
                        </span>
                        <span className="text-muted-foreground text-[9px]">
                          {installation.version ? `copilot v${installation.version}` : t("copilot:versionUnknown", "version unknown")}
                          {installation.ghVersion ? ` (gh ${installation.ghVersion})` : ""}
                          {" "}({installation.source})
                          {installation.isActive && ` - ${t("copilot:active", "Active")}`}
                        </span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Docs link */}
          <Button
            variant="link"
            size="sm"
            className="w-full text-xs text-muted-foreground gap-1"
            onClick={() =>
              globalThis.electronAPI?.openExternal?.(
                "https://docs.github.com/en/copilot/github-copilot-in-the-cli"
              )
            }
          >
            {t("copilot:viewCopilotCliDocs", "View Copilot CLI Docs")}
            <ExternalLink className="h-3 w-3" />
          </Button>
        </div>
      </PopoverContent>

      {/* Update warning dialog */}
      <AlertDialog open={showInstallWarning} onOpenChange={setShowInstallWarning}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("copilot:updateCopilotCli", "Update Copilot CLI?")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("copilot:updateDescription", "This will upgrade the gh-copilot extension. A new terminal will open in the \"Terminaux Agent\" page to run the upgrade command.")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("common:cancel", "Cancel")}</AlertDialogCancel>
            <AlertDialogAction onClick={performInstall}>
              {t("copilot:openTerminalAndUpdate", "Open Terminal & Update")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Path change warning dialog */}
      <AlertDialog open={showPathChangeWarning} onOpenChange={setShowPathChangeWarning}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("copilot:switchGhCliInstallation", "Switch gh CLI installation?")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("copilot:switchDescription", "Switching installations will use a different gh binary for Copilot CLI.")}
              {" "}
              <span className="block mt-2 font-mono text-xs break-all">
                {selectedInstallation}
              </span>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setSelectedInstallation(null)}>
              {t("common:cancel", "Cancel")}
            </AlertDialogCancel>
            <AlertDialogAction onClick={performPathSwitch}>
              {t("copilot:switch", "Switch")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Popover>
  );
}
