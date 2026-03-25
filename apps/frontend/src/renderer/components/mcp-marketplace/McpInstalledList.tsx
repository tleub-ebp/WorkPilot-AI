/**
 * MCP Installed Servers List
 *
 * Displays and manages all installed MCP servers.
 * Allows enabling/disabling, configuring, and uninstalling servers.
 */

import { useTranslation } from 'react-i18next';
import {
  Power,
  Trash2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Terminal,
  Globe,
  Wrench,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Switch } from '../ui/switch';
import {
  useMcpMarketplaceStore,
  toggleMarketplaceServer,
  uninstallMarketplaceServer,
} from '../../stores/mcp-marketplace-store';

export function McpInstalledList() {
  const { t } = useTranslation(['common']);
  const { installed, isInstalledLoading, catalog } = useMcpMarketplaceStore();

  const getCatalogInfo = (serverId: string) => {
    return catalog.find((s) => s.id === serverId);
  };

  if (isInstalledLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (installed.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground px-6">
        <Power className="h-16 w-16 mb-4 opacity-20" />
        <h2 className="text-lg font-medium mb-1">{t('mcpMarketplace.installedTab.empty')}</h2>
        <p className="text-sm text-center max-w-md">
          {t('mcpMarketplace.installedTab.emptyHint')}
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-auto p-6">
      <div className="space-y-3 max-w-4xl mx-auto">
        {installed.map((server) => {
          const catalogInfo = getCatalogInfo(server.serverId);
          const color = catalogInfo?.color || '#6B7280';
          
          // biome-ignore lint/suspicious/noImplicitAnyLet: type inferred from assignment
          let statusIcon;
          if (server.status === 'installed' && server.enabled) {
            statusIcon = <CheckCircle2 className="h-4 w-4 text-green-500" />;
          } else if (server.status === 'error') {
            statusIcon = <XCircle className="h-4 w-4 text-destructive" />;
          } else {
            statusIcon = <AlertCircle className="h-4 w-4 text-muted-foreground" />;
          }

          return (
            <div
              key={server.serverId}
              className="flex items-center gap-4 p-4 rounded-xl border border-border bg-card hover:border-border/80 transition-colors"
            >
              {/* Color indicator + icon */}
              <div
                className="shrink-0 flex items-center justify-center w-10 h-10 rounded-lg text-white text-sm font-bold"
                style={{ backgroundColor: color }}
              >
                {server.name.charAt(0)}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium text-sm">{server.name}</h3>
                  {statusIcon}
                  {server.isCustomBuilt && (
                    <Badge variant="outline" className="text-[10px] gap-1">
                      <Wrench className="h-3 w-3" />
                      {t('mcpMarketplace.installedTab.custom')}
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1">
                  <span className="flex items-center gap-1">
                    {server.transport === 'stdio' ? (
                      <Terminal className="h-3 w-3" />
                    ) : (
                      <Globe className="h-3 w-3" />
                    )}
                    {server.transport}
                  </span>
                  <span>v{server.version}</span>
                  <span>
                    {t('mcpMarketplace.installedTab.since', {
                      date: new Date(server.installedAt).toLocaleDateString(),
                    })}
                  </span>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 shrink-0">
                <Switch
                  checked={server.enabled}
                  onCheckedChange={(checked) =>
                    toggleMarketplaceServer(server.serverId, checked)
                  }
                  aria-label={
                    server.enabled
                      ? t('mcpMarketplace.installedTab.disable')
                      : t('mcpMarketplace.installedTab.enable')
                  }
                />
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-destructive hover:text-destructive"
                  onClick={() => uninstallMarketplaceServer(server.serverId)}
                  title={t('mcpMarketplace.uninstall')}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
