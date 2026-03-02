import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Check, Copy, Loader2, FlaskConical, FileText, Play, RotateCcw, X, Search, Zap } from 'lucide-react';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Badge } from '../ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { ScrollArea } from '../ui/scroll-area';

import {
  useTestGenerationStore,
  type TestGenerationResult,
  type CoverageGap,
  type GeneratedTest,
  type PostBuildResult,
} from '../../stores/test-generation-store';
import { useProjectStore } from '../../stores/project-store';

const TEST_TYPES = ['unit', 'e2e', 'tdd'] as const;
const PRIORITY_COLORS = {
  high: 'bg-red-100 text-red-800',
  medium: 'bg-yellow-100 text-yellow-800',
  low: 'bg-green-100 text-green-800',
};

/**
 * TestGenerationDialog — AI-powered test generation dialog.
 *
 * Shows a dialog where users can analyze coverage gaps and generate
 * comprehensive test suites for their code.
 *
 * Usage:
 *   const { openDialog, closeDialog, isOpen } = useTestGenerationStore();
 *   <TestGenerationDialog />
 */
interface TestGenerationDialogProps {
  /** Called when tests are generated and should be applied */
  onApplyTests?: (testFileContent: string, testFilePath: string) => void;
}

export function TestGenerationDialog({ onApplyTests }: TestGenerationDialogProps) {
  const { t } = useTranslation(['testGeneration', 'common']);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState('analyze');
  const [userStory, setUserStory] = useState('');
  const [targetModule, setTargetModule] = useState('');
  const [tddSpec, setTddSpec] = useState('');

  const {
    isOpen,
    closeDialog,
    phase,
    status,
    result,
    postBuildResults,
    error,
    selectedFile,
    existingTestPath,
    maxTestsPerFunction,
    setMaxTestsPerFunction,
    reset,
    analyzeCoverage,
    generateUnitTests,
    generateE2ETests,
    generateTDDTests,
    runPostBuildGeneration,
  } = useTestGenerationStore();

  const selectedProjectId = useProjectStore((s) => s.selectedProjectId);

  // Reset state when dialog closes
  useEffect(() => {
    if (!isOpen) {
      reset();
      setActiveTab('analyze');
      setUserStory('');
      setTargetModule('');
      setTddSpec('');
      setCopied(false);
    }
  }, [isOpen, reset]);

  const handleAnalyzeCoverage = useCallback(async () => {
    if (!selectedFile) return;
    await analyzeCoverage(selectedFile, existingTestPath || undefined);
  }, [selectedFile, existingTestPath, analyzeCoverage]);

  const handleGenerateUnitTests = useCallback(async () => {
    if (!selectedFile) return;
    await generateUnitTests(selectedFile, existingTestPath || undefined, maxTestsPerFunction);
  }, [selectedFile, existingTestPath, maxTestsPerFunction, generateUnitTests]);

  const handleGenerateE2ETests = useCallback(async () => {
    if (!userStory.trim() || !targetModule.trim()) return;
    await generateE2ETests(userStory, targetModule);
  }, [userStory, targetModule, generateE2ETests]);

  const handleGenerateTDDTests = useCallback(async () => {
    if (!tddSpec.trim()) return;
    try {
      const spec = JSON.parse(tddSpec);
      await generateTDDTests(spec);
    } catch (e) {
      console.error('Invalid TDD spec JSON:', e);
    }
  }, [tddSpec, generateTDDTests]);

  const handleCopyToClipboard = useCallback((content: string) => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, []);

  const handleApplyTests = useCallback(() => {
    if (result && onApplyTests) {
      onApplyTests(result.test_file_content, result.test_file_path);
      closeDialog();
    }
  }, [result, onApplyTests, closeDialog]);

  const renderCoverageGaps = (gaps: CoverageGap[]) => (
    <div className="space-y-3">
      {gaps.map((gap, index) => (
        <Card key={index}>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-mono text-sm">{gap.function.full_name}</h4>
              <Badge className={PRIORITY_COLORS[gap.priority]}>
                {gap.priority} priority
              </Badge>
            </div>
            <p className="text-sm text-gray-600 mb-2">{gap.reason}</p>
            <div className="text-xs text-gray-500">
              Line: {gap.function.line_number} | Complexity: {gap.function.complexity} | 
              Tests needed: {gap.suggested_test_count}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );

  const renderGeneratedTests = (tests: GeneratedTest[]) => (
    <div className="space-y-4">
      {tests.map((test, index) => (
        <Card key={index}>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-mono">{test.test_name}</CardTitle>
              <Badge variant="outline">{test.test_type}</Badge>
            </div>
            <CardDescription>{test.description}</CardDescription>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-32 w-full">
              <pre className="text-xs bg-gray-50 p-2 rounded">{test.test_code}</pre>
            </ScrollArea>
          </CardContent>
        </Card>
      ))}
    </div>
  );

  const renderPostBuildResults = (results: PostBuildResult[]) => (
    <div className="space-y-3">
      {results.map((result, index) => (
        <Card key={index}>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-mono text-sm">{result.source_file}</h4>
              <Badge variant="outline">{result.tests_generated} tests</Badge>
            </div>
            <p className="text-xs text-gray-500 mb-2">{result.test_file_path}</p>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleCopyToClipboard(result.test_file_content)}
              >
                {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                Copy
              </Button>
              {onApplyTests && (
                <Button
                  size="sm"
                  onClick={() => onApplyTests(result.test_file_content, result.test_file_path)}
                >
                  Apply
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );

  return (
    <Dialog open={isOpen} onOpenChange={closeDialog}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FlaskConical className="w-5 h-5" />
            Test Generation Agent
          </DialogTitle>
          <DialogDescription>
            Analyze coverage gaps and generate comprehensive test suites for your code.
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="analyze">Analyze</TabsTrigger>
            <TabsTrigger value="unit">Unit Tests</TabsTrigger>
            <TabsTrigger value="e2e">E2E Tests</TabsTrigger>
            <TabsTrigger value="tdd">TDD Mode</TabsTrigger>
          </TabsList>

          <TabsContent value="analyze" className="space-y-4">
            <div className="space-y-4">
              <div>
                <Label htmlFor="file-path">Source File</Label>
                <Input
                  id="file-path"
                  value={selectedFile}
                  readOnly
                  placeholder="Select a file to analyze"
                />
              </div>

              {existingTestPath && (
                <div>
                  <Label htmlFor="existing-test">Existing Test File</Label>
                  <Input
                    id="existing-test"
                    value={existingTestPath}
                    readOnly
                  />
                </div>
              )}

              <div className="flex gap-2">
                <Button
                  onClick={handleAnalyzeCoverage}
                  disabled={phase === 'analyzing' || !selectedFile}
                >
                  {phase === 'analyzing' ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Search className="w-4 h-4 mr-2" />
                  )}
                  Analyze Coverage
                </Button>
                <Button
                  onClick={handleGenerateUnitTests}
                  disabled={phase === 'generating' || !selectedFile}
                  variant="outline"
                >
                  {phase === 'generating' ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Zap className="w-4 h-4 mr-2" />
                  )}
                  Generate Tests
                </Button>
              </div>

              {status && (
                <div className="text-sm text-gray-600">
                  {phase === 'analyzing' && <Loader2 className="w-3 h-3 inline mr-2 animate-spin" />}
                  {phase === 'generating' && <Loader2 className="w-3 h-3 inline mr-2 animate-spin" />}
                  {status}
                </div>
              )}

              {error && (
                <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
                  {error}
                </div>
              )}

              {result && result.coverage_gaps.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-3">Coverage Gaps Found</h3>
                  {renderCoverageGaps(result.coverage_gaps)}
                </div>
              )}

              {result && result.generated_tests.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-3">Generated Tests</h3>
                  {renderGeneratedTests(result.generated_tests)}
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="unit" className="space-y-4">
            <div className="space-y-4">
              <div>
                <Label htmlFor="unit-file">Source File</Label>
                <Input
                  id="unit-file"
                  value={selectedFile}
                  readOnly
                  placeholder="Select a file for unit test generation"
                />
              </div>

              <div>
                <Label htmlFor="max-tests">Max Tests per Function</Label>
                <Input
                  id="max-tests"
                  type="number"
                  min="1"
                  max="10"
                  value={maxTestsPerFunction}
                  onChange={(e) => setMaxTestsPerFunction(parseInt(e.target.value) || 3)}
                />
              </div>

              <Button
                onClick={handleGenerateUnitTests}
                disabled={phase === 'generating' || !selectedFile}
                className="w-full"
              >
                {phase === 'generating' ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Play className="w-4 h-4 mr-2" />
                )}
                Generate Unit Tests
              </Button>

              {result && result.generated_tests.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-lg font-semibold">Generated Unit Tests</h3>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleCopyToClipboard(result.test_file_content)}
                      >
                        {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                        Copy All
                      </Button>
                      {onApplyTests && (
                        <Button size="sm" onClick={handleApplyTests}>
                          Apply Tests
                        </Button>
                      )}
                    </div>
                  </div>
                  {renderGeneratedTests(result.generated_tests)}
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="e2e" className="space-y-4">
            <div className="space-y-4">
              <div>
                <Label htmlFor="user-story">User Story</Label>
                <Textarea
                  id="user-story"
                  value={userStory}
                  onChange={(e) => setUserStory(e.target.value)}
                  placeholder="Describe the user story or scenario..."
                  rows={4}
                />
              </div>

              <div>
                <Label htmlFor="target-module">Target Module</Label>
                <Input
                  id="target-module"
                  value={targetModule}
                  onChange={(e) => setTargetModule(e.target.value)}
                  placeholder="e.g., src/auth/login.py"
                />
              </div>

              <Button
                onClick={handleGenerateE2ETests}
                disabled={phase === 'generating' || !userStory.trim() || !targetModule.trim()}
                className="w-full"
              >
                {phase === 'generating' ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Play className="w-4 h-4 mr-2" />
                )}
                Generate E2E Tests
              </Button>

              {result && result.generated_tests.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-lg font-semibold">Generated E2E Tests</h3>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleCopyToClipboard(result.test_file_content)}
                      >
                        {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                        Copy All
                      </Button>
                      {onApplyTests && (
                        <Button size="sm" onClick={handleApplyTests}>
                          Apply Tests
                        </Button>
                      )}
                    </div>
                  </div>
                  {renderGeneratedTests(result.generated_tests)}
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="tdd" className="space-y-4">
            <div className="space-y-4">
              <div>
                <Label htmlFor="tdd-spec">Function Specification (JSON)</Label>
                <Textarea
                  id="tdd-spec"
                  value={tddSpec}
                  onChange={(e) => setTddSpec(e.target.value)}
                  placeholder={`{
  "name": "calculate_total",
  "args": ["items", "tax_rate"],
  "returns": "float",
  "description": "Calculate total with tax",
  "edge_cases": ["empty_items", "invalid_tax_rate"]
}`}
                  rows={8}
                />
              </div>

              <Button
                onClick={handleGenerateTDDTests}
                disabled={phase === 'generating' || !tddSpec.trim()}
                className="w-full"
              >
                {phase === 'generating' ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Play className="w-4 h-4 mr-2" />
                )}
                Generate TDD Tests
              </Button>

              {result && result.generated_tests.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-lg font-semibold">Generated TDD Tests</h3>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleCopyToClipboard(result.test_file_content)}
                      >
                        {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                        Copy All
                      </Button>
                      {onApplyTests && (
                        <Button size="sm" onClick={handleApplyTests}>
                          Apply Tests
                        </Button>
                      )}
                    </div>
                  </div>
                  {renderGeneratedTests(result.generated_tests)}
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>

        <DialogFooter>
          <Button variant="outline" onClick={closeDialog}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
