/**
 * Azure DevOps Work Item Import Modal
 * Main modal component for importing work items from Azure DevOps
 */

import { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Download, Loader2, Search, Filter, CheckSquare, Square, RefreshCw } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { Checkbox } from '../ui/checkbox';
import { Label } from '../ui/label';
import { ScrollArea } from '../ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import type {
  AzureDevOpsWorkItem,
  AzureDevOpsImportResult,
  AzureDevOpsSyncStatus,
} from '../../../shared/types';
import type { AzureDevOpsImportModalProps, AzureDevOpsFilters } from './types';

export function AzureDevOpsImportModal({
  projectId,
  open,
  onOpenChange,
  onImportComplete,
}: AzureDevOpsImportModalProps) {
  const { t } = useTranslation('settings');
  const [workItems, setWorkItems] = useState<AzureDevOpsWorkItem[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState<AzureDevOpsFilters>({
    workItemType: 'all',
    state: 'all',
    assignedTo: 'all',
  });

  const [isLoadingItems, setIsLoadingItems] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<AzureDevOpsImportResult | null>(null);
  const [syncStatus, setSyncStatus] = useState<AzureDevOpsSyncStatus | null>(null);

  // Load connection status
  useEffect(() => {
    if (open) {
      loadConnectionStatus();
    }
  }, [open, projectId]);

  // Load work items when modal opens
  useEffect(() => {
    if (open && syncStatus?.connected) {
      loadWorkItems();
    }
  }, [open, syncStatus?.connected]);

  const loadConnectionStatus = async () => {
    try {
      const result = await window.electronAPI.checkAzureDevOpsConnection(projectId);
      if (result.success) {
        setSyncStatus(result.data);
        if (!result.data.connected) {
          setError(result.data.error || t('settings:azureDevOpsImport.errorNotConfigured'));
        }
      } else {
        setError(result.error || t('settings:azureDevOpsImport.errorCheckConnectionFailed'));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('settings:azureDevOpsImport.errorUnknown'));
    }
  };

  const loadWorkItems = async () => {
    setIsLoadingItems(true);
    setError(null);
    try {
      const result = await window.electronAPI.getAzureDevOpsWorkItems(
        projectId,
        undefined, // Use default project from config
        undefined, // Use default item types (Bug, Task, User Story)
        1000 // Max items
      );

      if (result.success) {
        setWorkItems(result.data || []);
      } else {
        setError(result.error || t('settings:azureDevOpsImport.errorLoadWorkItemsFailed'));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('settings:azureDevOpsImport.errorUnknown'));
    } finally {
      setIsLoadingItems(false);
    }
  };

  const handleRefresh = () => {
    setSelectedIds(new Set());
    setSearchQuery('');
    setFilters({
      workItemType: 'all',
      state: 'all',
      assignedTo: 'all',
    });
    loadWorkItems();
  };

  const handleImport = async () => {
    if (selectedIds.size === 0) return;

    setIsImporting(true);
    setError(null);

    try {
      const result = await window.electronAPI.importAzureDevOpsWorkItems(
        projectId,
        Array.from(selectedIds)
      );

      if (result.success) {
        setImportResult(result.data);
        if (result.data.success && onImportComplete) {
          setTimeout(() => {
            onImportComplete();
          }, 1500);
        }
      } else {
        setError(result.error || t('settings:azureDevOpsImport.errorImportFailed'));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('settings:azureDevOpsImport.errorUnknown'));
    } finally {
      setIsImporting(false);
    }
  };

  // Filter work items
  const filteredItems = useMemo(() => {
    return workItems.filter((item) => {
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const matchesSearch =
          item.title.toLowerCase().includes(query) ||
          item.id.toString().includes(query) ||
          (item.description && item.description.toLowerCase().includes(query));
        if (!matchesSearch) return false;
      }

      // Work item type filter
      if (filters.workItemType !== 'all' && item.workItemType !== filters.workItemType) {
        return false;
      }

      // State filter
      if (filters.state !== 'all' && item.state !== filters.state) {
        return false;
      }

      return true;
    });
  }, [workItems, searchQuery, filters]);

  // Get unique values for filters
  const uniqueTypes = useMemo(() => {
    return Array.from(new Set(workItems.map((item) => item.workItemType))).sort();
  }, [workItems]);

  const uniqueStates = useMemo(() => {
    return Array.from(new Set(workItems.map((item) => item.state))).sort();
  }, [workItems]);

  // Selection handlers
  const toggleItem = (id: number) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedIds(newSelected);
  };

  const selectAll = () => {
    setSelectedIds(new Set(filteredItems.map((item) => item.id)));
  };

  const deselectAll = () => {
    setSelectedIds(new Set());
  };

  const isAllSelected = filteredItems.length > 0 && selectedIds.size === filteredItems.length;
  const isSomeSelected = selectedIds.size > 0 && selectedIds.size < filteredItems.length;

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      // Reset state when closing
      setSelectedIds(new Set());
      setSearchQuery('');
      setFilters({
        workItemType: 'all',
        state: 'all',
        assignedTo: 'all',
      });
      setError(null);
      setImportResult(null);
    }
    onOpenChange(newOpen);
  };

  const successMessage = importResult?.success
    ? t('settings:azureDevOpsImport.successCount', { count: importResult.imported })
    : '';
  const failedSuffix = importResult?.success && importResult.failed > 0
    ? ` ${t('settings:azureDevOpsImport.successFailedSuffix', { count: importResult.failed })}`
    : '';

  // Get color for work item type badge
  const getTypeColor = (type: string): string => {
    switch (type.toLowerCase()) {
      case 'bug':
        return 'bg-red-500/10 text-red-500 border-red-500/20';
      case 'task':
        return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
      case 'user story':
        return 'bg-green-500/10 text-green-500 border-green-500/20';
      case 'feature':
        return 'bg-purple-500/10 text-purple-500 border-purple-500/20';
      case 'epic':
        return 'bg-orange-500/10 text-orange-500 border-orange-500/20';
      default:
        return 'bg-gray-500/10 text-gray-500 border-gray-500/20';
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[800px] max-h-[85vh] flex flex-col">
        <DialogHeader className="shrink-0">
          <DialogTitle className="flex items-center gap-2 text-foreground">
            <Download className="h-5 w-5" />
            {t('settings:azureDevOpsImport.title')}
          </DialogTitle>
          <DialogDescription>
            {t('settings:azureDevOpsImport.description')}
          </DialogDescription>
        </DialogHeader>

        {/* Import Success Banner */}
        {importResult?.success && (
          <div className="bg-green-500/10 border border-green-500/20 rounded-md p-4">
            <h4 className="font-semibold text-green-500 mb-2">
              {t('settings:azureDevOpsImport.successTitle')}
            </h4>
            <p className="text-sm text-foreground/70">
              {`${successMessage}${failedSuffix}`}
            </p>
          </div>
        )}

        {/* Error Banner */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-md p-4">
            <p className="text-sm text-red-500">{error}</p>
          </div>
        )}

        {/* Main Content */}
        {!importResult?.success && syncStatus?.connected && (
          <>
            {/* Connection Info */}
            {syncStatus.projectName && (
              <div className="text-sm text-foreground/70 bg-muted/50 p-3 rounded-md">
                <strong>{t('settings:azureDevOpsImport.projectLabel')}</strong>{' '}
                {syncStatus.projectName}
              </div>
            )}

            {/* Search Bar */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder={t('settings:azureDevOpsImport.searchPlaceholder')}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>

            {/* Filters */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs text-foreground/70 mb-1 block">
                  {t('settings:azureDevOpsImport.filterTypeLabel')}
                </Label>
                <Select
                  value={filters.workItemType}
                  onValueChange={(value) =>
                    setFilters((prev) => ({ ...prev, workItemType: value }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">
                      {t('settings:azureDevOpsImport.filterTypeAll')}
                    </SelectItem>
                    {uniqueTypes.map((type) => (
                      <SelectItem key={type} value={type}>
                        {type}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label className="text-xs text-foreground/70 mb-1 block">
                  {t('settings:azureDevOpsImport.filterStateLabel')}
                </Label>
                <Select
                  value={filters.state}
                  onValueChange={(value) =>
                    setFilters((prev) => ({ ...prev, state: value }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">
                      {t('settings:azureDevOpsImport.filterStateAll')}
                    </SelectItem>
                    {uniqueStates.map((state) => (
                      <SelectItem key={state} value={state}>
                        {state}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Selection Controls */}
            {filteredItems.length > 0 && (
              <div className="flex items-center justify-between py-2 border-t border-b">
                <div className="flex items-center gap-2">
                  <Checkbox
                    checked={isAllSelected}
                    onCheckedChange={() => {
                      if (isAllSelected) {
                        deselectAll();
                      } else {
                        selectAll();
                      }
                    }}
                    className={isSomeSelected ? 'data-[state=checked]:bg-primary/50' : ''}
                  />
                  <span className="text-sm text-foreground/70">
                    {t('settings:azureDevOpsImport.selectionCount', {
                      selected: selectedIds.size,
                      total: filteredItems.length,
                    })}
                  </span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleRefresh}
                  disabled={isLoadingItems}
                >
                  <RefreshCw className={`h-4 w-4 ${isLoadingItems ? 'animate-spin' : ''}`} />
                </Button>
              </div>
            )}

            {/* Work Items List */}
            <ScrollArea className="flex-1 -mx-6 px-6">
              {isLoadingItems ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : filteredItems.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  <p>{t('settings:azureDevOpsImport.emptyTitle')}</p>
                  {(searchQuery || filters.workItemType !== 'all' || filters.state !== 'all') && (
                    <p className="text-sm mt-2">{t('settings:azureDevOpsImport.emptySubtitle')}</p>
                  )}
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredItems.map((item) => (
                    <div
                      key={item.id}
                      className="flex items-start gap-3 p-3 rounded-md border hover:bg-muted/50 cursor-pointer transition-colors"
                      onClick={() => toggleItem(item.id)}
                    >
                      <Checkbox
                        checked={selectedIds.has(item.id)}
                        onCheckedChange={() => toggleItem(item.id)}
                        onClick={(e) => e.stopPropagation()}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-mono text-xs text-muted-foreground">
                            #{item.id}
                          </span>
                          <Badge variant="outline" className={getTypeColor(item.workItemType)}>
                            {item.workItemType}
                          </Badge>
                          <Badge variant="outline">{item.state}</Badge>
                          {item.priority !== undefined && (
                            <Badge variant="outline">P{item.priority}</Badge>
                          )}
                        </div>
                        <h4 className="font-medium text-sm mb-1">{item.title}</h4>
                        {item.description && (
                          <p className="text-xs text-muted-foreground line-clamp-2">
                            {item.description}
                          </p>
                        )}
                        {item.tags.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {item.tags.slice(0, 3).map((tag, idx) => (
                              <Badge key={idx} variant="secondary" className="text-xs">
                                {tag}
                              </Badge>
                            ))}
                            {item.tags.length > 3 && (
                              <Badge variant="secondary" className="text-xs">
                                +{item.tags.length - 3}
                              </Badge>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>
          </>
        )}

        <DialogFooter className="shrink-0">
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            {importResult?.success
              ? t('settings:azureDevOpsImport.done')
              : t('settings:azureDevOpsImport.cancel')}
          </Button>
          {!importResult?.success && syncStatus?.connected && (
            <Button
              onClick={handleImport}
              disabled={selectedIds.size === 0 || isImporting}
            >
              {isImporting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('settings:azureDevOpsImport.importing')}
                </>
              ) : (
                <>
                  <Download className="mr-2 h-4 w-4" />
                  {t('settings:azureDevOpsImport.importButton', {
                    count: selectedIds.size,
                  })}
                </>
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
