/**
 * Import Confirm Dialog
 * Shows a confirmation dialog when importing work items (Azure DevOps / Jira)
 * Allows the user to enable "Require human review before coding" for imported tasks.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Download, Loader2 } from 'lucide-react';
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../ui/alert-dialog';
import { Button } from '../ui/button';
import { Checkbox } from '../ui/checkbox';
import { Label } from '../ui/label';
import { ScrollArea } from '../ui/scroll-area';
import { Badge } from '../ui/badge';
import type { TaskStatus } from '../../../shared/types';

/**
 * Common work item shape accepted by the import dialog.
 * Both AzureDevOpsWorkItem and JiraWorkItem satisfy this interface.
 */
export interface ImportableWorkItem {
  id: string | number;
  title: string;
  description?: string;
  state: string;
  workItemType: string;
  tags: string[];
}

interface ImportConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workItems: ImportableWorkItem[];
  targetColumn: TaskStatus | null;
  isImporting: boolean;
  onConfirm: (requireReviewBeforeCoding: boolean) => void;
}

export function ImportConfirmDialog({
  open,
  onOpenChange,
  workItems,
  targetColumn,
  isImporting,
  onConfirm,
}: ImportConfirmDialogProps) {
  const { t } = useTranslation(['settings', 'tasks', 'common']);
  const [requireReviewBeforeCoding, setRequireReviewBeforeCoding] = useState(false);

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
    <AlertDialog open={open} onOpenChange={(newOpen) => {
      if (!isImporting) {
        onOpenChange(newOpen);
      }
    }}>
      <AlertDialogContent className="sm:max-w-[550px]">
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <Download className="h-5 w-5" />
            {t('settings:azureDevOpsImport.importConfirmTitle', {
              count: workItems.length,
            })}
          </AlertDialogTitle>
          <AlertDialogDescription>
            {t('settings:azureDevOpsImport.importConfirmDescription', {
              column: targetColumn ? t(`tasks:status.${targetColumn}`) : '',
            })}
          </AlertDialogDescription>
        </AlertDialogHeader>

        {/* Work Items Preview */}
        <ScrollArea className="max-h-48 rounded-md border border-border p-2">
          <div className="space-y-1">
            {workItems.map((item) => (
              <div
                key={item.id}
                className="flex items-center gap-2 text-sm py-1.5 px-2 rounded hover:bg-muted/50"
              >
                <span className="font-mono text-xs text-muted-foreground shrink-0">
                  #{item.id}
                </span>
                <Badge variant="outline" className={`${getTypeColor(item.workItemType)} shrink-0 text-xs`}>
                  {item.workItemType}
                </Badge>
                <span className="truncate">{item.title}</span>
              </div>
            ))}
          </div>
        </ScrollArea>

        {/* Review Requirement Toggle */}
        <div className="flex items-start gap-3 p-4 rounded-lg border border-border bg-muted/30">
          <Checkbox
            id="import-require-review"
            checked={requireReviewBeforeCoding}
            onCheckedChange={(checked) => setRequireReviewBeforeCoding(checked === true)}
            disabled={isImporting}
            className="mt-0.5"
          />
          <div className="flex-1 space-y-1">
            <Label
              htmlFor="import-require-review"
              className="text-sm font-medium text-foreground cursor-pointer"
            >
              {t('tasks:form.requireReviewLabel')}
            </Label>
            <p className="text-xs text-muted-foreground">
              {t('tasks:form.requireReviewDescription')}
            </p>
          </div>
        </div>

        <AlertDialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isImporting}
          >
            {t('common:buttons.cancel')}
          </Button>
          <Button
            onClick={() => onConfirm(requireReviewBeforeCoding)}
            disabled={isImporting}
          >
            {isImporting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                {t('settings:azureDevOpsImport.importing')}
              </>
            ) : (
              <>
                <Download className="h-4 w-4 mr-2" />
                {t('settings:azureDevOpsImport.importConfirmButton', {
                  count: workItems.length,
                })}
              </>
            )}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
