import { create } from 'zustand';
import type { CiPlatform, PipelineGeneratorResult, DetectedStack } from '../../main/pipeline-generator-service';

export type PipelineGeneratorPhase = 'idle' | 'generating' | 'complete' | 'error';

export const CI_PLATFORMS: CiPlatform[] = ['github', 'gitlab', 'circleci'];

export const PLATFORM_LABELS: Record<CiPlatform, string> = {
  github: 'GitHub Actions',
  gitlab: 'GitLab CI/CD',
  circleci: 'CircleCI',
};

export const PLATFORM_ICONS: Record<CiPlatform, string> = {
  github: '🐙',
  gitlab: '🦊',
  circleci: '⚙️',
};

interface PipelineGeneratorState {
  phase: PipelineGeneratorPhase;
  status: string;
  streamingOutput: string;
  result: PipelineGeneratorResult | null;
  error: string | null;
  selectedPlatforms: CiPlatform[];
  selectedPlatformView: CiPlatform | null;
  model?: string;
  thinkingLevel?: string;

  setPhase: (phase: PipelineGeneratorPhase) => void;
  setStatus: (status: string) => void;
  appendStreamingOutput: (chunk: string) => void;
  setResult: (result: PipelineGeneratorResult) => void;
  setError: (error: string) => void;
  togglePlatform: (platform: CiPlatform) => void;
  setSelectedPlatforms: (platforms: CiPlatform[]) => void;
  setSelectedPlatformView: (platform: CiPlatform | null) => void;
  setModel: (model?: string) => void;
  setThinkingLevel: (level?: string) => void;
  reset: () => void;
}

const initialState = {
  phase: 'idle' as PipelineGeneratorPhase,
  status: '',
  streamingOutput: '',
  result: null,
  error: null,
  selectedPlatforms: ['github', 'gitlab'] as CiPlatform[],
  selectedPlatformView: null,
  model: undefined,
  thinkingLevel: undefined,
};

export const usePipelineGeneratorStore = create<PipelineGeneratorState>((set) => ({
  ...initialState,

  setPhase: (phase) => set({ phase }),
  setStatus: (status) => set({ status }),
  appendStreamingOutput: (chunk) => set((s) => ({ streamingOutput: s.streamingOutput + chunk })),
  setResult: (result) => set({ result, phase: 'complete' }),
  setError: (error) => set({ error, phase: 'error' }),
  togglePlatform: (platform) =>
    set((s) => ({
      selectedPlatforms: s.selectedPlatforms.includes(platform)
        ? s.selectedPlatforms.filter((p) => p !== platform)
        : [...s.selectedPlatforms, platform],
    })),
  setSelectedPlatforms: (selectedPlatforms) => set({ selectedPlatforms }),
  setSelectedPlatformView: (selectedPlatformView) => set({ selectedPlatformView }),
  setModel: (model) => set({ model }),
  setThinkingLevel: (thinkingLevel) => set({ thinkingLevel }),
  reset: () => set(initialState),
}));

export function generatePipelines(projectDir: string): void {
  const store = usePipelineGeneratorStore.getState();
  store.setPhase('generating');
  usePipelineGeneratorStore.setState({ streamingOutput: '', error: null, result: null });

  window.electronAPI.generatePipelines({
    projectDir,
    platforms: store.selectedPlatforms,
    model: store.model,
    thinkingLevel: store.thinkingLevel,
  });
}

export function cancelPipelineGeneration(): void {
  window.electronAPI.cancelPipelineGeneration();
  usePipelineGeneratorStore.getState().setPhase('idle');
}

export function setupPipelineGeneratorListeners(): () => void {
  const store = () => usePipelineGeneratorStore.getState();

  const unsubChunk = window.electronAPI.onPipelineGeneratorStreamChunk((chunk: string) => {
    store().appendStreamingOutput(chunk);
  });

  const unsubStatus = window.electronAPI.onPipelineGeneratorStatus((status: string) => {
    store().setStatus(status);
  });

  const unsubError = window.electronAPI.onPipelineGeneratorError((error: string) => {
    store().setError(error);
  });

  const unsubComplete = window.electronAPI.onPipelineGeneratorComplete((result: PipelineGeneratorResult) => {
    store().setResult(result);
    const firstPlatform = result.platforms_generated?.[0] as CiPlatform | undefined;
    if (firstPlatform) store().setSelectedPlatformView(firstPlatform);
  });

  return () => {
    unsubChunk();
    unsubStatus();
    unsubError();
    unsubComplete();
  };
}
