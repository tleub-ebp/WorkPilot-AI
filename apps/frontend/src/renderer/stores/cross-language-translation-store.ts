import { create } from 'zustand';

export interface SupportedLanguage {
  id: string;
  label: string;
  extension: string;
}

export type TranslationStatus = 'idle' | 'translating' | 'complete' | 'failed';

export interface TranslationHistoryEntry {
  id: string;
  started_at: string;
  completed_at?: string;
  source_lang: string;
  target_lang: string;
  file_path: string;
  status: 'pending' | 'complete' | 'failed';
}

interface CrossLangTranslationState {
  languages: SupportedLanguage[];
  sourceLang: string;
  targetLang: string;
  inputCode: string;
  outputCode: string;
  streamBuffer: string;
  status: TranslationStatus;
  history: TranslationHistoryEntry[];
  preserveComments: boolean;
  generateTests: boolean;
  error: string | null;

  loadLanguages: () => Promise<void>;
  setSourceLang: (lang: string) => void;
  setTargetLang: (lang: string) => void;
  setInputCode: (code: string) => void;
  setPreserveComments: (v: boolean) => void;
  setGenerateTests: (v: boolean) => void;
  translate: (projectDir: string, params?: { filePath?: string; outputPath?: string }) => Promise<void>;
  cancelTranslation: (projectDir: string) => Promise<void>;
  loadHistory: (projectDir: string) => Promise<void>;
  clearHistory: (projectDir: string) => Promise<void>;
  clearError: () => void;
}

const DEFAULT_LANGUAGES: SupportedLanguage[] = [
  { id: 'python', label: 'Python', extension: '.py' },
  { id: 'typescript', label: 'TypeScript', extension: '.ts' },
  { id: 'javascript', label: 'JavaScript', extension: '.js' },
  { id: 'go', label: 'Go', extension: '.go' },
  { id: 'java', label: 'Java', extension: '.java' },
  { id: 'csharp', label: 'C#', extension: '.cs' },
  { id: 'rust', label: 'Rust', extension: '.rs' },
];

export const useCrossLangTranslationStore = create<CrossLangTranslationState>((set, get) => ({
  languages: DEFAULT_LANGUAGES,
  sourceLang: 'python',
  targetLang: 'typescript',
  inputCode: '',
  outputCode: '',
  streamBuffer: '',
  status: 'idle',
  history: [],
  preserveComments: true,
  generateTests: false,
  error: null,

  loadLanguages: async () => {
    try {
      const result = await globalThis.electronAPI.invoke('crossLangTranslation:getSupportedLanguages');
      if (result.success) {
        set({ languages: result.data as SupportedLanguage[] });
      }
    } catch { /* keep defaults */ }
  },

  setSourceLang: (lang) => set({ sourceLang: lang }),
  setTargetLang: (lang) => set({ targetLang: lang }),
  setInputCode: (code) => set({ inputCode: code }),
  setPreserveComments: (v) => set({ preserveComments: v }),
  setGenerateTests: (v) => set({ generateTests: v }),

  translate: async (projectDir, params = {}) => {
    const { sourceLang, targetLang, inputCode, preserveComments, generateTests } = get();
    set({ status: 'translating', streamBuffer: '', outputCode: '', error: null });

    // Listen for stream chunks
    const removeListener = globalThis.electronAPI?.onIpcEvent?.(
      'crossLangTranslation:streamChunk',
      (chunk: string) => {
        set((state) => ({ streamBuffer: state.streamBuffer + chunk }));
      },
    );

    try {
      const result = await globalThis.electronAPI.invoke('crossLangTranslation:translate', {
        projectDir,
        sourceLang,
        targetLang,
        code: params.filePath ? undefined : inputCode,
        filePath: params.filePath,
        outputPath: params.outputPath,
        preserveComments,
        generateTests,
      });

      if (result.success) {
        const data = result.data as { translated_code?: string };
        set({
          status: 'complete',
          outputCode: data.translated_code ?? get().streamBuffer,
        });
      } else {
        set({ status: 'failed', error: result.error ?? 'Translation failed' });
      }
    } catch (err) {
      set({ status: 'failed', error: String(err) });
    } finally {
      removeListener?.();
    }
  },

  cancelTranslation: async (projectDir) => {
    try {
      await globalThis.electronAPI.invoke('crossLangTranslation:cancel', projectDir);
      set({ status: 'idle' });
    } catch { /* ignore */ }
  },

  loadHistory: async (projectDir) => {
    try {
      const result = await globalThis.electronAPI.invoke('crossLangTranslation:getHistory', projectDir);
      if (result.success) {
        set({ history: result.data as TranslationHistoryEntry[] });
      }
    } catch { /* ignore */ }
  },

  clearHistory: async (projectDir) => {
    try {
      await globalThis.electronAPI.invoke('crossLangTranslation:clearHistory', projectDir);
      set({ history: [] });
    } catch { /* ignore */ }
  },

  clearError: () => set({ error: null }),
}));
