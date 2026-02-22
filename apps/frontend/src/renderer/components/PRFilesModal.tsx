import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { ScrollArea } from './ui/scroll-area';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { DiffViewer } from './ui/diff-viewer';
import { Loader2, FileText, GitPullRequest, ExternalLink, Plus, Minus, ChevronRight, ChevronDown } from 'lucide-react';
import { cn } from '../lib/utils';

interface PRFileData {
  filename: string;
  status: 'added' | 'removed' | 'modified' | 'renamed';
  additions: number;
  deletions: number;
  changes: number;
  patch?: string;
  previous_filename?: string;
}

interface PRData {
  number: number;
  title: string;
  body: string;
  author: string;
  state: string;
  source_branch: string;
  target_branch: string;
  additions: number;
  deletions: number;
  changed_files: number;
  files: PRFileData[];
  diff: string;
  url: string;
  created_at: string;
  updated_at: string;
  labels: string[];
  reviewers: string[];
  is_draft: boolean;
  mergeable: boolean;
}

interface PRFilesModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  prUrl: string;
  taskId?: string;
}

export function PRFilesModal({ open, onOpenChange, prUrl, taskId }: PRFilesModalProps) {
  const { t } = useTranslation(['taskReview', 'common']);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [prData, setPrData] = useState<PRData | null>(null);
  const [expandedFiles, setExpandedFiles] = useState<Set<string>>(new Set());

  console.log('[PRFilesModal] Component render:', { open, prUrl, taskId });

  // Reset state when modal opens/closes
  useEffect(() => {
    console.log('[PRFilesModal] useEffect triggered:', { open, prUrl });
    if (open && prUrl) {
      console.log('[PRFilesModal] Fetching PR details...');
      fetchPRDetails();
    } else {
      setPrData(null);
      setError(null);
      setExpandedFiles(new Set());
    }
  }, [open, prUrl]);

  const fetchPRDetails = async () => {
    if (!prUrl) return;

    setLoading(true);
    setError(null);

    try {
      // Extract PR number from URL (GitHub format: https://github.com/owner/repo/pull/123)
      // or Azure DevOps format: https://dev.azure.com/org/project/_git/repo/pullrequest/123
      let prMatch = prUrl.match(/\/pull\/(\d+)/);
      let prNumber: number;
      
      if (!prMatch) {
        // Try Azure DevOps format
        const adoMatch = prUrl.match(/\/pullrequest\/(\d+)/);
        if (!adoMatch) {
          throw new Error('Invalid PR URL format - expected GitHub or Azure DevOps URL');
        }
        prNumber = parseInt(adoMatch[1]);
        console.log('[PRFilesModal] Detected Azure DevOps PR:', prNumber);
      } else {
        prNumber = parseInt(prMatch[1]);
        console.log('[PRFilesModal] Detected GitHub PR:', prNumber);
      }
      
      // Call IPC to get PR details with files
      const result = await window.electronAPI?.getPRDetails?.(prNumber, taskId);
      
      if (!result?.success) {
        throw new Error(result?.error || 'Failed to fetch PR details');
      }

      setPrData(result.data?.data ?? null);
      
      // Debug: Log the structure of files data
      if (result.data?.data?.files) {
        console.log('[PRFilesModal] Files data structure:', result.data.data.files);
        console.log('[PRFilesModal] First file sample:', result.data.data.files[0]);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      console.error('[PRFilesModal] Failed to fetch PR data:', err);
    } finally {
      setLoading(false);
    }
  };

  const getFilePatch = (file: PRFileData): string => {
    console.log(`[PRFilesModal] Getting patch for file: ${file.filename}`, {
      hasPatch: !!file.patch,
      patchLength: file.patch?.length,
      hasGlobalDiff: !!prData?.diff,
      globalDiffLength: prData?.diff?.length
    });
    
    // If file has its own patch, use it
    if (file.patch) {
      console.log(`[PRFilesModal] Using file's own patch for ${file.filename}`);
      return file.patch;
    }
    
    // Otherwise, try to extract from the global diff
    if (prData?.diff && file.filename) {
      try {
        console.log(`[PRFilesModal] Attempting to extract patch from global diff for ${file.filename}`);
        // Simple extraction: look for the file in the global diff
        const lines = prData.diff.split('\n');
        let inFileSection = false;
        let fileLines: string[] = [];
        
        for (let i = 0; i < lines.length; i++) {
          const line = lines[i];
          
          // Check if we're starting this file's section
          if (line.startsWith(`diff --git a/${file.filename} b/${file.filename}`) ||
              line.includes(` b/${file.filename}`)) {
            inFileSection = true;
            fileLines = [line];
            console.log(`[PRFilesModal] Found file section for ${file.filename} at line ${i}`);
            continue;
          }
          
          // If we're in a file section and hit the next file, stop
          if (inFileSection && line.startsWith('diff --git')) {
            console.log(`[PRFilesModal] End of file section for ${file.filename}`);
            break;
          }
          
          // Add lines if we're in this file's section
          if (inFileSection) {
            fileLines.push(line);
          }
        }
        
        const result = fileLines.length > 0 ? fileLines.join('\n') : '';
        console.log(`[PRFilesModal] Extracted ${fileLines.length} lines for ${file.filename}`);
        return result;
      } catch (err) {
        console.warn(`Failed to extract patch for ${file.filename}:`, err);
        return '';
      }
    }
    
    console.log(`[PRFilesModal] No patch available for ${file.filename}`);
    return '';
  };

  const toggleFileExpansion = (filename: string) => {
    console.log(`[PRFilesModal] Toggle file expansion called for: ${filename}`);
    setExpandedFiles(prev => {
      const next = new Set(prev);
      if (next.has(filename)) {
        console.log(`[PRFilesModal] Collapsing file: ${filename}`);
        next.delete(filename);
      } else {
        console.log(`[PRFilesModal] Expanding file: ${filename}`);
        next.add(filename);
      }
      return next;
    });
  };

  const getFileStatusIcon = (status: string) => {
    switch (status) {
      case 'added':
        return <Plus className="h-4 w-4 text-green-500" />;
      case 'removed':
        return <Minus className="h-4 w-4 text-red-500" />;
      case 'modified':
        return <ChevronRight className="h-4 w-4 text-yellow-500" />;
      case 'renamed':
        return <ChevronRight className="h-4 w-4 text-blue-500" />;
      default:
        return <FileText className="h-4 w-4 text-gray-500" />;
    }
  };

  const getFileStatusVariant = (status: string): "default" | "secondary" | "destructive" | "outline" => {
    switch (status) {
      case 'added':
        return 'default';
      case 'removed':
        return 'destructive';
      case 'modified':
        return 'outline';
      case 'renamed':
        return 'secondary';
      default:
        return 'secondary';
    }
  };

  const openPRInBrowser = () => {
    if (prUrl && window.electronAPI?.openExternal) {
      window.electronAPI.openExternal(prUrl);
    }
  };

  if (loading) {
    console.log('[PRFilesModal] Rendering loading state');
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-7xl max-h-[95vh] w-[95vw] h-[90vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="sr-only">Loading PR files</DialogTitle>
            <DialogDescription className="sr-only">Loading pull request files...</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col items-center justify-center py-8 flex-1">
            <Loader2 className="h-8 w-8 animate-spin text-primary mb-4" />
            <p className="text-muted-foreground">{t('taskReview:pr.files.loading')}</p>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  if (error) {
    console.log('[PRFilesModal] Rendering error state:', error);
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-7xl max-h-[95vh] w-[95vw] h-[90vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-destructive">
              <GitPullRequest className="h-5 w-5" />
              {t('taskReview:pr.files.errorTitle')}
            </DialogTitle>
            <DialogDescription>
              {t('taskReview:pr.files.errorDescription')}
            </DialogDescription>
          </DialogHeader>
          <div className="py-4 flex-1 overflow-auto">
            <p className="text-sm text-destructive whitespace-pre-wrap">{error}</p>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={openPRInBrowser}>
              <ExternalLink className="h-4 w-4 mr-2" />
              {t('taskReview:pr.files.openInBrowser')}
            </Button>
            <Button onClick={() => onOpenChange(false)}>
              {t('common:buttons.close')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  if (!prData) {
    console.log('[PRFilesModal] No PR data, rendering null');
    return null;
  }

  console.log('[PRFilesModal] Rendering main content with', prData.files.length, 'files');

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-7xl max-h-[95vh] w-[95vw] h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <GitPullRequest className="h-5 w-5 text-primary" />
            {t('taskReview:pr.files.title')} #{prData.number}
          </DialogTitle>
          <DialogDescription className="flex items-center gap-2">
            <span>{prData.title}</span>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2"
              onClick={openPRInBrowser}
            >
              <ExternalLink className="h-3 w-3 mr-1" />
              {t('taskReview:pr.files.openInGitHub')}
            </Button>
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="files" className="flex-1 overflow-hidden">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="overview">{t('taskReview:pr.files.overview')}</TabsTrigger>
            <TabsTrigger value="files">
              {t('taskReview:pr.files.files')} ({prData.changed_files})
            </TabsTrigger>
            <TabsTrigger value="diff">{t('taskReview:pr.files.diff')}</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="mt-4 flex-1 overflow-auto">
            <div className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-4 border rounded-lg">
                  <div className="text-2xl font-bold text-green-500">+{prData.additions}</div>
                  <div className="text-sm text-muted-foreground">{t('taskReview:pr.files.additions')}</div>
                </div>
                <div className="text-center p-4 border rounded-lg">
                  <div className="text-2xl font-bold text-red-500">-{prData.deletions}</div>
                  <div className="text-sm text-muted-foreground">{t('taskReview:pr.files.deletions')}</div>
                </div>
                <div className="text-center p-4 border rounded-lg">
                  <div className="text-2xl font-bold">{prData.changed_files}</div>
                  <div className="text-sm text-muted-foreground">{t('taskReview:pr.files.changedFiles')}</div>
                </div>
                <div className="text-center p-4 border rounded-lg">
                  <div className="text-2xl font-bold">{prData.additions + prData.deletions}</div>
                  <div className="text-sm text-muted-foreground">{t('taskReview:pr.files.totalChanges')}</div>
                </div>
              </div>

              <div className="space-y-2">
                <h4 className="font-semibold">{t('taskReview:pr.files.details')}</h4>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-muted-foreground">{t('taskReview:pr.files.author')}: </span>
                    <span>{prData.author}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">{t('taskReview:pr.files.sourceBranch')}: </span>
                    <span className="font-mono">{prData.source_branch}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">{t('taskReview:pr.files.targetBranch')}: </span>
                    <span className="font-mono">{prData.target_branch}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">{t('taskReview:pr.files.state')}: </span>
                    <Badge variant={prData.state === 'open' ? 'default' : 'secondary'}>
                      {prData.state}
                    </Badge>
                  </div>
                </div>
              </div>

              {prData.body && (
                <div className="space-y-2">
                  <h4 className="font-semibold">{t('taskReview:pr.files.description')}</h4>
                  <div className="p-3 border rounded-md bg-muted/50">
                    <pre className="whitespace-pre-wrap text-sm">{prData.body}</pre>
                  </div>
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="files" className="mt-4">
            <ScrollArea className="h-[500px] rounded-md border">
              <div className="p-4 space-y-2">
                {prData.files.map((file, index) => (
                  <div
                    key={index}
                    className="border rounded-lg overflow-hidden"
                  >
                    <div
                      className={cn(
                        "flex items-center justify-between p-3 cursor-pointer hover:bg-muted/50 transition-colors"
                      )}
                      onClick={() => {
                        console.log(`[PRFilesModal] File clicked: ${file.filename}`);
                        toggleFileExpansion(file.filename);
                      }}
                    >
                      <div className="flex items-center gap-2">
                        {getFileStatusIcon(file.status)}
                        <span className="font-mono text-sm">{file.filename}</span>
                        {file.previous_filename && (
                          <span className="text-xs text-muted-foreground">
                            (was: {file.previous_filename})
                          </span>
                        )}
                        <ChevronRight 
                          className={cn(
                            "h-4 w-4 text-muted-foreground transition-transform",
                            expandedFiles.has(file.filename) && "rotate-90"
                          )} 
                        />
                      </div>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <span className="text-green-600">+{file.additions}</span>
                        <span className="text-red-600">-{file.deletions}</span>
                      </div>
                    </div>
                    {expandedFiles.has(file.filename) && (
                      <div className="border-t">
                        <div className="p-3">
                          <DiffViewer 
                            patch={getFilePatch(file)}
                            className="max-h-[400px] overflow-auto border rounded"
                          />
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="diff" className="mt-4">
            <ScrollArea className="h-[500px] rounded-md border">
              <div className="p-4">
                <DiffViewer 
                  patch={prData.diff}
                  className="max-h-full"
                />
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}

export default PRFilesModal;