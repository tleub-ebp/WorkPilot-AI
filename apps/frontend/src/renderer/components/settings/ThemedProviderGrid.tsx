import React, { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, Filter, Grid3x3, List, Plus, RefreshCw } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { ThemedProviderCard } from './ThemedProviderCard';
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

interface ThemedProviderGridProps {
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

export function ThemedProviderGrid({
  providers,
  onConfigure,
  onTest,
  onToggle,
  onRemove,
  onAddProvider,
  onRefreshProviders,
  isLoading = false,
  className
}: ThemedProviderGridProps) {
  const { t } = useTranslation('settings');
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');
  const [sortBy, setSortBy] = useState<SortBy>('name');

  // Filtres et recherche
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

    // Tri
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

  // Statistiques
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
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">Providers LLM</h2>
            <p className="text-sm text-gray-600">Gérez vos services d'intelligence artificielle</p>
          </div>
          
          <div className="flex gap-2">
            {onRefreshProviders && (
              <Button
                variant="outline"
                onClick={onRefreshProviders}
                disabled={isLoading}
                size="sm"
              >
                <RefreshCw className={cn('w-4 h-4 mr-2', isLoading && 'animate-spin')} />
                Actualiser
              </Button>
            )}
            {onAddProvider && (
              <Button
                onClick={onAddProvider}
                size="sm"
              >
                <Plus className="w-4 h-4 mr-2" />
                Ajouter
              </Button>
            )}
          </div>
        </div>
        
        {/* Statistiques */}
        <div className="flex gap-4 text-sm">
          <div className="px-3 py-1 bg-gray-100 rounded">
            <span className="font-medium">{stats.total}</span> total
          </div>
          <div className="px-3 py-1 bg-green-100 text-green-700 rounded">
            <span className="font-medium">{stats.configured}</span> configurés
          </div>
          {stats.errors > 0 && (
            <div className="px-3 py-1 bg-red-100 text-red-700 rounded">
              <span className="font-medium">{stats.errors}</span> erreurs
            </div>
          )}
        </div>
      </div>

      {/* Barre de recherche et filtres */}
      <div className="border rounded-lg p-4 space-y-4 bg-gray-50">
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <Input
                placeholder="Rechercher un provider..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
          
          <div className="flex gap-2">
            <Select value={filterStatus} onValueChange={(value: FilterStatus) => setFilterStatus(value)}>
              <SelectTrigger className="w-40">
                <Filter className="w-4 h-4 mr-2 text-gray-500" />
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous</SelectItem>
                <SelectItem value="configured">Configurés</SelectItem>
                <SelectItem value="unconfigured">Non configurés</SelectItem>
                <SelectItem value="errors">Avec erreurs</SelectItem>
              </SelectContent>
            </Select>

            <Select value={sortBy} onValueChange={(value: SortBy) => setSortBy(value)}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="name">Nom</SelectItem>
                <SelectItem value="category">Catégorie</SelectItem>
                <SelectItem value="status">Statut</SelectItem>
                <SelectItem value="usage">Utilisation</SelectItem>
              </SelectContent>
            </Select>

            <div className="flex bg-gray-200 rounded p-1">
              <Button
                variant={viewMode === 'grid' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('grid')}
                className="h-7 px-2"
              >
                <Grid3x3 className="w-3 h-3" />
              </Button>
              <Button
                variant={viewMode === 'list' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('list')}
                className="h-7 px-2"
              >
                <List className="w-3 h-3" />
              </Button>
            </div>
          </div>
        </div>

        {/* Résultats de recherche */}
        {searchQuery && (
          <div className="text-sm text-gray-600">
            {filteredAndSortedProviders.length} résultat{filteredAndSortedProviders.length > 1 ? 's' : ''} pour "{searchQuery}"
          </div>
        )}
      </div>

      {/* Grille de providers */}
      <div className="space-y-4">
        {filteredAndSortedProviders.length === 0 ? (
          <div className="text-center py-12 border-2 border-dashed border-gray-300 rounded-lg">
            <div className="space-y-3">
              <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto">
                <Search className="w-6 h-6 text-gray-400" />
              </div>
              <div>
                <h3 className="font-medium text-gray-900">
                  {searchQuery || filterStatus !== 'all' 
                    ? 'Aucun provider trouvé'
                    : 'Aucun provider disponible'
                  }
                </h3>
                <p className="text-sm text-gray-600 mt-1">
                  {searchQuery || filterStatus !== 'all' 
                    ? 'Essayez d\'ajuster vos critères de recherche.'
                    : 'Commencez par ajouter votre premier provider.'
                  }
                </p>
              </div>
              {onAddProvider && !searchQuery && filterStatus === 'all' && (
                <Button
                  onClick={onAddProvider}
                  size="sm"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Ajouter votre premier provider
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
            {filteredAndSortedProviders.map((provider) => (
              <ThemedProviderCard
                key={provider.id}
                provider={provider}
                onConfigure={onConfigure}
                onTest={onTest}
                onToggle={onToggle}
                onRemove={onRemove}
                className={viewMode === 'list' ? 'max-w-2xl' : ''}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
