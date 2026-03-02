import { create } from 'zustand';

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
  maxTestsPerFunction: number;

  // Actions
  openDialog: (filePath: string, existingTestPath?: string) => void;
  closeDialog: () => void;
  setPhase: (phase: TestGenerationPhase) => void;
  setStatus: (status: string) => void;
  setResult: (result: TestGenerationResult) => void;
  setPostBuildResults: (postBuildResults: PostBuildResult[]) => void;
  setError: (error: string) => void;
  setMaxTestsPerFunction: (max: number) => void;
  reset: () => void;

  // API Actions
  analyzeCoverage: (filePath: string, existingTestPath?: string) => Promise<CoverageGap[]>;
  generateUnitTests: (filePath: string, existingTestPath?: string, maxTestsPerFunction?: number) => Promise<TestGenerationResult>;
  generateE2ETests: (userStory: string, targetModule: string) => Promise<TestGenerationResult>;
  generateTDDTests: (spec: any) => Promise<TestGenerationResult>;
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
  maxTestsPerFunction: 3,
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
  setMaxTestsPerFunction: (maxTestsPerFunction: number) => set({ maxTestsPerFunction }),

  reset: () => set(initialState),

  analyzeCoverage: async (filePath: string, existingTestPath?: string) => {
    const { setPhase, setStatus, setError } = get();
    
    try {
      setPhase('analyzing');
      setStatus('Analyzing test coverage...');

      const response = await fetch('http://localhost:9000/api/test-generation/analyze-coverage', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          file_path: filePath,
          existing_test_path: existingTestPath,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to analyze coverage');
      }

      setPhase('complete');
      setStatus('Coverage analysis complete');
      return data.gaps;
    } catch (error) {
      setPhase('error');
      setError(error instanceof Error ? error.message : 'Unknown error');
      throw error;
    }
  },

  generateUnitTests: async (filePath: string, existingTestPath?: string, maxTestsPerFunction?: number) => {
    const { setPhase, setStatus, setError, setResult } = get();
    
    try {
      setPhase('generating');
      setStatus('Generating unit tests...');

      const response = await fetch('http://localhost:9000/api/test-generation/generate-unit-tests', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          file_path: filePath,
          existing_test_path: existingTestPath,
          max_tests_per_function: maxTestsPerFunction || 3,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to generate tests');
      }

      setPhase('complete');
      setStatus('Unit tests generated successfully');
      setResult(data.result);
      return data.result;
    } catch (error) {
      setPhase('error');
      setError(error instanceof Error ? error.message : 'Unknown error');
      throw error;
    }
  },

  generateE2ETests: async (userStory: string, targetModule: string) => {
    const { setPhase, setStatus, setError, setResult } = get();
    
    try {
      setPhase('generating');
      setStatus('Generating E2E tests...');

      const response = await fetch('http://localhost:9000/api/test-generation/generate-e2e-tests', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_story: userStory,
          target_module: targetModule,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to generate E2E tests');
      }

      setPhase('complete');
      setStatus('E2E tests generated successfully');
      setResult(data.result);
      return data.result;
    } catch (error) {
      setPhase('error');
      setError(error instanceof Error ? error.message : 'Unknown error');
      throw error;
    }
  },

  generateTDDTests: async (spec: any) => {
    const { setPhase, setStatus, setError, setResult } = get();
    
    try {
      setPhase('generating');
      setStatus('Generating TDD tests...');

      const response = await fetch('http://localhost:9000/api/test-generation/generate-tdd-tests', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(spec),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to generate TDD tests');
      }

      setPhase('complete');
      setStatus('TDD tests generated successfully');
      setResult(data.result);
      return data.result;
    } catch (error) {
      setPhase('error');
      setError(error instanceof Error ? error.message : 'Unknown error');
      throw error;
    }
  },

  runPostBuildGeneration: async (projectPath: string, modifiedFiles: string[]) => {
    const { setPhase, setStatus, setError, setPostBuildResults } = get();
    
    try {
      setPhase('generating');
      setStatus('Running post-build test generation...');

      const response = await fetch('http://localhost:9000/api/test-generation/run-post-build', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          project_path: projectPath,
          modified_files: modifiedFiles,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to run post-build generation');
      }

      setPhase('complete');
      setStatus('Post-build test generation complete');
      setPostBuildResults(data.results);
      return data.results;
    } catch (error) {
      setPhase('error');
      setError(error instanceof Error ? error.message : 'Unknown error');
      throw error;
    }
  },
}));

// Helper function to open dialog
export const openTestGenerationDialog = () => {
  useTestGenerationStore.getState().reset();
  // This would be handled by the component that opens the dialog
};
