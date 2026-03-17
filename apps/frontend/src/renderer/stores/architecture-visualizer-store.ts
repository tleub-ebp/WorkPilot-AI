import { create } from 'zustand';
import type { ArchitectureVisualizerResult } from '../../main/architecture-visualizer-service';

export type ArchitectureVisualizerPhase = 'idle' | 'generating' | 'complete' | 'error';

export const DIAGRAM_TYPES = [
  'module_dependencies',
  'component_hierarchy',
  'data_flow',
  'database_schema',
] as const;

export type DiagramType = typeof DIAGRAM_TYPES[number];

interface ArchitectureVisualizerState {
  phase: ArchitectureVisualizerPhase;
  status: string;
  streamingOutput: string;
  result: ArchitectureVisualizerResult | null;
  error: string | null;
  isOpen: boolean;
  selectedDiagramTypes: DiagramType[];
  selectedDiagramView: DiagramType | null;
  model?: string;
  thinkingLevel?: string;

  openDashboard: () => void;
  closeDashboard: () => void;
  setPhase: (phase: ArchitectureVisualizerPhase) => void;
  setStatus: (status: string) => void;
  appendStreamingOutput: (chunk: string) => void;
  setResult: (result: ArchitectureVisualizerResult) => void;
  setError: (error: string) => void;
  setSelectedDiagramTypes: (types: DiagramType[]) => void;
  toggleDiagramType: (type: DiagramType) => void;
  setSelectedDiagramView: (type: DiagramType | null) => void;
  setModel: (model?: string) => void;
  setThinkingLevel: (level?: string) => void;
  reset: () => void;
}

const initialState = {
  phase: 'idle' as ArchitectureVisualizerPhase,
  status: '',
  streamingOutput: '',
  result: null,
  error: null,
  isOpen: false,
  selectedDiagramTypes: [...DIAGRAM_TYPES] as DiagramType[],
  selectedDiagramView: null,
  model: undefined,
  thinkingLevel: undefined,
};

export const useArchitectureVisualizerStore = create<ArchitectureVisualizerState>((set) => ({
  ...initialState,

  openDashboard: () => set({ isOpen: true }),
  closeDashboard: () => set({ isOpen: false, phase: 'idle', status: '', streamingOutput: '', result: null, error: null }),
  setPhase: (phase) => set({ phase }),
  setStatus: (status) => set({ status }),
  appendStreamingOutput: (chunk) => set((s) => ({ streamingOutput: s.streamingOutput + chunk })),
  setResult: (result) => set({ result, phase: 'complete' }),
  setError: (error) => set({ error, phase: 'error' }),
  setSelectedDiagramTypes: (selectedDiagramTypes) => set({ selectedDiagramTypes }),
  toggleDiagramType: (type) => set((s) => ({
    selectedDiagramTypes: s.selectedDiagramTypes.includes(type)
      ? s.selectedDiagramTypes.filter((t) => t !== type)
      : [...s.selectedDiagramTypes, type],
  })),
  setSelectedDiagramView: (selectedDiagramView) => set({ selectedDiagramView }),
  setModel: (model) => set({ model }),
  setThinkingLevel: (thinkingLevel) => set({ thinkingLevel }),
  reset: () => set(initialState),
}));

export function generateArchitectureDiagrams(projectDir: string): void {
  const store = useArchitectureVisualizerStore.getState();
  store.setPhase('generating');
  useArchitectureVisualizerStore.setState({ streamingOutput: '', error: null, result: null });

  window.electronAPI.generateArchitectureDiagrams({
    projectDir,
    diagramTypes: store.selectedDiagramTypes,
    model: store.model,
    thinkingLevel: store.thinkingLevel,
  });
}

export function cancelArchitectureVisualization(): void {
  window.electronAPI.cancelArchitectureVisualization();
  useArchitectureVisualizerStore.getState().setPhase('idle');
}

export function setupArchitectureVisualizerListeners(): () => void {
  const store = () => useArchitectureVisualizerStore.getState();

  const unsubChunk = window.electronAPI.onArchitectureVisualizerStreamChunk((chunk: string) => {
    store().appendStreamingOutput(chunk);
  });

  const unsubStatus = window.electronAPI.onArchitectureVisualizerStatus((status: string) => {
    store().setStatus(status);
    if (status.includes('complete') || status.includes('Analysis')) {
      store().setPhase('generating');
    }
  });

  const unsubError = window.electronAPI.onArchitectureVisualizerError((error: string) => {
    store().setError(error);
  });

  const unsubComplete = window.electronAPI.onArchitectureVisualizerComplete((result: ArchitectureVisualizerResult) => {
    store().setResult(result);
    // Default to first available diagram type
    const firstType = result.diagram_types_analyzed?.[0] as DiagramType | undefined;
    if (firstType) store().setSelectedDiagramView(firstType);
  });

  return () => {
    unsubChunk();
    unsubStatus();
    unsubError();
    unsubComplete();
  };
}
