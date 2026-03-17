import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import {
  Check,
  AlertTriangle,
  X,
  Loader2,
  RefreshCw,
  ExternalLink,
} from "lucide-react";
import { Button } from "./ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "./ui/popover";
import { Tooltip, TooltipContent, TooltipTrigger } from "./ui/tooltip";
import { cn } from "@/lib/utils";

interface CodexCliStatusBadgeProps {
  readonly className?: string;
  readonly onNavigateToTerminals?: () => void;
}

interface CodexIconProps {
  readonly className?: string;
}

type StatusType = "loading" | "authenticated" | "not-configured" | "error";

const CHECK_INTERVAL_MS = 60 * 1000; // Re-check every 60s

/**
 * OpenAI Codex icon (simplified)
 */
function CodexIcon({ className }: CodexIconProps) {
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
      <path d="M12 2L2 7l10 5 10-5-10-5z" />
      <path d="M2 17l10 5 10-5" />
      <path d="M2 12l10 5 10-5" />
    </svg>
  );
}

/**
 * Codex CLI status badge for the sidebar.
 * Shows authentication status by checking ~/.codex/auth.json via IPC.
 */
export function CodexCliStatusBadge({ className, onNavigateToTerminals }: CodexCliStatusBadgeProps) {
  const { t } = useTranslation(["common", "navigation"]);
  const [status, setStatus] = useState<StatusType>("loading");
  const [profileName, setProfileName] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const checkAuth = useCallback(async () => {
    try {
      if (!globalThis.electronAPI?.checkOpenAICodexOAuth) {
        setStatus("error");
        return;
      }

      const result = await globalThis.electronAPI.checkOpenAICodexOAuth();

      if (result?.isAuthenticated) {
        setStatus("authenticated");
        setProfileName(result.profileName || null);
      } else {
        setStatus("not-configured");
        setProfileName(null);
      }
      setLastChecked(new Date());
    } catch (err) {
      console.error("Failed to check Codex CLI auth:", err);
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    checkAuth();
    const interval = setInterval(checkAuth, CHECK_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [checkAuth]);

  const getStatusColor = () => {
    switch (status) {
      case "authenticated":
        return "bg-green-500";
      case "not-configured":
        return "bg-muted-foreground";
      case "error":
        return "bg-destructive";
      default:
        return "bg-muted-foreground";
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case "loading":
        return <Loader2 className="h-3 w-3 animate-spin" />;
      case "authenticated":
        return <Check className="h-3 w-3" />;
      case "not-configured":
        return <X className="h-3 w-3" />;
      case "error":
        return <AlertTriangle className="h-3 w-3" />;
    }
  };

  const getTooltipText = () => {
    switch (status) {
      case "loading":
        return "Vérification Codex CLI...";
      case "authenticated":
        return profileName ? `Codex CLI (${profileName})` : "Codex CLI connecté";
      case "not-configured":
        return "Codex CLI non configuré";
      case "error":
        return "Erreur Codex CLI";
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
                status === "not-configured" || status === "error" ? "text-muted-foreground" : "",
                className
              )}
            >
              <div className="relative">
                <CodexIcon className="h-4 w-4" />
                <span
                  className={cn(
                    "absolute -bottom-0.5 -right-0.5 h-2 w-2 rounded-full",
                    getStatusColor()
                  )}
                />
              </div>
              <span className="truncate">Codex</span>
              {status === "not-configured" && (
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
                {status === "authenticated" && "Connecté"}
                {status === "not-configured" && "Non configuré"}
                {status === "loading" && "Vérification..."}
                {status === "error" && "Erreur"}
              </p>
            </div>
          </div>

          {/* Auth info */}
          {status === "authenticated" && profileName && (
            <div className="text-xs space-y-1 p-2 bg-muted rounded-md">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Compte :</span>
                <span className="font-medium truncate ml-2">{profileName}</span>
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
          {status === "not-configured" && (
            <div className="text-xs p-2 bg-muted/50 rounded-md text-muted-foreground">
              <p>Lancez <code className="font-mono bg-muted px-1 rounded">codex</code> dans un terminal pour vous authentifier via OAuth.</p>
              <p className="mt-1">Configurez dans Paramètres → OpenAI → OAuth / Codex.</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              className="flex-1 gap-1"
              onClick={() => {
                checkAuth();
              }}
              disabled={status === "loading"}
            >
              <RefreshCw className={cn("h-3 w-3", status === "loading" && "animate-spin")} />
              {t("common:refresh", "Rafraîchir")}
            </Button>
          </div>

          {/* Docs link */}
          <Button
            variant="link"
            size="sm"
            className="w-full text-xs text-muted-foreground gap-1"
            onClick={() =>
              globalThis.electronAPI?.openExternal?.(
                "https://github.com/openai/codex"
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
