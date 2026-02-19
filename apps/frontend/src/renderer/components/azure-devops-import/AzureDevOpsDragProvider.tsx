/**
 * Azure DevOps Drag Provider
 * Provides drag and drop context for Azure DevOps work items
 */

import { createContext, useContext, ReactNode } from 'react';
import type { AzureDevOpsWorkItem } from '../../../shared/types/integrations';

interface AzureDevOpsDragContextType {
  onWorkItemsImported: (workItems: AzureDevOpsWorkItem[], targetStatus: string) => Promise<void>;
}

const AzureDevOpsDragContext = createContext<AzureDevOpsDragContextType | null>(null);

interface AzureDevOpsDragProviderProps {
  children: ReactNode;
  onWorkItemsImported: (workItems: AzureDevOpsWorkItem[], targetStatus: string) => Promise<void>;
}

export function AzureDevOpsDragProvider({ 
  children, 
  onWorkItemsImported 
}: AzureDevOpsDragProviderProps) {
  return (
    <AzureDevOpsDragContext.Provider value={{ onWorkItemsImported }}>
      {children}
    </AzureDevOpsDragContext.Provider>
  );
}

export function useAzureDevOpsDrag() {
  const context = useContext(AzureDevOpsDragContext);
  if (!context) {
    throw new Error('useAzureDevOpsDrag must be used within AzureDevOpsDragProvider');
  }
  return context;
}
