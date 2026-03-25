/**
 * MCP Marketplace — Main View Component
 *
 * The universal integration ecosystem. Provides:
 * - Catalog: Browse and install MCP servers
 * - Installed: Manage installed servers
 * - Builder: Create custom MCP servers (no-code)
 */

import { useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Store,
  Download,
  Wrench,
  Search,
  Filter,
  BadgeCheck,
  ArrowUpDown,
  RefreshCw,
} from 'lucide-react';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import {
  useMcpMarketplaceStore,
  loadMarketplaceCatalog,
  loadInstalledServers,
  loadBuilderProjects,
} from '../../stores/mcp-marketplace-store';
import type { McpMarketplaceTab, McpCategory } from '../../../shared/types/mcp-marketplace';
import { McpServerCard } from './McpServerCard';
import { McpInstalledList } from './McpInstalledList';
import { McpBuilder } from './McpBuilder';

const TABS: { id: McpMarketplaceTab; labelKey: string; icon: typeof Store }[] = [
  { id: 'catalog', labelKey: 'mcpMarketplace.tabs.catalog', icon: Store },
  { id: 'installed', labelKey: 'mcpMarketplace.tabs.installed', icon: Download },
  { id: 'builder', labelKey: 'mcpMarketplace.tabs.builder', icon: Wrench },
];

const CATEGORIES: { value: McpCategory | 'all'; labelKey: string }[] = [
  { value: 'all', labelKey: 'mcpMarketplace.categories.all' },
  { value: 'communication', labelKey: 'mcpMarketplace.categories.communication' },
  { value: 'project-management', labelKey: 'mcpMarketplace.categories.projectManagement' },
  { value: 'design', labelKey: 'mcpMarketplace.categories.design' },
  { value: 'monitoring', labelKey: 'mcpMarketplace.categories.monitoring' },
  { value: 'version-control', labelKey: 'mcpMarketplace.categories.versionControl' },
  { value: 'documentation', labelKey: 'mcpMarketplace.categories.documentation' },
  { value: 'database', labelKey: 'mcpMarketplace.categories.database' },
  { value: 'cloud', labelKey: 'mcpMarketplace.categories.cloud' },
  { value: 'security', labelKey: 'mcpMarketplace.categories.security' },
  { value: 'analytics', labelKey: 'mcpMarketplace.categories.analytics' },
  { value: 'ai', labelKey: 'mcpMarketplace.categories.ai' },
];

export function McpMarketplace() {
  const { t } = useTranslation(['common']);
  const {
    activeTab,
    setActiveTab,
    filters,
    setFilters,
    getFilteredCatalog,
    installed,
    isCatalogLoading,
  } = useMcpMarketplaceStore();

  const filteredCatalog = getFilteredCatalog();

  // Load data on mount
  useEffect(() => {
    loadMarketplaceCatalog();
    loadInstalledServers();
    loadBuilderProjects();
  }, []);

  const handleRefresh = useCallback(() => {
    loadMarketplaceCatalog();
    loadInstalledServers();
    loadBuilderProjects();
  }, []);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="shrink-0 border-b border-border bg-background px-6 pt-5 pb-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2.5">
              <Store className="h-7 w-7 text-primary" />
              {t('mcpMarketplace.title')}
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              {t('mcpMarketplace.subtitle')}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="text-xs">
              {installed.length} {t('mcpMarketplace.installedCount')}
            </Badge>
            <Button variant="ghost" size="icon" onClick={handleRefresh} title={t('mcpMarketplace.refresh')}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-muted/50 rounded-lg p-1 w-fit">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button type="button"
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-all ${
                  isActive
                    ? 'bg-background text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground hover:bg-background/50'
                }`}
              >
                <Icon className="h-4 w-4" />
                {t(tab.labelKey)}
              </button>
            );
          })}
        </div>
      </div>

      {/* Catalog tab content */}
      {activeTab === 'catalog' && (
        <>
          {/* Filters bar */}
          <div className="shrink-0 flex items-center gap-3 px-6 py-3 border-b border-border bg-background/50">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                value={filters.search}
                onChange={(e) => setFilters({ search: e.target.value })}
                placeholder={t('mcpMarketplace.searchPlaceholder')}
                className="pl-9 h-9"
              />
            </div>

            <Select
              value={filters.category}
              onValueChange={(val) => setFilters({ category: val as McpCategory | 'all' })}
            >
              <SelectTrigger className="w-[180px] h-9">
                <Filter className="h-3.5 w-3.5 mr-1.5 text-muted-foreground" />
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CATEGORIES.map((cat) => (
                  <SelectItem key={cat.value} value={cat.value}>
                    {t(cat.labelKey)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={filters.sortBy}
              onValueChange={(val) => setFilters({ sortBy: val as 'popular' | 'rating' | 'newest' | 'name' })}
            >
              <SelectTrigger className="w-[160px] h-9">
                <ArrowUpDown className="h-3.5 w-3.5 mr-1.5 text-muted-foreground" />
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="popular">{t('mcpMarketplace.sort.popular')}</SelectItem>
                <SelectItem value="rating">{t('mcpMarketplace.sort.rating')}</SelectItem>
                <SelectItem value="newest">{t('mcpMarketplace.sort.newest')}</SelectItem>
                <SelectItem value="name">{t('mcpMarketplace.sort.name')}</SelectItem>
              </SelectContent>
            </Select>

            <Button
              variant={filters.showVerifiedOnly ? 'default' : 'outline'}
              size="sm"
              className="h-9 gap-1.5"
              onClick={() => setFilters({ showVerifiedOnly: !filters.showVerifiedOnly })}
            >
              <BadgeCheck className="h-3.5 w-3.5" />
              {t('mcpMarketplace.verifiedOnly')}
            </Button>
          </div>

          {/* Catalog grid */}
          <div className="flex-1 overflow-auto p-6">
            {(() => {
              if (isCatalogLoading) {
                return (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {Array.from({ length: 6 }).map(() => (
                      <div
                        key={`skeleton-${crypto.randomUUID()}`}
                        className="h-[220px] rounded-xl border border-border bg-muted/30 animate-pulse"
                      />
                    ))}
                  </div>
                );
              } else if (filteredCatalog.length === 0) {
                return (
                  <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
                    <Search className="h-12 w-12 mb-3 opacity-30" />
                    <p className="text-lg font-medium">{t('mcpMarketplace.noResults')}</p>
                    <p className="text-sm mt-1">{t('mcpMarketplace.noResultsHint')}</p>
                  </div>
                );
              } else {
                return (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filteredCatalog.map((server) => (
                      <McpServerCard key={server.id} server={server} />
                    ))}
                  </div>
                );
              }
            })()}
          </div>
        </>
      )}

      {/* Installed tab content */}
      {activeTab === 'installed' && <McpInstalledList />}

      {/* Builder tab content */}
      {activeTab === 'builder' && <McpBuilder />}
    </div>
  );
}
