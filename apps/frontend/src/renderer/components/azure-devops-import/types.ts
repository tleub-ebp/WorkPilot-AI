/**
 * Azure DevOps Integration Types
 */

export interface AzureDevOpsWorkItem {
  id: number;
  title: string;
  description?: string;
  state: string;
  workItemType: string;
  assignedTo?: string;
  tags: string[];
  priority?: number;
  createdDate?: string;
  areaPath?: string;
  iterationPath?: string;
  url?: string;
}

export interface AzureDevOpsImportModalProps {
  projectId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImportComplete?: () => void;
}

export interface AzureDevOpsFilters {
  workItemType: string; // 'all' | 'Bug' | 'Task' | 'User Story' | etc.
  state: string; // 'all' | 'Active' | 'New' | 'Closed' | etc.
  assignedTo: string; // 'all' | 'me' | 'unassigned'
}
