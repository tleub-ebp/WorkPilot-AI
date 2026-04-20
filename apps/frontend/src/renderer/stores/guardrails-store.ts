import { create } from "zustand";
import type {
	GuardrailRuleDoc,
	GuardrailsDoc,
	GuardrailTestResult,
} from "../../preload/api/modules/guardrails-api";

interface GuardrailsState {
	doc: GuardrailsDoc;
	dirty: boolean;
	loading: boolean;
	error: string | null;
	lastTest: GuardrailTestResult | null;

	load: (projectPath: string) => Promise<void>;
	save: (projectPath: string) => Promise<void>;
	addRule: () => void;
	updateRule: (index: number, patch: Partial<GuardrailRuleDoc>) => void;
	deleteRule: (index: number) => void;
	runTest: (
		projectPath: string,
		toolName: string,
		toolInput: Record<string, unknown>,
	) => Promise<void>;
	reset: () => void;
}

const emptyRule = (): GuardrailRuleDoc => ({
	id: `rule-${Date.now()}`,
	description: "",
	action: "warn",
	when: { tool: ["Write", "Edit"] },
});

export const useGuardrailsStore = create<GuardrailsState>((set, get) => ({
	doc: { version: 1, rules: [] },
	dirty: false,
	loading: false,
	error: null,
	lastTest: null,

	load: async (projectPath) => {
		set({ loading: true, error: null });
		try {
			const doc = await globalThis.electronAPI.loadGuardrails(projectPath);
			set({ doc, dirty: false, loading: false });
		} catch (e) {
			set({ error: String(e), loading: false });
		}
	},

	save: async (projectPath) => {
		set({ loading: true, error: null });
		try {
			await globalThis.electronAPI.saveGuardrails(projectPath, get().doc);
			set({ dirty: false, loading: false });
		} catch (e) {
			set({ error: String(e), loading: false });
		}
	},

	addRule: () =>
		set((s) => ({
			doc: { ...s.doc, rules: [...s.doc.rules, emptyRule()] },
			dirty: true,
		})),

	updateRule: (index, patch) =>
		set((s) => ({
			doc: {
				...s.doc,
				rules: s.doc.rules.map((r, i) =>
					i === index ? { ...r, ...patch, when: { ...r.when, ...(patch.when ?? {}) } } : r,
				),
			},
			dirty: true,
		})),

	deleteRule: (index) =>
		set((s) => ({
			doc: {
				...s.doc,
				rules: s.doc.rules.filter((_, i) => i !== index),
			},
			dirty: true,
		})),

	runTest: async (projectPath, toolName, toolInput) => {
		try {
			const lastTest = await globalThis.electronAPI.testGuardrails(
				projectPath,
				toolName,
				toolInput,
			);
			set({ lastTest });
		} catch (e) {
			set({ error: String(e) });
		}
	},

	reset: () => set({ lastTest: null, error: null }),
}));
