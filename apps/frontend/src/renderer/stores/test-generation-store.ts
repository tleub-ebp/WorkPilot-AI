import { create } from 'zustand';
import { useProjectStore } from './project-store';

/**
 * Function information from coverage analysis
 */
export interface FunctionInfo {
  name: string;
  module: string;
  class_name: string | null;
  args: string[];
  return_type: string | null;
  docstring: string;
  line_number: number;
  is_async: boolean;
  decorators: string[];
  complexity: number;
  full_name: string;
  is_private: boolean;
  is_dunder: boolean;
}

/**
 * Coverage gap information
 */
export interface CoverageGap {
  function: FunctionInfo;
  priority: 'high' | 'medium' | 'low';
  reason: string;
  suggested_test_count: number;
}

/**
 * Generated test information
 */
export interface GeneratedTest {
  test_name: string;
  test_code: string;
  target_function: string;
  test_type: 'unit' | 'integration' | 'e2e';
  description: string;
  imports: string[];
  fixtures: string[];
}

/**
 * Test generation result
 */
export interface TestGenerationResult {
  source_file: string;
  functions_analyzed: number;
  tests_generated: number;
  coverage_gaps: CoverageGap[];
  generated_tests: GeneratedTest[];
  test_file_content: string;
  test_file_path: string;
}

/**
 * Post-build generation result
 */
export interface PostBuildResult {
  source_file: string;
  tests_generated: number;
  test_file_path: string;
  test_file_content: string;
}

export type TestGenerationPhase = 'idle' | 'analyzing' | 'generating' | 'complete' | 'error';

interface TestGenerationState {
  // State
  phase: TestGenerationPhase;
  status: string;
  result: TestGenerationResult | null;
  postBuildResults: PostBuildResult[] | null;
  error: string | null;
  isOpen: boolean;
  selectedFile: string;
  existingTestPath: string | null;
  coverageTarget: number;
  tddLanguage: string;
  tddSnippetType: string;

  // Actions
  openDialog: (filePath: string, existingTestPath?: string) => void;
  closeDialog: () => void;
  setPhase: (phase: TestGenerationPhase) => void;
  setStatus: (status: string) => void;
  setResult: (result: TestGenerationResult) => void;
  setPostBuildResults: (postBuildResults: PostBuildResult[]) => void;
  setError: (error: string) => void;
  setCoverageTarget: (target: number) => void;
  setTddLanguage: (language: string) => void;
  setTddSnippetType: (snippetType: string) => void;
  setSelectedFile: (filePath: string) => void;
  reset: () => void;

  // API Actions
  analyzeCoverage: (filePath: string, existingTestPath?: string) => Promise<CoverageGap[]>;
  generateUnitTests: (filePath: string, existingTestPath?: string, coverageTarget?: number) => Promise<TestGenerationResult>;
  generateE2ETests: (userStory: string, targetModule: string) => Promise<TestGenerationResult>;
  generateTDDTests: (spec: { description: string; language: string; snippet_type: string }) => Promise<TestGenerationResult>;
  runPostBuildGeneration: (projectPath: string, modifiedFiles: string[]) => Promise<PostBuildResult[]>;
}

const initialState = {
  phase: 'idle' as TestGenerationPhase,
  status: '',
  result: null,
  postBuildResults: null,
  error: null,
  isOpen: false,
  selectedFile: '',
  existingTestPath: null,
  coverageTarget: 80,
  tddLanguage: 'typescript',
  tddSnippetType: 'function',
};

