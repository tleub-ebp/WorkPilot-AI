import { create } from 'zustand';

type ActiveMode = 'design-import' | 'canvas';

interface VisualToCodeState {
  activeMode: ActiveMode;
  setActiveMode: (mode: ActiveMode) => void;
}

export const useVisualToCodeStore = create<VisualToCodeState>((set) => ({
  activeMode: 'design-import',
  setActiveMode: (mode) => set({ activeMode: mode }),
}));
