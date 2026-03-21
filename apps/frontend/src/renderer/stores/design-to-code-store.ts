import { create } from 'zustand';

/**
 * Component spec from design analysis
 */
export interface ComponentSpec {
  name: string;
  type: string;
  description: string;
  children: { name: string; type: string }[];
}

/**
 * Design specification from vision analysis
 */
export interface DesignSpec {
  components: ComponentSpec[];
  color_palette: Record<string, string>;
  typography: Record<string, Record<string, string>>;
}

/**
 * Generated file from the pipeline
 */
export interface GeneratedFile {
  path: string;
  content: string;
  language: string;
  description: string;
}

/**
 * Visual test generated for a component
 */
export interface VisualTest {
  name: string;
  test_code: string;
  threshold: number;
  description: string;
}

/**
 * Design token from the project's design system
 */
export interface DesignTokenUsed {
  name: string;
  value: string;
  category: string;
}

/**
 * Pipeline result
 */
export interface DesignToCodeResult {
  success: boolean;
  phase: string;
  design_spec: DesignSpec | null;
  generated_files: GeneratedFile[];
  visual_tests: VisualTest[];
  design_tokens_used: DesignTokenUsed[];
  figma_sync_status: Record<string, unknown> | null;
  errors: string[];
  warnings: string[];
  duration_seconds: number;
  tokens_used: number;
}

export type PipelinePhase =
  | 'idle'
  | 'analyzing'
  | 'spec_generation'
  | 'code_generation'
  | 'design_token_integration'
  | 'visual_test_generation'
  | 'figma_sync'
  | 'complete'
  | 'error';

export type FrameworkType = 'react' | 'vue' | 'angular' | 'svelte' | 'nextjs' | 'nuxt';

export type DesignSourceType = 'screenshot' | 'figma' | 'wireframe' | 'whiteboard' | 'photo';

interface DesignToCodeState {
  // Pipeline state
  phase: PipelinePhase;
  status: string;
  result: DesignToCodeResult | null;
  error: string | null;

  // Configuration
  framework: FrameworkType;
  sourceType: DesignSourceType;
  designSystemPath: string;
  figmaUrl: string;
  generateTests: boolean;
  customInstructions: string;

  // Image state
  imageData: string | null;
  imagePreview: string | null;
  imageName: string | null;

  // Selected file for preview
  selectedFileIndex: number;
  activeTab: 'upload' | 'spec' | 'code' | 'tests' | 'tokens';
}

interface DesignToCodeActions {
  // Configuration
  setFramework: (framework: FrameworkType) => void;
  setSourceType: (sourceType: DesignSourceType) => void;
  setDesignSystemPath: (path: string) => void;
  setFigmaUrl: (url: string) => void;
  setGenerateTests: (generate: boolean) => void;
  setCustomInstructions: (instructions: string) => void;

  // Image
  setImageData: (data: string | null, preview: string | null, name: string | null) => void;
  clearImage: () => void;

  // Pipeline
  startPipeline: () => void;
  updatePhase: (phase: PipelinePhase, status: string) => void;
  setPipelineResult: (result: DesignToCodeResult) => void;
  setPipelineError: (error: string) => void;
  resetPipeline: () => void;

  // UI
  setSelectedFileIndex: (index: number) => void;
  setActiveTab: (tab: 'upload' | 'spec' | 'code' | 'tests' | 'tokens') => void;
}

const initialState: DesignToCodeState = {
  phase: 'idle',
  status: '',
  result: null,
  error: null,
  framework: 'react',
  sourceType: 'screenshot',
  designSystemPath: '',
  figmaUrl: '',
  generateTests: true,
  customInstructions: '',
  imageData: null,
  imagePreview: null,
  imageName: null,
  selectedFileIndex: 0,
  activeTab: 'upload',
};

export const useDesignToCodeStore = create<DesignToCodeState & DesignToCodeActions>((set) => ({
  ...initialState,

  // Configuration
  setFramework: (framework) => set({ framework }),
  setSourceType: (sourceType) => set({ sourceType }),
  setDesignSystemPath: (path) => set({ designSystemPath: path }),
  setFigmaUrl: (url) => set({ figmaUrl: url }),
  setGenerateTests: (generate) => set({ generateTests: generate }),
  setCustomInstructions: (instructions) => set({ customInstructions: instructions }),

  // Image
  setImageData: (data, preview, name) =>
    set({ imageData: data, imagePreview: preview, imageName: name }),
  clearImage: () => set({ imageData: null, imagePreview: null, imageName: null }),

  // Pipeline
  startPipeline: () =>
    set({
      phase: 'analyzing',
      status: 'Starting pipeline...',
      error: null,
      result: null,
      activeTab: 'spec',
    }),
  updatePhase: (phase, status) => set({ phase, status }),
  setPipelineResult: (result) =>
    set({
      result,
      phase: result.success ? 'complete' : 'error',
      status: result.success ? 'Pipeline complete!' : 'Pipeline failed',
      error: result.errors.length > 0 ? result.errors.join('; ') : null,
      activeTab: result.success ? 'code' : 'upload',
    }),
  setPipelineError: (error) =>
    set({
      phase: 'error',
      status: 'Pipeline failed',
      error,
    }),
  resetPipeline: () =>
    set({
      phase: 'idle',
      status: '',
      result: null,
      error: null,
      selectedFileIndex: 0,
      activeTab: 'upload',
    }),

  // UI
  setSelectedFileIndex: (index) => set({ selectedFileIndex: index }),
  setActiveTab: (tab) => set({ activeTab: tab }),
}));

/**
 * Run the design-to-code pipeline via IPC
 */
export async function runDesignToCodePipeline(): Promise<void> {
  const state = useDesignToCodeStore.getState();

  if (!state.imageData && !state.figmaUrl) {
    state.setPipelineError('Please provide an image or Figma URL.');
    return;
  }

  state.startPipeline();

  try {
    // Call the backend via IPC (Electron)
    const result = await globalThis.electronAPI.runDesignToCodePipeline({
      imageData: state.imageData || '',
      framework: state.framework,
      sourceType: state.sourceType,
      designSystemPath: state.designSystemPath,
      figmaUrl: state.figmaUrl,
      generateTests: state.generateTests,
      customInstructions: state.customInstructions,
    });

    state.setPipelineResult(result as DesignToCodeResult);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    state.setPipelineError(message);
  }
}