export const useTestGenerationStore = create<TestGenerationState>((set, get) => ({
  ...initialState,

  openDialog: (filePath: string, existingTestPath?: string) => {
    set({
      isOpen: true,
      selectedFile: filePath,
      existingTestPath: existingTestPath || null,
      phase: 'idle',
      status: '',
      result: null,
      error: null,
    });
  },

  closeDialog: () => {
    set({
      isOpen: false,
      phase: 'idle',
      status: '',
      result: null,
      error: null,
    });
  },

  setPhase: (phase: TestGenerationPhase) => set({ phase }),
  setStatus: (status: string) => set({ status }),
  setResult: (result: TestGenerationResult) => set({ result }),
  setPostBuildResults: (postBuildResults: PostBuildResult[]) => set({ postBuildResults }),
  setError: (error: string) => set({ error }),
  setCoverageTarget: (coverageTarget: number) => set({ coverageTarget }),
  setTddLanguage: (tddLanguage: string) => set({ tddLanguage }),
  setTddSnippetType: (tddSnippetType: string) => set({ tddSnippetType }),
  setSelectedFile: (filePath: string) => set({ selectedFile: filePath }),

  reset: () => set(initialState),

  analyzeCoverage: async (filePath: string, existingTestPath?: string) => {
    const { setPhase, setStatus, setError } = get();
    setPhase('analyzing');
    setStatus('Analyzing test coverage...');

    return new Promise<CoverageGap[]>((resolve, reject) => {
      const onResult = (data: any) => {
        window.electronAPI.removeTestGenerationResultListener(onResult);
        window.electronAPI.removeTestGenerationErrorListener(onError);
        setPhase('complete');
        setStatus('Coverage analysis complete');
        resolve((data as { gaps?: CoverageGap[] }).gaps || []);
      };
      const onError = (error: string) => {
        window.electronAPI.removeTestGenerationResultListener(onResult);
        window.electronAPI.removeTestGenerationErrorListener(onError);
        setPhase('error');
        setError(error);
        reject(new Error(error));
      };
      const projectPath = useProjectStore.getState().getActiveProject()?.path;
      window.electronAPI.onTestGenerationStatus((status: string) => setStatus(status));
      window.electronAPI.onTestGenerationResult(onResult);
      window.electronAPI.onTestGenerationError(onError);
      window.electronAPI.analyzeTestCoverage(filePath, existingTestPath, projectPath);
    });
  },

  generateUnitTests: async (filePath: string, existingTestPath?: string, coverageTarget?: number) => {
    const { setPhase, setStatus, setError, setResult } = get();
    setPhase('generating');
    setStatus('Generating unit tests...');

    return new Promise<TestGenerationResult>((resolve, reject) => {
      const onComplete = (data: any) => {
        window.electronAPI.removeTestGenerationCompleteListener(onComplete);
        window.electronAPI.removeTestGenerationErrorListener(onError);
        const parsed = data as { result?: TestGenerationResult };
        const result = parsed.result as TestGenerationResult;
        setPhase('complete');
        setStatus('Unit tests generated successfully');
        setResult(result);
        resolve(result);
      };
      const onError = (error: string) => {
        window.electronAPI.removeTestGenerationCompleteListener(onComplete);
        window.electronAPI.removeTestGenerationErrorListener(onError);
        setPhase('error');
        setError(error);
        reject(new Error(error));
      };
      const projectPath = useProjectStore.getState().getActiveProject()?.path;
      window.electronAPI.onTestGenerationStatus((status: string) => setStatus(status));
      window.electronAPI.onTestGenerationComplete(onComplete);
      window.electronAPI.onTestGenerationError(onError);
      window.electronAPI.generateUnitTests(filePath, existingTestPath, coverageTarget, projectPath);
    });
  },

  generateE2ETests: async (userStory: string, targetModule: string) => {
    const { setPhase, setStatus, setError, setResult } = get();
    setPhase('generating');
    setStatus('Generating E2E tests...');

    return new Promise<TestGenerationResult>((resolve, reject) => {
      const onComplete = (data: any) => {
        window.electronAPI.removeTestGenerationCompleteListener(onComplete);
        window.electronAPI.removeTestGenerationErrorListener(onError);
        const parsed = data as { result?: TestGenerationResult };
        const result = parsed.result as TestGenerationResult;
        setPhase('complete');
        setStatus('E2E tests generated successfully');
        setResult(result);
        resolve(result);
      };
      const onError = (error: string) => {
        window.electronAPI.removeTestGenerationCompleteListener(onComplete);
        window.electronAPI.removeTestGenerationErrorListener(onError);
        setPhase('error');
        setError(error);
        reject(new Error(error));
      };
      const projectPath = useProjectStore.getState().getActiveProject()?.path;
      window.electronAPI.onTestGenerationStatus((status: string) => setStatus(status));
      window.electronAPI.onTestGenerationComplete(onComplete);
      window.electronAPI.onTestGenerationError(onError);
      window.electronAPI.generateE2ETests(userStory, targetModule, projectPath);
    });
  },

  generateTDDTests: async (spec: { description: string; language: string; snippet_type: string }) => {
    const { setPhase, setStatus, setError, setResult } = get();
    setPhase('generating');
    setStatus('Generating TDD tests...');

    return new Promise<TestGenerationResult>((resolve, reject) => {
      const onComplete = (data: any) => {
        window.electronAPI.removeTestGenerationCompleteListener(onComplete);
        window.electronAPI.removeTestGenerationErrorListener(onError);
        const parsed = data as { result?: TestGenerationResult };
        const result = parsed.result as TestGenerationResult;
        setPhase('complete');
        setStatus('TDD tests generated successfully');
        setResult(result);
        resolve(result);
      };
      const onError = (error: string) => {
        window.electronAPI.removeTestGenerationCompleteListener(onComplete);
        window.electronAPI.removeTestGenerationErrorListener(onError);
        setPhase('error');
        setError(error);
        reject(new Error(error));
      };
      const projectPath = useProjectStore.getState().getActiveProject()?.path;
      window.electronAPI.onTestGenerationStatus((status: string) => setStatus(status));
      window.electronAPI.onTestGenerationComplete(onComplete);
      window.electronAPI.onTestGenerationError(onError);
      window.electronAPI.generateTDDTests(spec.description, spec.language, spec.snippet_type, projectPath);
    });
  },

  runPostBuildGeneration: async (projectPath: string, modifiedFiles: string[]) => {
    const { setPhase, setStatus, setError, setPostBuildResults } = get();

    try {
      setPhase('generating');
      setStatus('Running post-build test generation...');

      // Post-build generation is not yet wired via IPC — placeholder for future implementation
      throw new Error(`Post-build generation for ${projectPath} with ${modifiedFiles.length} file(s) is not yet implemented via IPC`);
    } catch (error) {
      setPhase('error');
      setError(error instanceof Error ? error.message : 'Unknown error');
      throw error;
    }
  },
}));

// Helper function to open dialog
export const openTestGenerationDialog = () => {
  const store = useTestGenerationStore.getState();
  store.reset();
  store.openDialog('', '');
};
