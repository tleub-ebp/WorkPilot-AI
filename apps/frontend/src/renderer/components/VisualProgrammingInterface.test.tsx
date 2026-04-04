import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom";

vi.mock("react-i18next", () => ({
	useTranslation: () => ({
		t: (key: string, fallback?: string) => {
			const translations: Record<string, string> = {
				newFlowchart: "New Flowchart",
				newArchitectureDiagram: "New Architecture Diagram",
				newMockup: "New Mockup",
				addBlock: "Add block",
				reverse: "Reverse: Code → Visual",
				generateCode: "Generate code",
				export: "Export JSON",
				saveAs: "Save as\u2026",
				load: "Load",
				chooseFramework: "Choose framework or language",
				chooseFileName: "Export file name",
				customBlockPrompt: "Custom block name?",
			};
			return translations[key] ?? fallback ?? key;
		},
		i18n: { language: "en", changeLanguage: vi.fn() },
	}),
}));

vi.mock("reactflow", async () => {
	const React = await import("react");
	return {
		default: React.forwardRef<
			HTMLDivElement,
			React.HTMLAttributes<HTMLDivElement>
		>(({ children, onDrop, onDragOver }, ref) =>
			React.createElement(
				"div",
				{ ref, "data-testid": "reactflow-canvas", onDrop, onDragOver },
				children,
			),
		),
		MiniMap: () => null,
		Controls: () => null,
		Background: () => null,
		addEdge: vi.fn((params: unknown, eds: unknown[]) => [...eds, params]),
		useNodesState: (initial: unknown[]) => [initial, vi.fn(), vi.fn()],
		useEdgesState: (initial: unknown[]) => [initial, vi.fn(), vi.fn()],
	};
});

vi.mock("file-saver", () => ({ saveAs: vi.fn() }));

vi.mock("@/stores/visual-to-code-store", () => ({
	useVisualToCodeStore: () => ({
		canvasNodes: [
			{
				id: "1",
				position: { x: 250, y: 5 },
				data: { label: "New Flowchart" },
				type: "editable",
			},
		],
		canvasEdges: [],
		canvasDiagramType: "flowchart",
		setCanvasNodes: () => {
			// Mock function for testing
		},
		setCanvasEdges: () => {
			// Mock function for testing
		},
		setCanvasDiagramType: () => {
			// Mock function for testing
		},
	}),
}));

import { CanvasPanel } from "./visual-to-code/CanvasPanel";

describe("CanvasPanel", () => {
	beforeEach(() => {
		// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
		(globalThis as any).electronAPI = {
			// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
			...(globalThis as any).electronAPI,
			onVisualProgrammingStatus: vi.fn(() => vi.fn()),
			onVisualProgrammingError: vi.fn(() => vi.fn()),
			onVisualProgrammingComplete: vi.fn(() => vi.fn()),
			runVisualProgramming: vi.fn().mockResolvedValue({ success: true }),
			saveJsonFile: vi.fn().mockResolvedValue({ success: true }),
			getUserHome: vi.fn().mockReturnValue("/home/user"),
		};
		// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
		(globalThis as any).platform = { isWindows: false };
	});

	it("renders diagram type buttons", () => {
		render(<CanvasPanel />);
		expect(screen.getByText("New Flowchart")).toBeInTheDocument();
		expect(screen.getByText("New Architecture Diagram")).toBeInTheDocument();
		expect(screen.getByText("New Mockup")).toBeInTheDocument();
	});

	it("renders action buttons", () => {
		render(<CanvasPanel />);
		expect(screen.getByText("Add block")).toBeInTheDocument();
		expect(screen.getByText("Reverse: Code \u2192 Visual")).toBeInTheDocument();
		expect(screen.getByText("Generate code")).toBeInTheDocument();
		expect(screen.getByText("Export JSON")).toBeInTheDocument();
		expect(screen.getByText("Save as\u2026")).toBeInTheDocument();
		expect(screen.getByText("Load")).toBeInTheDocument();
	});

	it("renders the ReactFlow canvas", () => {
		render(<CanvasPanel />);
		expect(screen.getByTestId("reactflow-canvas")).toBeInTheDocument();
	});

	it("Generate code button is enabled when diagram has nodes", () => {
		render(<CanvasPanel />);
		// Initial state has 1 node (the default New Flowchart node), so button is enabled
		const button = screen.getByRole("button", { name: "Generate code" });
		expect(button).not.toBeDisabled();
	});
});
