import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  AlertTriangle, 
  Check, 
  Copy, 
  GitBranch, 
  GitMerge, 
  Loader2, 
  RefreshCw, 
  Shield, 
  TriangleAlert, 
  X, 
  FileText,
  Users,
  Target,
  Zap
} from 'lucide-react';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { ScrollArea } from '../ui/scroll-area';

import {
  useConflictPredictorStore,
  startConflictPrediction,
  setupConflictPredictorListeners,
} from '../../stores/conflict-predictor-store';
import { useProjectStore } from '../../stores/project-store';

/**
 * ConflictPredictorDialog — AI-powered conflict prediction dialog.
 *
 * Shows a dialog where users can analyze potential conflicts between
 * worktrees and branches before they occur.
 *
 * Usage:
 *   const { openDialog, closeDialog, isOpen } = useConflictPredictorStore();
 *   <ConflictPredictorDialog />
 */
export function ConflictPredictorDialog() {
  const { t } = useTranslation(['conflictPredictor', 'common']);
  const [copied, setCopied] = useState(false);
  const streamOutputRef = useRef<HTMLPreElement>(null);

  const {
    isOpen,
    closeDialog,
    phase,
    status,
    streamingOutput,
    result,
    error,
    reset,
  } = useConflictPredictorStore();

  const selectedProjectId = useProjectStore((s) => s.selectedProjectId);

  // Setup IPC listeners once
  useEffect(() => {
    const cleanup = setupConflictPredictorListeners();
    return cleanup;
  }, []);

  // Auto-scroll streaming output
  useEffect(() => {
    if (streamOutputRef.current) {
      streamOutputRef.current.scrollTop = streamOutputRef.current.scrollHeight;
    }
  }, [streamingOutput]);

  const handleAnalyze = useCallback(() => {
    if (!selectedProjectId) return;
    startConflictPrediction(selectedProjectId);
  }, [selectedProjectId]);

  const handleRetry = useCallback(() => {
    reset();
    handleAnalyze();
  }, [handleAnalyze, reset]);

  const handleClose = useCallback(() => {
    closeDialog();
    reset();
  }, [closeDialog, reset]);

  const handleCopyResults = useCallback(async () => {
    if (!result) return;

    const reportText = generateReportText(result);
    await navigator.clipboard.writeText(reportText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [result]);

  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'critical': return 'destructive';
      case 'high': return 'destructive';
      case 'medium': return 'secondary';
      case 'low': return 'outline';
      default: return 'outline';
    }
  };

  const getRiskLevelIcon = (level: string) => {
    switch (level) {
      case 'critical': return <AlertTriangle className="h-4 w-4" />;
      case 'high': return <TriangleAlert className="h-4 w-4" />;
      case 'medium': return <Shield className="h-4 w-4" />;
      case 'low': return <Check className="h-4 w-4" />;
      default: return <Shield className="h-4 w-4" />;
    }
  };

  const getAssessmentColor = (assessment: string) => {
    if (assessment.includes('CRITICAL')) return 'text-red-600';
    if (assessment.includes('HIGH')) return 'text-orange-600';
    if (assessment.includes('MEDIUM')) return 'text-yellow-600';
    if (assessment.includes('LOW')) return 'text-green-600';
    return 'text-green-600';
  };

  const generateReportText = (result: any) => {
    let report = '# Conflict Prediction Analysis Report\n\n';
    report += `**Risk Assessment:** ${result.summary.risk_assessment}\n\n`;
    report += `**Total Worktrees:** ${result.total_worktrees}\n`;
    report += `**Active Worktrees:** ${result.active_worktrees.join(', ')}\n\n`;
    
    if (result.summary.total_conflicts > 0) {
      report += `**Conflicts Detected:** ${result.summary.total_conflicts}\n`;
      report += `- Critical: ${result.summary.critical_conflicts}\n`;
      report += `- High: ${result.summary.high_conflicts}\n`;
      report += `- Medium: ${result.summary.medium_conflicts}\n\n`;
      
      report += '## Conflicts\n\n';
      result.conflicts_detected.forEach((conflict: any, index: number) => {
        report += `### ${index + 1}. ${conflict.risk_level.toUpperCase()} - ${conflict.file_path}\n`;
        report += `**Worktrees:** ${conflict.worktree1} vs ${conflict.worktree2}\n`;
        report += `**Description:** ${conflict.description}\n`;
        report += `**Resolution:** ${conflict.resolution_strategy}\n\n`;
      });
    } else {
      report += '**✅ No conflicts detected - Safe for parallel development**\n\n';
    }
    
    if (result.recommendations.length > 0) {
      report += '## Recommendations\n\n';
      result.recommendations.forEach((rec: string, index: number) => {
        report += `${index + 1}. ${rec}\n`;
      });
      report += '\n';
    }
    
    if (result.safe_merge_order.length > 1) {
      report += '## Safe Merge Order\n\n';
      result.safe_merge_order.forEach((worktree: string, index: number) => {
        report += `${index + 1}. ${worktree}\n`;
      });
      report += '\n';
    }
    
    if (result.high_risk_areas.length > 0) {
      report += '## High Risk Areas\n\n';
      result.high_risk_areas.forEach((area: string) => {
        report += `- ${area}\n`;
      });
    }
    
    return report;
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <GitBranch className="h-5 w-5" />
            Conflict Predictor
          </DialogTitle>
          <DialogDescription>
            Proactive conflict detection between worktrees and branches
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col h-full">
          {/* Status and Progress */}
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                {phase === 'analyzing' && <Loader2 className="h-4 w-4 animate-spin" />}
                {phase === 'complete' && <Check className="h-4 w-4 text-green-600" />}
                {phase === 'error' && <AlertTriangle className="h-4 w-4 text-red-600" />}
                <span className="text-sm font-medium">{status}</span>
              </div>
              
              {phase === 'analyzing' && (
                <div className="text-xs text-muted-foreground">
                  Analyzing worktrees...
                </div>
              )}
            </div>
            
            {phase === 'analyzing' && <Progress value={66} className="h-2" />}
          </div>

          {/* Results */}
          {result && (
            <Tabs defaultValue="overview" className="flex-1">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="conflicts">Conflicts</TabsTrigger>
                <TabsTrigger value="files">Files</TabsTrigger>
                <TabsTrigger value="recommendations">Recommendations</TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="mt-4">
                <div className="space-y-4">
                  {/* Risk Assessment */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Target className="h-5 w-5" />
                        Risk Assessment
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className={`text-lg font-semibold ${getAssessmentColor(result.summary.risk_assessment)}`}>
                        {result.summary.risk_assessment}
                      </div>
                    </CardContent>
                  </Card>

                  {/* Summary Stats */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <Card>
                      <CardContent className="pt-6">
                        <div className="text-2xl font-bold">{result.total_worktrees}</div>
                        <p className="text-xs text-muted-foreground">Active Worktrees</p>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardContent className="pt-6">
                        <div className="text-2xl font-bold text-red-600">{result.summary.total_conflicts}</div>
                        <p className="text-xs text-muted-foreground">Total Conflicts</p>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardContent className="pt-6">
                        <div className="text-2xl font-bold text-orange-600">{result.summary.critical_conflicts + result.summary.high_conflicts}</div>
                        <p className="text-xs text-muted-foreground">High Risk</p>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardContent className="pt-6">
                        <div className="text-2xl font-bold text-green-600">{result.modified_files.length}</div>
                        <p className="text-xs text-muted-foreground">Files Modified</p>
                      </CardContent>
                    </Card>
                  </div>

                  {/* Active Worktrees */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Users className="h-5 w-5" />
                        Active Worktrees & Branches
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex flex-wrap gap-2">
                        {result.active_worktrees.map((worktree) => (
                          <Badge key={worktree} variant="outline">
                            <GitBranch className="h-3 w-3 mr-1" />
                            {worktree}
                          </Badge>
                        ))}
                      </div>
                    </CardContent>
                  </Card>

                  {/* Safe Merge Order */}
                  {result.safe_merge_order.length > 1 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <GitMerge className="h-5 w-5" />
                          Safe Merge Order
                        </CardTitle>
                        <CardDescription>
                          Suggested order to minimize conflicts
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2">
                          {result.safe_merge_order.map((worktree, index) => (
                            <div key={worktree} className="flex items-center gap-2">
                              <div className="w-6 h-6 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center">
                                {index + 1}
                              </div>
                              <span>{worktree}</span>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              </TabsContent>

              <TabsContent value="conflicts" className="mt-4">
                <ScrollArea className="h-[400px]">
                  <div className="space-y-3">
                    {result.conflicts_detected.length === 0 ? (
                      <div className="text-center py-8 text-muted-foreground">
                        <Check className="h-12 w-12 mx-auto mb-4 text-green-600" />
                        <p>No conflicts detected - safe for parallel development!</p>
                      </div>
                    ) : (
                      result.conflicts_detected.map((conflict, index) => (
                        <Card key={index}>
                          <CardHeader>
                            <div className="flex items-center justify-between">
                              <CardTitle className="text-base">{conflict.file_path}</CardTitle>
                              <Badge variant={getRiskLevelColor(conflict.risk_level)} className="flex items-center gap-1">
                                {getRiskLevelIcon(conflict.risk_level)}
                                {conflict.risk_level.toUpperCase()}
                              </Badge>
                            </div>
                          </CardHeader>
                          <CardContent>
                            <div className="space-y-2">
                              <div className="flex items-center gap-2 text-sm">
                                <GitBranch className="h-4 w-4" />
                                <span>{conflict.worktree1} vs {conflict.worktree2}</span>
                              </div>
                              <p className="text-sm text-muted-foreground">{conflict.description}</p>
                              <div className="mt-2 p-2 bg-muted rounded text-sm">
                                <strong>Resolution:</strong> {conflict.resolution_strategy}
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      ))
                    )}
                  </div>
                </ScrollArea>
              </TabsContent>

              <TabsContent value="files" className="mt-4">
                <ScrollArea className="h-[400px]">
                  <div className="space-y-2">
                    {result.modified_files.map((file, index) => (
                      <div key={index} className="flex items-center justify-between p-3 border rounded">
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4" />
                          <span className="text-sm font-mono">{file.file_path}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">{file.modification_type}</Badge>
                          <div className="text-xs text-muted-foreground">
                            {file.lines_added > 0 && <span className="text-green-600">+{file.lines_added}</span>}
                            {file.lines_removed > 0 && <span className="text-red-600">-{file.lines_removed}</span>}
                          </div>
                          <Badge variant="outline">{file.worktree_name}</Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </TabsContent>

              <TabsContent value="recommendations" className="mt-4">
                <div className="space-y-4">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Zap className="h-5 w-5" />
                        Recommendations
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {result.recommendations.map((rec, index) => (
                          <div key={index} className="flex gap-3">
                            <div className="w-6 h-6 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center shrink-0">
                              {index + 1}
                            </div>
                            <p className="text-sm">{rec}</p>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>

                  {result.high_risk_areas.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <AlertTriangle className="h-5 w-5" />
                          High Risk Areas
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2">
                          {result.high_risk_areas.map((area, index) => (
                            <div key={index} className="flex items-center gap-2 text-sm">
                              <div className="w-2 h-2 rounded-full bg-red-500"></div>
                              <span>{area}</span>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              </TabsContent>
            </Tabs>
          )}

          {/* Error */}
          {error && (
            <Card className="border-red-200 bg-red-50">
              <CardContent className="pt-6">
                <div className="flex items-center gap-2 text-red-600">
                  <AlertTriangle className="h-4 w-4" />
                  <span className="text-sm">{error}</span>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Streaming Output (for debugging) */}
          {process.env.NODE_ENV === 'development' && streamingOutput && (
            <Card className="mt-4">
              <CardHeader>
                <CardTitle className="text-sm">Debug Output</CardTitle>
              </CardHeader>
              <CardContent>
                <pre ref={streamOutputRef} className="text-xs bg-muted p-2 rounded overflow-auto max-h-32">
                  {streamingOutput}
                </pre>
              </CardContent>
            </Card>
          )}
        </div>

        <DialogFooter className="flex gap-2">
          {phase === 'idle' && (
            <>
              <Button variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button onClick={handleAnalyze} disabled={!selectedProjectId}>
                Analyze Conflicts
              </Button>
            </>
          )}

          {phase === 'analyzing' && (
            <Button variant="outline" onClick={handleClose}>
              Cancel
            </Button>
          )}

          {phase === 'complete' && result && (
            <>
              <Button variant="outline" onClick={handleCopyResults}>
                <Copy className="h-4 w-4 mr-2" />
                {copied ? 'Copied!' : 'Copy Report'}
              </Button>
              <Button onClick={handleAnalyze}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Re-analyze
              </Button>
              <Button onClick={handleClose}>
                Close
              </Button>
            </>
          )}

          {phase === 'error' && (
            <>
              <Button variant="outline" onClick={handleClose}>
                Close
              </Button>
              <Button onClick={handleRetry}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
