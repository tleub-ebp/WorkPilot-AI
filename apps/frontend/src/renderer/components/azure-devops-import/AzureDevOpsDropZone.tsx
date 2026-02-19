/**
 * Azure DevOps Drop Zone Component
 * Provides a drop zone for Azure DevOps work items within Kanban columns
 */

import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Download, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { TaskStatus } from '../../../shared/types';
import type { AzureDevOpsWorkItem } from '../../../shared/types/integrations';

interface AzureDevOpsDropZoneProps {
  columnStatus: TaskStatus;
  onWorkItemsImported: (workItems: AzureDevOpsWorkItem[], targetStatus: TaskStatus) => void;
  children: React.ReactNode;
  className?: string;
}

export function AzureDevOpsDropZone({ 
  columnStatus, 
  onWorkItemsImported, 
  children, 
  className 
}: AzureDevOpsDropZoneProps) {
  const { t } = useTranslation('settings');
  const [isHovered, setIsHovered] = useState(false);
  const [draggedWorkItems, setDraggedWorkItems] = useState<AzureDevOpsWorkItem[]>([]);

  const handleDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.stopPropagation();
    
    // Check if dragging Azure DevOps work items
    const items = event.dataTransfer.getData('application/json');
    if (items) {
      try {
        const parsed = JSON.parse(items);
        if (parsed.type === 'azure-devops-workitems') {
          setDraggedWorkItems(parsed.workItems || []);
          setIsHovered(true);
          // Prevent dnd-kit from handling this drag event
          event.nativeEvent.stopImmediatePropagation();
        }
      } catch {
        // Invalid JSON, ignore
      }
    }
  }, []);

  const handleDragLeave = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.stopPropagation();
    event.nativeEvent.stopImmediatePropagation();
    setIsHovered(false);
    setDraggedWorkItems([]);
  }, []);

  const handleDrop = useCallback(async (event: React.DragEvent) => {
    event.preventDefault();
    event.stopPropagation();
    event.nativeEvent.stopImmediatePropagation();
    
    const items = event.dataTransfer.getData('application/json');
    if (!items) return;
    
    try {
      const parsed = JSON.parse(items);
      if (parsed.type === 'azure-devops-workitems' && parsed.workItems?.length > 0) {
        await onWorkItemsImported(parsed.workItems, columnStatus);
      }
    } catch (error) {
      console.error('Failed to parse dropped items:', error);
    } finally {
      setIsHovered(false);
      setDraggedWorkItems([]);
    }
  }, [columnStatus, onWorkItemsImported]);

  const isActive = isHovered;
  const hasItems = draggedWorkItems.length > 0;

  return (
    <div
      className={cn('relative flex-1', className)}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      data-column-status={columnStatus}
      style={{ zIndex: 100 }}
    >
      {children}
      
      {/* Drop Zone Overlay */}
      {isActive && (
        <div className="absolute inset-0 bg-primary/10 border-2 border-dashed border-primary/70 rounded-lg flex items-center justify-center z-200 pointer-events-auto">
          <div className="text-center space-y-2 p-4 bg-background/98 rounded-lg border border-primary/30 shadow-lg">
            <div className="flex items-center justify-center gap-2">
              <Download className="h-6 w-6 text-primary animate-bounce" />
              <ArrowRight className="h-4 w-4 text-primary" />
              <div className="text-2xl">📋</div>
            </div>
            
            <div className="space-y-1">
              <p className="font-medium text-primary">
                {hasItems 
                  ? t('azureDevOpsImport.dropZoneItems', { count: draggedWorkItems.length })
                  : t('azureDevOpsImport.dropZone')
                }
              </p>
              
              {hasItems && (
                <div className="text-sm text-muted-foreground">
                  {draggedWorkItems.slice(0, 3).map((item, idx) => (
                    <div key={item.id} className="flex items-center gap-2 justify-center">
                      <span className="font-mono text-xs">#{item.id}</span>
                      <span className="truncate max-w-[200px]">{item.title}</span>
                      <span className="text-xs bg-blue-500/10 text-blue-500 px-1 rounded">
                        {item.workItemType}
                      </span>
                    </div>
                  ))}
                  {draggedWorkItems.length > 3 && (
                    <div className="text-xs text-muted-foreground">
                      +{draggedWorkItems.length - 3} {t('azureDevOpsImport.moreItems')}
                    </div>
                  )}
                </div>
              )}
              
              <p className="text-xs text-muted-foreground">
                {t('azureDevOpsImport.dropToColumn', { 
                  column: t(`tasks:status.${columnStatus}`) 
                })}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
