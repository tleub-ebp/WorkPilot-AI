/**
 * Jira Side Panel Component
 * Provides a sliding panel for importing Jira issues with drag & drop
 * Mirrors the Azure DevOps Side Panel functionality
 */

import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Download, Search, RefreshCw, X, ChevronRight, GripVertical, ChevronLeft, Settings } from 'lucide-react';
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
import { cn } from '@/lib/utils';
import type { JiraWorkItem, JiraSyncStatus } from '../../../shared/types/integrations';
import type { TaskStatus } from '../../../shared/types';

interface JiraSidePanelProps {
  projectId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onWorkItemsImported?: (workItems: JiraWorkItem[], targetStatus: TaskStatus) => void;
  onOpenSettings?: () => void;
}

interface JiraFilters {
  workItemType: string;
  state: string;
}

export function JiraSidePanel({
  projectId,
  open,
  onOpenChange,
  onWorkItemsImported,
  onOpenSettings
}: JiraSidePanelProps) {
  const { t } = useTranslation('settings');
  const [workItems, setWorkItems] = useState<JiraWorkItem[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState<JiraFilters>({
    workItemType: 'all',
    state: 'all',
  });

  const [isLoadingItems, setIsLoadingItems] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syncStatus, setSyncStatus] = useState<JiraSyncStatus | null>(null);
  const [draggedIds, setDraggedIds] = useState<Set<string>>(new Set());
  const [panelWidth, setPanelWidth] = useState(384);
  const [isResizing, setIsResizing] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [lastCacheTime, setLastCacheTime] = useState<number>(0);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const resizeStartX = useRef(0);
  const resizeStartWidth = useRef(0);

  // Load saved panel width on component mount
  useEffect(() => {
    const loadSavedPanelWidth = () => {
      try {
        const savedWidth = localStorage.getItem(`jira-panel-width-${projectId}`);
        if (savedWidth) {
          const width = parseInt(savedWidth, 10);
          if (!isNaN(width) && width >= 320 && width <= 800) {
            setPanelWidth(width);
            setIsCollapsed(width <= 320);
          }
        }
      } catch (error) {
        console.debug('[Jira] Failed to load saved panel width:', error);
      }
    };

    if (projectId) {
      loadSavedPanelWidth();
    }
  }, [projectId]);

  // Save panel width when it changes (but not when collapsed)
  useEffect(() => {
    if (projectId && !isCollapsed) {
      try {
        localStorage.setItem(`jira-panel-width-${projectId}`, panelWidth.toString());
      } catch (error) {
        console.debug('[Jira] Failed to save panel width:', error);
      }
    }
  }, [panelWidth, projectId, isCollapsed]);

  // Load connection status
  useEffect(() => {
    if (open) {
      loadConnectionStatus();
    }
  }, [open, projectId]);

  // Load cached work items on component mount
  useEffect(() => {
    const loadCachedWorkItems = () => {
      try {
        const cacheKey = `jira-workitems-cache-${projectId}`;
        const cacheTimeKey = `jira-workitems-cache-time-${projectId}`;

        const cachedData = localStorage.getItem(cacheKey);
        const cachedTime = localStorage.getItem(cacheTimeKey);

        if (cachedData && cachedTime) {
          const cacheTime = parseInt(cachedTime, 10);
          const now = Date.now();
          const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

          if (now - cacheTime < CACHE_DURATION) {
            const workItems = JSON.parse(cachedData);
            setWorkItems(workItems);
            setLastCacheTime(cacheTime);
            console.debug('[Jira] Using cached work items');
            return;
          }
        }
      } catch (error) {
        console.debug('[Jira] Failed to load cached work items:', error);
      }
    };

    if (projectId) {
      loadCachedWorkItems();
    }
  }, [projectId]);

  // Load work items when panel opens (with cache logic)
  useEffect(() => {
    if (open && syncStatus?.connected) {
      const now = Date.now();
      const CACHE_DURATION = 5 * 60 * 1000;

      if (!lastCacheTime || now - lastCacheTime > CACHE_DURATION) {
        loadWorkItems();
      } else {
        console.debug('[Jira] Using recent cache, skipping refresh');
      }
    }
  }, [open, syncStatus?.connected, lastCacheTime]);

  const loadConnectionStatus = async () => {
    try {
      const result = await window.electronAPI.checkJiraConnection(projectId);
      if (result.success) {
        setSyncStatus(result.data ?? null);
        if (!result.data?.connected) {
          setError(result.data?.error || 'Jira not configured');
        }
      } else {
        setError(result.error || 'Failed to check Jira connection');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  const loadWorkItems = async (forceRefresh = false) => {
    if (!forceRefresh && lastCacheTime) {
      const now = Date.now();
      const CACHE_DURATION = 5 * 60 * 1000;
      if (now - lastCacheTime < CACHE_DURATION) {
        console.debug('[Jira] Using recent cache, skipping load');
        return;
      }
    }

    setIsLoadingItems(true);
    setError(null);
    try {
      const result = await window.electronAPI.getJiraIssues(projectId, 100);

      if (result.success) {
        const workItems = result.data || [];
        setWorkItems(workItems);

        // Save to cache
        try {
          const cacheKey = `jira-workitems-cache-${projectId}`;
          const cacheTimeKey = `jira-workitems-cache-time-${projectId}`;
          const now = Date.now();

          localStorage.setItem(cacheKey, JSON.stringify(workItems));
          localStorage.setItem(cacheTimeKey, now.toString());
          setLastCacheTime(now);

          console.debug('[Jira] Work items cached successfully');
        } catch (cacheError) {
          console.debug('[Jira] Failed to cache work items:', cacheError);
        }
      } else {
        setError(result.error || 'Failed to load Jira issues');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoadingItems(false);
    }
  };

  const handleRefresh = () => {
    setSelectedIds(new Set());
    setSearchQuery('');
    setFilters({ workItemType: 'all', state: 'all' });

    setIsRefreshing(true);
    loadWorkItems(true).finally(() => {
      setIsRefreshing(false);
    });
  };

  // Filter work items
  const filteredItems = useMemo(() => {
    return workItems.filter((item) => {
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const matchesSearch =
          item.title.toLowerCase().includes(query) ||
          item.id.toLowerCase().includes(query) ||
          (item.description && item.description.toLowerCase().includes(query));
        if (!matchesSearch) return false;
      }

      if (filters.workItemType !== 'all' && item.workItemType !== filters.workItemType) {
        return false;
      }

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
  const toggleItem = useCallback((id: string) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedIds(newSelected);
  }, [selectedIds]);

  const selectAll = useCallback(() => {
    setSelectedIds(new Set(filteredItems.map((item) => item.id)));
  }, [filteredItems]);

  const deselectAll = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const isAllSelected = filteredItems.length > 0 && selectedIds.size === filteredItems.length;
  const isSomeSelected = selectedIds.size > 0 && selectedIds.size < filteredItems.length;

  // Resize handlers
  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    setIsResizing(true);
    resizeStartX.current = e.clientX;
    resizeStartWidth.current = panelWidth;
  }, [panelWidth]);

  const handleResizeMove = useCallback((e: MouseEvent) => {
    if (!isResizing) return;

    const deltaX = resizeStartX.current - e.clientX;
    const newWidth = Math.min(Math.max(resizeStartWidth.current + deltaX, 320), 800);
    setPanelWidth(newWidth);
    setIsCollapsed(newWidth <= 320);
  }, [isResizing]);

  const handleResizeEnd = useCallback(() => {
    setIsResizing(false);
  }, []);

  // Toggle collapse function
  const toggleCollapse = useCallback(() => {
    if (isCollapsed) {
      let restoredWidth = 384;
      try {
        const savedWidth = localStorage.getItem(`jira-panel-width-${projectId}`);
        if (savedWidth) {
          const width = parseInt(savedWidth, 10);
          if (!isNaN(width) && width >= 320 && width <= 800) {
            restoredWidth = width;
          }
        }
      } catch (error) {
        console.debug('[Jira] Failed to load saved panel width for restore:', error);
      }

      setPanelWidth(restoredWidth);
      setIsCollapsed(false);
    } else {
      try {
        localStorage.setItem(`jira-panel-width-${projectId}`, panelWidth.toString());
      } catch (error) {
        console.debug('[Jira] Failed to save panel width before collapse:', error);
      }

      setPanelWidth(320);
      setIsCollapsed(true);
    }
  }, [isCollapsed, projectId, panelWidth]);

  // Add global mouse event listeners for resize
  useEffect(() => {
    if (isResizing) {
      document.addEventListener('mousemove', handleResizeMove);
      document.addEventListener('mouseup', handleResizeEnd);
      return () => {
        document.removeEventListener('mousemove', handleResizeMove);
        document.removeEventListener('mouseup', handleResizeEnd);
      };
    }
  }, [isResizing, handleResizeMove, handleResizeEnd]);

  // Drag handlers - uses 'jira-workitems' type to distinguish from Azure DevOps
  const handleDragStart = useCallback((e: React.DragEvent, workItemIds: string[]) => {
    console.log('[Jira] Drag start:', workItemIds);
    const itemsToDrag = workItemIds
      .map(id => workItems.find(item => item.id === id))
      .filter((item): item is JiraWorkItem => item !== undefined);

    const dragData = {
      type: 'jira-workitems',
      workItems: itemsToDrag
    };

    console.log('[Jira] Drag data:', dragData);
    e.dataTransfer.setData('application/json', JSON.stringify(dragData));
    e.dataTransfer.effectAllowed = 'copy';
    setDraggedIds(new Set(workItemIds));

    const customEvent = new CustomEvent('jira-drag-start', {
      detail: dragData,
      bubbles: true,
      cancelable: true
    });
    document.dispatchEvent(customEvent);
  }, [workItems]);

  const handleDragEnd = useCallback(() => {
    console.log('[Jira] Drag end');
    setDraggedIds(new Set());
  }, []);

  // Get color for work item type badge
  const getTypeColor = (type: string): string => {
    switch (type.toLowerCase()) {
      case 'bug':
        return 'bg-red-500/10 text-red-500 border-red-500/20';
      case 'task':
        return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
      case 'story':
        return 'bg-green-500/10 text-green-500 border-green-500/20';
      case 'epic':
        return 'bg-orange-500/10 text-orange-500 border-orange-500/20';
      case 'sub-task':
        return 'bg-cyan-500/10 text-cyan-500 border-cyan-500/20';
      default:
        return 'bg-gray-500/10 text-gray-500 border-gray-500/20';
    }
  };

  // Get priority badge color
  const getPriorityColor = (priority?: string): string => {
    switch (priority?.toLowerCase()) {
      case 'highest':
      case 'critical':
        return 'bg-red-500/10 text-red-500 border-red-500/20';
      case 'high':
        return 'bg-orange-500/10 text-orange-500 border-orange-500/20';
      case 'medium':
        return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
      case 'low':
        return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
      case 'lowest':
        return 'bg-gray-500/10 text-gray-500 border-gray-500/20';
      default:
        return 'bg-gray-500/10 text-gray-500 border-gray-500/20';
    }
  };

  const selectedWorkItems = workItems.filter(item => selectedIds.has(item.id));

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-300 flex">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/20"
        onClick={() => onOpenChange(false)}
      />

      {/* Panel */}
      <div
        className="absolute right-0 top-0 h-full bg-background border-l border-border shadow-2xl flex flex-col"
        style={{ width: `${panelWidth}px` }}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-2">
            <Download className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold">Jira Import</h2>
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleCollapse}
              className="h-7 w-7"
              title={isCollapsed ? "Agrandir" : "Réduire"}
            >
              {isCollapsed ? <ChevronLeft className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onOpenChange(false)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Connection Info */}
        {syncStatus?.projectKey && (
          <div className="px-4 py-2 bg-muted/50 border-b border-border">
            <p className="text-sm text-foreground/70">
              <strong>Project:</strong>{' '}
              {syncStatus.projectKey}
              {syncStatus.instanceUrl && (
                <span className="ml-2 text-xs text-muted-foreground">({syncStatus.instanceUrl})</span>
              )}
            </p>
          </div>
        )}

        {/* Error Banner */}
        {error && (
          <div className="mx-4 mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-md">
            <p className="text-sm text-red-500 mb-3">{error}</p>
            {error.includes('not configured') && onOpenSettings && (
              <Button
                variant="outline"
                size="sm"
                onClick={onOpenSettings}
                className="gap-2"
              >
                <Settings className="h-4 w-4" />
                {t('settings:jiraImport.configureButton')}
              </Button>
            )}
          </div>
        )}

        {/* Search and Filters */}
        {syncStatus?.connected && (
          <div className="p-4 space-y-4 border-b border-border">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search issues..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>

            {/* Filters */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs text-foreground/70 mb-1 block">
                  Type
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
                    <SelectItem value="all">All Types</SelectItem>
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
                  Status
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
                    <SelectItem value="all">All Statuses</SelectItem>
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
              <div className="flex items-center justify-between py-2">
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
                    {selectedIds.size} / {filteredItems.length} selected
                  </span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleRefresh}
                  disabled={isLoadingItems || isRefreshing}
                  title={isRefreshing ? "Refreshing..." : "Refresh (bypass cache)"}
                >
                  <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin text-primary' : isLoadingItems ? 'animate-spin' : ''}`} />
                </Button>
              </div>
            )}
          </div>
        )}

        {/* Work Items List */}
        <ScrollArea className="flex-1">
          {isLoadingItems ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : filteredItems.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground px-4">
              <p>No Jira issues found</p>
              {(searchQuery || filters.workItemType !== 'all' || filters.state !== 'all') && (
                <p className="text-sm mt-2">Try adjusting your filters</p>
              )}
            </div>
          ) : (
            <div className="p-4 space-y-2">
              {filteredItems.map((item) => (
                <div
                  key={item.id}
                  className={cn(
                    "flex items-start gap-3 p-3 rounded-md border transition-all cursor-pointer",
                    "hover:bg-muted/50",
                    selectedIds.has(item.id) && "bg-primary/10 border-primary/30 cursor-grab",
                    draggedIds.has(item.id) && "cursor-grabbing opacity-50"
                  )}
                  onClick={() => toggleItem(item.id)}
                  draggable={selectedIds.has(item.id)}
                  onDragStart={(e) => {
                    console.log('[Jira] Drag start triggered for item:', item.id);
                    if (selectedIds.has(item.id)) {
                      handleDragStart(e, Array.from(selectedIds));
                    } else {
                      e.preventDefault();
                    }
                  }}
                  onDragEnd={handleDragEnd}
                >
                  <Checkbox
                    checked={selectedIds.has(item.id)}
                    onCheckedChange={() => toggleItem(item.id)}
                    onClick={(e) => e.stopPropagation()}
                  />

                  {selectedIds.has(item.id) && (
                    <GripVertical className="h-4 w-4 text-muted-foreground cursor-grab" />
                  )}

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-xs text-muted-foreground">
                        {item.id}
                      </span>
                      <Badge variant="outline" className={getTypeColor(item.workItemType)}>
                        {item.workItemType}
                      </Badge>
                      <Badge variant="outline">{item.state}</Badge>
                      {item.priority && (
                        <Badge variant="outline" className={getPriorityColor(item.priority)}>
                          {item.priority}
                        </Badge>
                      )}
                    </div>
                    <h4 className="font-medium text-sm mb-1 truncate">{item.title}</h4>
                    {item.description && (
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {item.description}
                      </p>
                    )}
                    {item.assignedTo && (
                      <p className="text-xs text-muted-foreground mt-1">
                        Assignee: {item.assignedTo}
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

        {/* Footer */}
        {selectedWorkItems.length > 0 && (
          <div className="p-4 border-t border-border space-y-3">
            <div className="flex items-center gap-2 text-sm text-foreground/70">
              <Download className="h-4 w-4" />
              <span>Drag selected issues to a Kanban column to import</span>
            </div>

            <div className="text-xs text-muted-foreground bg-muted/50 p-2 rounded">
              {selectedWorkItems.length} item(s) selected
              <div className="mt-1 space-y-1">
                {selectedWorkItems.slice(0, 3).map((item) => (
                  <div key={item.id} className="flex items-center gap-2">
                    <span className="font-mono">{item.id}</span>
                    <span className="truncate">{item.title}</span>
                  </div>
                ))}
                {selectedWorkItems.length > 3 && (
                  <div>+{selectedWorkItems.length - 3} more</div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Resize handle */}
        <div
          className="absolute left-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-primary/20 transition-colors"
          onMouseDown={handleResizeStart}
          title="Resize"
        >
          <div className="absolute inset-y-0 -left-2 -right-2" />
        </div>
      </div>
    </div>
  );
}
