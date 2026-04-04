import type { Edge, Node } from "reactflow";
import { create } from "zustand";
import { persist } from "zustand/middleware";

export type DiagramType = "flowchart" | "architecture" | "mockup";

type ActiveMode = "design-import" | "canvas";

interface VisualToCodeState {
	activeMode: ActiveMode;
	setActiveMode: (mode: ActiveMode) => void;
	// Canvas state (persisted across navigation)
	canvasNodes: Node[];
	canvasEdges: Edge[];
	canvasDiagramType: DiagramType;
	setCanvasNodes: (nodes: Node[]) => void;
	setCanvasEdges: (edges: Edge[]) => void;
	setCanvasDiagramType: (type: DiagramType) => void;
}

export const useVisualToCodeStore = create<VisualToCodeState>()(
	persist(
		(set) => ({
			activeMode: "design-import",
			setActiveMode: (mode) => set({ activeMode: mode }),
			canvasNodes: [],
			canvasEdges: [],
			canvasDiagramType: "flowchart",
			setCanvasNodes: (nodes) => set({ canvasNodes: nodes }),
			setCanvasEdges: (edges) => set({ canvasEdges: edges }),
			setCanvasDiagramType: (type) => set({ canvasDiagramType: type }),
		}),
		{
			name: "visual-to-code-canvas",
			partialize: (state) => ({
				canvasNodes: state.canvasNodes,
				canvasEdges: state.canvasEdges,
				canvasDiagramType: state.canvasDiagramType,
			}),
		},
	),
);
