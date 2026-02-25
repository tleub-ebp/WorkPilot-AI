import React, { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, Filter, Grid3x3, List, Plus, RefreshCw } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { CleanProviderCard } from './CleanProviderCard';
import { cn } from '@/lib/utils';

interface Provider {
  id: string;
  name: string;
  category: string;
  description?: string;
  isConfigured: boolean;
  isWorking?: boolean;
  lastTested?: string;
  usageCount?: number;
  isPremium?: boolean;
  icon?: React.ReactNode;
}

interface CleanProviderGridProps {
  providers: Provider[];
  onConfigure: (providerId: string) => void;
  onTest: (providerId: string) => void;
  onToggle: (providerId: string, enabled: boolean) => void;
  onRemove?: (providerId: string) => void;
  onAddProvider?: () => void;
  onRefreshProviders?: () => void;
  isLoading?: boolean;
  isAutoSwitchingOpen?: boolean;
  testingProviders?: Set<string>;
  className?: string;
}

type ViewMode = 'grid' | 'list';
type FilterStatus = 'all' | 'configured' | 'unconfigured' | 'errors';
type SortBy = 'name' | 'category' | 'status' | 'usage';

export function CleanProviderGrid({
  providers,
  onConfigure,
  onTest,
  onToggle,
  onRemove,
  onAddProvider,
  onRefreshProviders,
  isLoading = false,
  isAutoSwitchingOpen,
  testingProviders = new Set(),
  className
}: CleanProviderGridProps) {
  const { t } = useTranslation('settings');
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');
  const [sortBy, setSortBy] = useState<SortBy>('name');

  // Filtres et recherche simples
  const filteredProviders = useMemo(() => {
    let filtered = providers.filter(provider => {
      const matchesSearch = provider.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                           provider.description?.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchesFilter = filterStatus === 'all' ||
                           (filterStatus === 'configured' && provider.isConfigured) ||
                           (filterStatus === 'unconfigured' && !provider.isConfigured) ||
                           (filterStatus === 'errors' && provider.isWorking === false);

      return matchesSearch && matchesFilter;
    });

    // Ajouter la logique de tri manquante
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.name.localeCompare(b.name);
        case 'category':
          return a.category.localeCompare(b.category);
        case 'status':
          const statusA = a.isConfigured ? (a.isWorking === false ? -1 : 1) : 0;
          const statusB = b.isConfigured ? (b.isWorking === false ? -1 : 1) : 0;
          return statusB - statusA;
        case 'usage':
          return (b.usageCount || 0) - (a.usageCount || 0);
        default:
          return 0;
      }
    });

    return filtered;
  }, [providers, searchQuery, filterStatus, sortBy]);

  // Statistiques simples
  const stats = useMemo(() => {
    const total = providers.length;
    const configured = providers.filter(p => p.isConfigured).length;
    const errors = providers.filter(p => p.isWorking === false).length;
    
    return { total, configured, errors };
  }, [providers]);

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header avec actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-foreground">{t('providerGrid.title')}</h2>
          <p className="text-sm text-muted-foreground">
            {t('providerGrid.description')}
          </p>
        </div>
        
        <div className="flex gap-2">
          {onRefreshProviders && (
            <Button
              variant="outline"
              size="sm"
              onClick={onRefreshProviders}
              disabled={isLoading}
            >
              <RefreshCw className={cn("w-4 h-4 mr-2", isLoading && "animate-spin")} />
              {t('providerGrid.actions.refresh')}
            </Button>
          )}
          {onAddProvider && (
            <Button
              onClick={onAddProvider}
              size="sm"
            >
              <Plus className="w-4 h-4 mr-2" />
              {t('providerGrid.actions.add')}
            </Button>
          )}
        </div>
      </div>

      {/* Statistiques */}
      <div className="flex items-center gap-4 text-sm">
        <div className="px-2 py-1 bg-primary/10 text-primary rounded">
          <span className="font-medium">{stats.total}</span> {t('providerGrid.stats.total')}
        </div>
        <div className="px-2 py-1 bg-green-500/10 text-green-600 rounded">
          <span className="font-medium">{stats.configured}</span> {t('providerGrid.stats.configured')}
        </div>
        {stats.errors > 0 && (
          <div className="px-2 py-1 bg-red-500/10 text-red-600 rounded">
            <span className="font-medium">{stats.errors}</span> {t('providerGrid.stats.errors')}
          </div>
        )}
      </div>

      {/* Barre de recherche minimaliste */}
      <div className="border rounded-lg p-3 bg-muted/30">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
              <Input
                placeholder={t('providerGrid.search.placeholder')}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 bg-background border-border"
              />
            </div>
          </div>
          
          <div className="flex gap-2">
            <Select value={filterStatus} onValueChange={(value: FilterStatus) => setFilterStatus(value)}>
              <SelectTrigger className="w-32 bg-background border-border">
                <Filter className="w-4 h-4 mr-2 text-muted-foreground" />
                <SelectValue placeholder={t('providerGrid.filters.placeholder')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('providerGrid.filters.all')}</SelectItem>
                <SelectItem value="configured">{t('providerGrid.filters.configured')}</SelectItem>
                <SelectItem value="unconfigured">{t('providerGrid.filters.unconfigured')}</SelectItem>
                <SelectItem value="errors">{t('providerGrid.filters.errors')}</SelectItem>
              </SelectContent>
            </Select>

            <Select value={sortBy} onValueChange={(value: SortBy) => setSortBy(value)}>
              <SelectTrigger className="w-32 bg-background border-border">
                <SelectValue placeholder={t('providerGrid.sort.placeholder')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="name">{t('providerGrid.sort.name')}</SelectItem>
                <SelectItem value="category">{t('providerGrid.sort.category')}</SelectItem>
                <SelectItem value="status">{t('providerGrid.sort.status')}</SelectItem>
                <SelectItem value="usage">{t('providerGrid.sort.usage')}</SelectItem>
              </SelectContent>
            </Select>

            <div className="flex bg-background rounded p-1 border border-border">
              <Button
                variant={viewMode === 'grid' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('grid')}
                className="h-6 w-6 p-0"
              >
                <Grid3x3 className="w-3 h-3" />
              </Button>
              <Button
                variant={viewMode === 'list' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('list')}
                className="h-6 w-6 p-0"
              >
                <List className="w-3 h-3" />
              </Button>
            </div>
          </div>
        </div>

        {/* Résultats de recherche */}
        {searchQuery && (
          <div className="text-xs text-muted-foreground">
            {t('providerGrid.search.results', { count: filteredProviders.length, query: searchQuery })}
          </div>
        )}
      </div>

      {/* Grille de providers */}
      <div className="space-y-4">
        {filteredProviders.length === 0 ? (
          <div className="text-center py-12 border-2 border-dashed border-border rounded-lg">
            <div className="space-y-3">
              <div className="w-10 h-10 bg-muted rounded-full flex items-center justify-center mx-auto">
                <Search className="w-5 h-5 text-muted-foreground" />
              </div>
              <div>
                <h3 className="font-medium text-foreground">
                  {searchQuery || filterStatus !== 'all' 
                    ? t('providerGrid.search.noResults')
                    : t('providerGrid.search.noProviders')
                  }
                </h3>
                <p className="text-sm text-muted-foreground mt-1">
                  {searchQuery || filterStatus !== 'all' 
                    ? t('providerGrid.search.adjustCriteria')
                    : t('providerGrid.search.addFirst')
                  }
                </p>
              </div>
              {onAddProvider && !searchQuery && filterStatus === 'all' && (
                <Button
                  onClick={onAddProvider}
                  size="sm"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  {t('providerGrid.search.addFirstButton')}
                </Button>
              )}
            </div>
          </div>
        ) : (
          <div className={cn(
            'grid gap-4',
            viewMode === 'grid' 
              ? 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3' 
              : 'grid-cols-1 max-w-2xl mx-auto'
          )}>
            {filteredProviders.map((provider) => (
              <CleanProviderCard
                key={provider.id}
                provider={provider}
                onConfigure={onConfigure}
                onTest={onTest}
                onToggle={onToggle}
                onRemove={onRemove}
                className={viewMode === 'list' ? 'max-w-2xl' : ''}
                isAutoSwitchingOpen={isAutoSwitchingOpen}
                isTesting={testingProviders.has(provider.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
