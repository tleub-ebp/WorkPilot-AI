/**
 * @vitest-environment jsdom
 */

/**
 * Unit tests for Prompt Optimizer Store
 * Tests Zustand store actions, IPC helpers (startOptimization, setupPromptOptimizerListeners)
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mock electronAPI
const mockOptimizePrompt = vi.fn();
const mockOnPromptOptimizerStreamChunk = vi.fn();
const mockOnPromptOptimizerStatus = vi.fn();
const mockOnPromptOptimizerError = vi.fn();
const mockOnPromptOptimizerComplete = vi.fn();

// Setup mocks before each test
beforeEach(() => {
	vi.clearAllMocks();
	vi.resetModules();

	// Mock globalThis.electronAPI
	Object.defineProperty(globalThis, "electronAPI", {
		value: {
			optimizePrompt: mockOptimizePrompt,
			onPromptOptimizerStreamChunk: mockOnPromptOptimizerStreamChunk,
			onPromptOptimizerStatus: mockOnPromptOptimizerStatus,
			onPromptOptimizerError: mockOnPromptOptimizerError,
			onPromptOptimizerComplete: mockOnPromptOptimizerComplete,
		},
		writable: true,
		configurable: true,
	});
});

describe("Prompt Optimizer Store", () => {
	let usePromptOptimizerStore: typeof import("../prompt-optimizer-store").usePromptOptimizerStore;
	let startOptimization: typeof import("../prompt-optimizer-store").startOptimization;
	let setupPromptOptimizerListeners: typeof import("../prompt-optimizer-store").setupPromptOptimizerListeners;

	beforeEach(async () => {
		// Mock the listener functions to return cleanup functions
		mockOnPromptOptimizerStreamChunk.mockReturnValue(vi.fn());
		mockOnPromptOptimizerStatus.mockReturnValue(vi.fn());
		mockOnPromptOptimizerError.mockReturnValue(vi.fn());
		mockOnPromptOptimizerComplete.mockReturnValue(vi.fn());

		const storeModule = await import("../prompt-optimizer-store");
		usePromptOptimizerStore = storeModule.usePromptOptimizerStore;
		startOptimization = storeModule.startOptimization;
		setupPromptOptimizerListeners = storeModule.setupPromptOptimizerListeners;
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	describe("Initial State", () => {
		it("should have correct default initial state", () => {
			const state = usePromptOptimizerStore.getState();
			expect(state.phase).toBe("idle");
			expect(state.status).toBe("");
			expect(state.streamingOutput).toBe("");
			expect(state.result).toBeNull();
			expect(state.error).toBeNull();
			expect(state.isOpen).toBe(false);
			expect(state.initialPrompt).toBe("");
			expect(state.agentType).toBe("general");
		});
	});

	describe("openDialog", () => {
		it("should open dialog with prompt and default agent type", () => {
			usePromptOptimizerStore.getState().openDialog("test prompt");

			const state = usePromptOptimizerStore.getState();
			expect(state.isOpen).toBe(true);
			expect(state.initialPrompt).toBe("test prompt");
			expect(state.agentType).toBe("general");
			expect(state.phase).toBe("idle");
		});

		it("should open dialog with custom agent type", () => {
			usePromptOptimizerStore.getState().openDialog("coding task", "coding");

			const state = usePromptOptimizerStore.getState();
			expect(state.isOpen).toBe(true);
			expect(state.initialPrompt).toBe("coding task");
			expect(state.agentType).toBe("coding");
		});

		it("should reset state when opening dialog", () => {
			// Set some dirty state first
			usePromptOptimizerStore.setState({
				phase: "error",
				error: "old error",
				streamingOutput: "old output",
				result: { optimized: "old", changes: [], reasoning: "" },
			});

			usePromptOptimizerStore.getState().openDialog("fresh prompt");

			const state = usePromptOptimizerStore.getState();
			expect(state.phase).toBe("idle");
			expect(state.error).toBeNull();
			expect(state.streamingOutput).toBe("");
			expect(state.result).toBeNull();
			expect(state.status).toBe("");
		});
	});

	describe("closeDialog", () => {
		it("should close dialog and reset transient state", () => {
			usePromptOptimizerStore.setState({
				isOpen: true,
				phase: "complete",
				status: "done",
				streamingOutput: "output",
				result: { optimized: "test", changes: ["a"], reasoning: "r" },
			});

			usePromptOptimizerStore.getState().closeDialog();

			const state = usePromptOptimizerStore.getState();
			expect(state.isOpen).toBe(false);
			expect(state.phase).toBe("idle");
			expect(state.status).toBe("");
			expect(state.streamingOutput).toBe("");
			expect(state.result).toBeNull();
			expect(state.error).toBeNull();
		});
	});

	describe("setPhase", () => {
		it("should update phase", () => {
			usePromptOptimizerStore.getState().setPhase("optimizing");
			expect(usePromptOptimizerStore.getState().phase).toBe("optimizing");

			usePromptOptimizerStore.getState().setPhase("complete");
			expect(usePromptOptimizerStore.getState().phase).toBe("complete");
		});
	});

	describe("setStatus", () => {
		it("should update status text", () => {
			usePromptOptimizerStore.getState().setStatus("Analyzing prompt...");
			expect(usePromptOptimizerStore.getState().status).toBe(
				"Analyzing prompt...",
			);
		});
	});

	describe("appendStreamingOutput", () => {
		it("should append chunks to streaming output", () => {
			usePromptOptimizerStore.getState().appendStreamingOutput("Hello ");
			usePromptOptimizerStore.getState().appendStreamingOutput("world!");

			expect(usePromptOptimizerStore.getState().streamingOutput).toBe(
				"Hello world!",
			);
		});

		it("should handle empty chunks", () => {
			usePromptOptimizerStore.getState().appendStreamingOutput("initial");
			usePromptOptimizerStore.getState().appendStreamingOutput("");

			expect(usePromptOptimizerStore.getState().streamingOutput).toBe(
				"initial",
			);
		});
	});

	describe("setResult", () => {
		it("should set result and transition to complete phase", () => {
			const result = {
				optimized: "Better prompt here",
				changes: ["Added context", "Improved clarity"],
				reasoning: "The prompt lacked specifics",
			};

			usePromptOptimizerStore.getState().setResult(result);

			const state = usePromptOptimizerStore.getState();
			expect(state.result).toEqual(result);
			expect(state.phase).toBe("complete");
		});
	});

	describe("setError", () => {
		it("should set error and transition to error phase", () => {
			usePromptOptimizerStore.getState().setError("Connection timeout");

			const state = usePromptOptimizerStore.getState();
			expect(state.error).toBe("Connection timeout");
			expect(state.phase).toBe("error");
		});
	});

	describe("setAgentType", () => {
		it("should update agent type", () => {
			usePromptOptimizerStore.getState().setAgentType("analysis");
			expect(usePromptOptimizerStore.getState().agentType).toBe("analysis");

			usePromptOptimizerStore.getState().setAgentType("verification");
			expect(usePromptOptimizerStore.getState().agentType).toBe("verification");
		});
	});

	describe("reset", () => {
		it("should restore all state to initial values", () => {
			usePromptOptimizerStore.setState({
				phase: "complete",
				status: "done",
				streamingOutput: "output",
				result: { optimized: "x", changes: [], reasoning: "" },
				error: null,
				isOpen: true,
				initialPrompt: "test",
				agentType: "coding",
			});

			usePromptOptimizerStore.getState().reset();

			const state = usePromptOptimizerStore.getState();
			expect(state.phase).toBe("idle");
			expect(state.status).toBe("");
			expect(state.streamingOutput).toBe("");
			expect(state.result).toBeNull();
			expect(state.error).toBeNull();
			expect(state.isOpen).toBe(false);
			expect(state.initialPrompt).toBe("");
			expect(state.agentType).toBe("general");
		});
	});

	describe("startOptimization", () => {
		it("should call IPC with project, prompt and agent type", () => {
			usePromptOptimizerStore.setState({
				initialPrompt: "Build a REST API",
				agentType: "coding",
			});

			startOptimization("project-123");

			expect(mockOptimizePrompt).toHaveBeenCalledWith(
				"project-123",
				"Build a REST API",
				"coding",
			);
		});

		it("should set phase to optimizing", () => {
			usePromptOptimizerStore.setState({
				initialPrompt: "test prompt",
				agentType: "general",
			});

			startOptimization("project-1");

			expect(usePromptOptimizerStore.getState().phase).toBe("optimizing");
		});

		it("should clear previous streaming output and errors", () => {
			usePromptOptimizerStore.setState({
				initialPrompt: "test prompt",
				agentType: "general",
				streamingOutput: "old output",
				error: "old error",
				result: { optimized: "old", changes: [], reasoning: "" },
			});

			startOptimization("project-1");

			const state = usePromptOptimizerStore.getState();
			expect(state.streamingOutput).toBe("");
			expect(state.error).toBeNull();
			expect(state.result).toBeNull();
		});

		it("should not call IPC if prompt is empty", () => {
			usePromptOptimizerStore.setState({
				initialPrompt: "   ",
				agentType: "general",
			});

			startOptimization("project-1");

			expect(mockOptimizePrompt).not.toHaveBeenCalled();
		});

		it("should not call IPC if prompt is empty string", () => {
			usePromptOptimizerStore.setState({
				initialPrompt: "",
				agentType: "general",
			});

			startOptimization("project-1");

			expect(mockOptimizePrompt).not.toHaveBeenCalled();
		});
	});

	describe("setupPromptOptimizerListeners", () => {
		it("should register all four IPC listeners", () => {
			// Mock all listener registrations to return cleanup fns
			mockOnPromptOptimizerStreamChunk.mockReturnValue(vi.fn());
			mockOnPromptOptimizerStatus.mockReturnValue(vi.fn());
			mockOnPromptOptimizerError.mockReturnValue(vi.fn());
			mockOnPromptOptimizerComplete.mockReturnValue(vi.fn());

			setupPromptOptimizerListeners();

			expect(mockOnPromptOptimizerStreamChunk).toHaveBeenCalledTimes(1);
			expect(mockOnPromptOptimizerStatus).toHaveBeenCalledTimes(1);
			expect(mockOnPromptOptimizerError).toHaveBeenCalledTimes(1);
			expect(mockOnPromptOptimizerComplete).toHaveBeenCalledTimes(1);
		});

		it("should return a cleanup function that calls all unsubscribers", () => {
			const unsubChunk = vi.fn();
			const unsubStatus = vi.fn();
			const unsubError = vi.fn();
			const unsubComplete = vi.fn();

			mockOnPromptOptimizerStreamChunk.mockReturnValue(unsubChunk);
			mockOnPromptOptimizerStatus.mockReturnValue(unsubStatus);
			mockOnPromptOptimizerError.mockReturnValue(unsubError);
			mockOnPromptOptimizerComplete.mockReturnValue(unsubComplete);

			const cleanup = setupPromptOptimizerListeners();
			cleanup();

			expect(unsubChunk).toHaveBeenCalledTimes(1);
			expect(unsubStatus).toHaveBeenCalledTimes(1);
			expect(unsubError).toHaveBeenCalledTimes(1);
			expect(unsubComplete).toHaveBeenCalledTimes(1);
		});

		it("should update store on stream chunk event", () => {
			mockOnPromptOptimizerStreamChunk.mockImplementation(
				(cb: (chunk: string) => void) => {
					cb("first chunk ");
					cb("second chunk");
					return vi.fn();
				},
			);
			mockOnPromptOptimizerStatus.mockReturnValue(vi.fn());
			mockOnPromptOptimizerError.mockReturnValue(vi.fn());
			mockOnPromptOptimizerComplete.mockReturnValue(vi.fn());

			setupPromptOptimizerListeners();

			expect(usePromptOptimizerStore.getState().streamingOutput).toBe(
				"first chunk second chunk",
			);
		});

		it("should update store on status event", () => {
			mockOnPromptOptimizerStreamChunk.mockReturnValue(vi.fn());
			mockOnPromptOptimizerStatus.mockImplementation(
				(cb: (status: string) => void) => {
					cb("Analyzing project context...");
					return vi.fn();
				},
			);
			mockOnPromptOptimizerError.mockReturnValue(vi.fn());
			mockOnPromptOptimizerComplete.mockReturnValue(vi.fn());

			setupPromptOptimizerListeners();

			expect(usePromptOptimizerStore.getState().status).toBe(
				"Analyzing project context...",
			);
		});

		it("should update store on error event", () => {
			mockOnPromptOptimizerStreamChunk.mockReturnValue(vi.fn());
			mockOnPromptOptimizerStatus.mockReturnValue(vi.fn());
			mockOnPromptOptimizerError.mockImplementation(
				(cb: (error: string) => void) => {
					cb("Process crashed");
					return vi.fn();
				},
			);
			mockOnPromptOptimizerComplete.mockReturnValue(vi.fn());

			setupPromptOptimizerListeners();

			const state = usePromptOptimizerStore.getState();
			expect(state.error).toBe("Process crashed");
			expect(state.phase).toBe("error");
		});

		it("should update store on complete event", () => {
			const mockResult = {
				optimized: "Enhanced prompt",
				changes: ["Added project context"],
				reasoning: "Enriched with stack info",
			};

			mockOnPromptOptimizerStreamChunk.mockReturnValue(vi.fn());
			mockOnPromptOptimizerStatus.mockReturnValue(vi.fn());
			mockOnPromptOptimizerError.mockReturnValue(vi.fn());
			mockOnPromptOptimizerComplete.mockImplementation(
				(cb: (result: any) => void) => {
					cb(mockResult);
					return vi.fn();
				},
			);

			setupPromptOptimizerListeners();

			const state = usePromptOptimizerStore.getState();
			expect(state.result).toEqual(mockResult);
			expect(state.phase).toBe("complete");
		});
	});
});
