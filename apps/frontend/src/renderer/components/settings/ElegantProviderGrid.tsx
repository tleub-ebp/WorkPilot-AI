import React, { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, Filter, Grid3x3, List, Plus, RefreshCw, Sparkles } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { ElegantProviderCard } from './ElegantProviderCard';
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
  icon?: React.ElementType;
}

interface ElegantProviderGridProps {
  providers: Provider[];
  onConfigure: (providerId: string) => void;
  onTest: (providerId: string) => void;
  onToggle: (providerId: string, enabled: boolean) => void;
  onRemove?: (providerId: string) => void;
  onAddProvider?: () => void;
  onRefreshProviders?: () => void;
  isLoading?: boolean;
  className?: string;
}

type ViewMode = 'grid' | 'list';
type FilterStatus = 'all' | 'configured' | 'unconfigured' | 'errors';
type SortBy = 'name' | 'category' | 'status' | 'usage';

export function ElegantProviderGrid({
  providers,
  onConfigure,
  onTest,
  onToggle,
  onRemove,
  onAddProvider,
  onRefreshProviders,
  isLoading = false,
  className
}: ElegantProviderGridProps) {
  const { t } = useTranslation('settings');
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');
  const [sortBy, setSortBy] = useState<SortBy>('name');

  // Filtres et recherche avec animation
  const filteredAndSortedProviders = useMemo(() => {
    let filtered = providers.filter(provider => {
      const matchesSearch = provider.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                           provider.description?.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchesFilter = filterStatus === 'all' ||
                           (filterStatus === 'configured' && provider.isConfigured) ||
                           (filterStatus === 'unconfigured' && !provider.isConfigured) ||
                           (filterStatus === 'errors' && provider.isWorking === false);

      return matchesSearch && matchesFilter;
    });

    // Tri avec animation implicite
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

  // Statistiques avec design élégant
  const stats = useMemo(() => {
    const total = providers.length;
    const configured = providers.filter(p => p.isConfigured).length;
    const working = providers.filter(p => p.isWorking !== false).length;
    const errors = providers.filter(p => p.isWorking === false).length;
    
    return { total, configured, working, errors };
  }, [providers]);

  const categories = useMemo(() => {
    const cats = new Set(providers.map(p => p.category));
    return Array.from(cats).sort();
  }, [providers]);

  return (
    <div className={cn('space-y-8', className)}>
      {/* Header élégant avec statistiques */}
      <div className="flex flex-col lg:flex-row gap-6 items-start lg:items-center justify-between">
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-linear-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-900 tracking-tight">Providers LLM</h2>
              <p className="text-sm text-gray-600 mt-0.5">Gérez vos services d'intelligence artificielle</p>
            </div>
          </div>
          
          <div className="flex flex-wrap gap-3">
            <div className="px-3 py-1.5 bg-gray-100/50 rounded-lg">
              <span className="text-sm font-medium text-gray-700">{stats.total} total</span>
            </div>
            <div className="px-3 py-1.5 bg-emerald-50/50 rounded-lg border border-emerald-200/50">
              <span className="text-sm font-medium text-emerald-700">{stats.configured} configurés</span>
            </div>
            {stats.errors > 0 && (
              <div className="px-3 py-1.5 bg-red-50/50 rounded-lg border border-red-200/50">
                <span className="text-sm font-medium text-red-700">{stats.errors} erreurs</span>
              </div>
            )}
          </div>
        </div>
        
        <div className="flex gap-3">
          {onRefreshProviders && (
            <Button
              variant="outline"
              onClick={onRefreshProviders}
              disabled={isLoading}
              className={cn(
                'px-4 py-2 rounded-xl transition-all duration-200',
                'hover:bg-gray-50 hover:shadow-md hover:scale-105',
                'active:scale-95',
                isLoading && 'opacity-50'
              )}
            >
              <RefreshCw className={cn('w-4 h-4 mr-2', isLoading && 'animate-spin')} />
              Actualiser
            </Button>
          )}
          {onAddProvider && (
            <Button
              onClick={onAddProvider}
              className={cn(
                'px-4 py-2 rounded-xl transition-all duration-200',
                'bg-linear-to-br from-blue-500 to-purple-600 text-white',
                'hover:from-blue-600 hover:to-purple-700 hover:shadow-lg hover:scale-105',
                'active:scale-95'
              )}
            >
              <Plus className="w-4 h-4 mr-2" />
              Ajouter un provider
            </Button>
          )}
        </div>
      </div>

      {/* Barre de recherche et filtres élégants */}
      <div className="bg-white/60 backdrop-blur-sm rounded-2xl border border-gray-200/50 p-6 space-y-4">
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <Input
                placeholder="Rechercher un provider..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className={cn(
                  'pl-12 pr-4 py-3 rounded-xl border-gray-200/50',
                  'bg-white/80 backdrop-blur-sm',
                  'focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500',
                  'transition-all duration-200'
                )}
              />
            </div>
          </div>
          
          <div className="flex gap-3">
            <Select value={filterStatus} onValueChange={(value: FilterStatus) => setFilterStatus(value)}>
              <SelectTrigger className={cn(
                'w-40 rounded-xl border-gray-200/50',
                'bg-white/80 backdrop-blur-sm',
                'hover:bg-gray-50/80 transition-colors duration-200'
              )}>
                <Filter className="w-4 h-4 mr-2 text-gray-500" />
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="rounded-xl border-gray-200/50">
                <SelectItem value="all" className="rounded-lg">Tous</SelectItem>
                <SelectItem value="configured" className="rounded-lg">Configurés</SelectItem>
                <SelectItem value="unconfigured" className="rounded-lg">Non configurés</SelectItem>
                <SelectItem value="errors" className="rounded-lg">Avec erreurs</SelectItem>
              </SelectContent>
            </Select>

            <Select value={sortBy} onValueChange={(value: SortBy) => setSortBy(value)}>
              <SelectTrigger className={cn(
                'w-32 rounded-xl border-gray-200/50',
                'bg-white/80 backdrop-blur-sm',
                'hover:bg-gray-50/80 transition-colors duration-200'
              )}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="rounded-xl border-gray-200/50">
                <SelectItem value="name" className="rounded-lg">Nom</SelectItem>
                <SelectItem value="category" className="rounded-lg">Catégorie</SelectItem>
                <SelectItem value="status" className="rounded-lg">Statut</SelectItem>
                <SelectItem value="usage" className="rounded-lg">Utilisation</SelectItem>
              </SelectContent>
            </Select>

            <div className="flex bg-gray-100/50 rounded-xl p-1">
              <Button
                variant={viewMode === 'grid' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('grid')}
                className={cn(
                  'rounded-lg transition-all duration-200',
                  viewMode === 'grid' 
                    ? 'bg-white shadow-sm text-gray-900' 
                    : 'text-gray-600 hover:text-gray-900'
                )}
              >
                <Grid3x3 className="w-4 h-4" />
              </Button>
              <Button
                variant={viewMode === 'list' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('list')}
                className={cn(
                  'rounded-lg transition-all duration-200',
                  viewMode === 'list' 
                    ? 'bg-white shadow-sm text-gray-900' 
                    : 'text-gray-600 hover:text-gray-900'
                )}
              >
                <List className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>

        {/* Résultats de recherche */}
        {searchQuery && (
          <div className="text-sm text-gray-600 animate-in slide-in-from-top-1 duration-200">
            {filteredAndSortedProviders.length} résultat{filteredAndSortedProviders.length > 1 ? 's' : ''} pour "{searchQuery}"
          </div>
        )}
      </div>

      {/* Grille de providers élégante */}
      <div className="space-y-6">
        {filteredAndSortedProviders.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-16 h-16 bg-gray-100/50 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Search className="w-8 h-8 text-gray-400" />
            </div>
            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-gray-900">
                {searchQuery || filterStatus !== 'all' 
                  ? 'Aucun provider trouvé'
                  : 'Aucun provider disponible'
                }
              </h3>
              <p className="text-sm text-gray-600 max-w-md mx-auto">
                {searchQuery || filterStatus !== 'all' 
                  ? 'Essayez d\'ajuster vos critères de recherche.'
                  : 'Commencez par ajouter votre premier provider.'
                }
              </p>
            </div>
            {onAddProvider && !searchQuery && filterStatus === 'all' && (
              <Button
                onClick={onAddProvider}
                className={cn(
                  'mt-6 px-6 py-3 rounded-xl',
                  'bg-linear-to-br from-blue-500 to-purple-600 text-white',
                  'hover:from-blue-600 hover:to-purple-700 hover:shadow-lg hover:scale-105',
                  'transition-all duration-200'
                )}
              >
                <Plus className="w-4 h-4 mr-2" />
                Ajouter votre premier provider
              </Button>
            )}
          </div>
        ) : (
          <div className={cn(
            'grid gap-6 transition-all duration-300',
            viewMode === 'grid' 
              ? 'grid-cols-1 md:grid-cols-2 xl:grid-cols-3' 
              : 'grid-cols-1 max-w-4xl mx-auto'
          )}>
            {filteredAndSortedProviders.map((provider, index) => (
              <div
                key={provider.id}
                className="animate-in slide-in-from-bottom-4 fade-in-0 duration-500"
                style={{ animationDelay: `${index * 100}ms` }}
              >
                <ElegantProviderCard
                  provider={provider}
                  onConfigure={onConfigure}
                  onTest={onTest}
                  onToggle={onToggle}
                  onRemove={onRemove}
                  className={viewMode === 'list' ? 'max-w-4xl' : ''}
                />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
