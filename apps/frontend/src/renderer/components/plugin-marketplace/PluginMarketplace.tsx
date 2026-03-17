import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Puzzle, Package, BookOpen } from 'lucide-react';
import {
  usePluginMarketplaceStore,
  loadPluginCatalog,
  loadInstalledPlugins,
} from '@/stores/plugin-marketplace-store';
import { PluginCatalogView } from './PluginCatalogView';
import { InstalledPluginsView } from './InstalledPluginsView';
import { PluginSDKView } from './PluginSDKView';
import { cn } from '@/lib/utils';
import type { PluginMarketplaceTab } from '@shared/types/plugin-marketplace';

const TABS: Array<{ id: PluginMarketplaceTab; labelKey: string; icon: React.ElementType }> = [
  { id: 'catalog', labelKey: 'common:pluginMarketplace.tabs.catalog', icon: Puzzle },
  { id: 'installed', labelKey: 'common:pluginMarketplace.tabs.installed', icon: Package },
  { id: 'sdk', labelKey: 'common:pluginMarketplace.tabs.sdk', icon: BookOpen },
];

export function PluginMarketplace() {
  const { t } = useTranslation(['common']);
  const { activeTab, setActiveTab, installed, error } = usePluginMarketplaceStore();

  useEffect(() => {
    loadPluginCatalog();
    loadInstalledPlugins();
  }, []);

  return (
    <div className="flex flex-col h-full overflow-hidden bg-background">
      {/* Header */}
      <div className="shrink-0 border-b border-border bg-background px-6 pt-5 pb-0">
        <div className="flex items-center gap-3 mb-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
            <Puzzle className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-xl font-bold">{t('common:pluginMarketplace.title')}</h1>
            <p className="text-xs text-muted-foreground">
              {t('common:pluginMarketplace.subtitle')}
            </p>
          </div>
          {installed.length > 0 && (
            <span className="ml-auto rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">
              {t('common:pluginMarketplace.installedBadge', { count: installed.length })}
            </span>
          )}
        </div>

        {/* Tabs */}
        <div className="flex gap-0">
          {TABS.map(({ id, labelKey, icon: Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => setActiveTab(id)}
              className={cn(
                'flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors',
                activeTab === id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
              )}
            >
              <Icon className="h-4 w-4" />
              {t(labelKey)}
              {id === 'installed' && installed.length > 0 && (
                <span className="ml-1 rounded-full bg-primary/10 px-1.5 text-[10px] font-medium text-primary">
                  {installed.length}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="shrink-0 bg-destructive/10 border-b border-destructive/20 px-6 py-2 text-xs text-destructive">
          {error}
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'catalog' && <PluginCatalogView />}
        {activeTab === 'installed' && <InstalledPluginsView />}
        {activeTab === 'sdk' && <PluginSDKView />}
      </div>
    </div>
  );
}
