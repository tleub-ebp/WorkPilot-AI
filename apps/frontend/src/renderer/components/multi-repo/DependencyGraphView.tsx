import type {
	RepoDependencyGraph,
	RepoExecutionState,
	RepoExecutionStatus,
} from "@shared/types";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";

interface DependencyGraphViewProps {
	graph: RepoDependencyGraph;
	executionOrder: string[];
	repoStates: RepoExecutionState[];
}

const STATUS_COLORS: Record<RepoExecutionStatus, string> = {
	pending: "#6b7280", // gray
	analyzing: "#3b82f6", // blue
	planning: "#8b5cf6", // purple
	coding: "#f59e0b", // amber
	qa: "#06b6d4", // cyan
	completed: "#22c55e", // green
	failed: "#ef4444", // red
	skipped: "#9ca3af", // light gray
};

/**
 * DependencyGraphView - SVG node-link diagram of repository dependencies
 */
export function DependencyGraphView({
	graph,
	executionOrder,
	repoStates,
}: DependencyGraphViewProps) {
	const { t } = useTranslation(["multiRepo"]);

	const layout = useMemo(() => {
		const nodes = executionOrder.length > 0 ? executionOrder : graph.nodes;
		if (nodes.length === 0)
			return { nodes: [], edges: [], width: 0, height: 0 };

		const nodeWidth = 160;
		const nodeHeight = 48;
		const horizontalGap = 60;
		const verticalGap = 80;
		const cols = Math.min(nodes.length, 4);
		const rows = Math.ceil(nodes.length / cols);

		const width = cols * (nodeWidth + horizontalGap) + horizontalGap;
		const height = rows * (nodeHeight + verticalGap) + verticalGap;

		const nodePositions = nodes.map((name, i) => {
			const col = i % cols;
			const row = Math.floor(i / cols);
			return {
				name,
				x: horizontalGap + col * (nodeWidth + horizontalGap),
				y: verticalGap + row * (nodeHeight + verticalGap),
				width: nodeWidth,
				height: nodeHeight,
			};
		});

		const nodeMap = new Map(nodePositions.map((n) => [n.name, n]));

		const edgeLines = graph.edges
			.map((edge) => {
				const source = nodeMap.get(edge.source);
				const target = nodeMap.get(edge.target);
				if (!source || !target) return null;
				return {
					x1: source.x + source.width / 2,
					y1: source.y + source.height / 2,
					x2: target.x + target.width / 2,
					y2: target.y + target.height / 2,
					type: edge.type,
				};
			})
			.filter(Boolean);

		return { nodes: nodePositions, edges: edgeLines, width, height };
	}, [graph, executionOrder]);

	const getRepoStatus = (repo: string): RepoExecutionStatus => {
		const state = repoStates.find((rs) => rs.repo === repo);
		return state?.status || "pending";
	};

	const getRepoProgress = (repo: string): number => {
		const state = repoStates.find((rs) => rs.repo === repo);
		return state?.progress || 0;
	};

	if (layout.nodes.length === 0) {
		return (
			<div className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
				{t("multiRepo:graph.noRepos")}
			</div>
		);
	}

	return (
		<div className="rounded-lg border border-border bg-card p-4">
			<h3 className="mb-3 text-sm font-medium text-foreground">
				{t("multiRepo:graph.title")}
			</h3>
			<div className="overflow-auto">
				{/* biome-ignore lint/a11y/noSvgWithoutTitle: SVG is decorative, intentional */}
				<svg
					width={layout.width}
					height={layout.height}
					className="mx-auto"
					viewBox={`0 0 ${layout.width} ${layout.height}`}
				>
					<defs>
						<marker
							id="arrowhead"
							markerWidth="10"
							markerHeight="7"
							refX="10"
							refY="3.5"
							orient="auto"
						>
							<polygon points="0 0, 10 3.5, 0 7" fill="#6b7280" />
						</marker>
					</defs>

					{/* Edges */}
					{layout.edges.map(
						(edge, i) =>
							edge && (
								<line
									// biome-ignore lint/suspicious/noArrayIndexKey: no stable key available
									key={`edge-${i}`}
									x1={edge.x1}
									y1={edge.y1}
									x2={edge.x2}
									y2={edge.y2}
									stroke="#6b7280"
									strokeWidth={1.5}
									strokeDasharray={edge.type === "api" ? "5,3" : undefined}
									markerEnd="url(#arrowhead)"
									opacity={0.5}
								/>
							),
					)}

					{/* Nodes */}
					{layout.nodes.map((node) => {
						const status = getRepoStatus(node.name);
						const progress = getRepoProgress(node.name);
						const color = STATUS_COLORS[status];
						const displayName = node.name.split("/").pop() || node.name;

						return (
							<g key={node.name}>
								{/* Background */}
								<rect
									x={node.x}
									y={node.y}
									width={node.width}
									height={node.height}
									rx={8}
									fill="var(--color-card)"
									stroke={color}
									strokeWidth={2}
								/>

								{/* Progress bar */}
								{progress > 0 && progress < 100 && (
									<rect
										x={node.x}
										y={node.y + node.height - 4}
										width={(node.width * progress) / 100}
										height={4}
										rx={2}
										fill={color}
										opacity={0.6}
									/>
								)}

								{/* Status indicator dot */}
								<circle
									cx={node.x + 14}
									cy={node.y + node.height / 2}
									r={5}
									fill={color}
								/>

								{/* Repo name */}
								<text
									x={node.x + 26}
									y={node.y + node.height / 2 - 4}
									className="text-[11px] font-medium"
									fill="var(--color-foreground)"
									dominantBaseline="auto"
								>
									{displayName.length > 16
										? `${displayName.slice(0, 14)}...`
										: displayName}
								</text>

								{/* Status label */}
								<text
									x={node.x + 26}
									y={node.y + node.height / 2 + 10}
									className="text-[9px]"
									fill={color}
									dominantBaseline="auto"
								>
									{status}
									{progress > 0 && progress < 100
										? ` ${Math.round(progress)}%`
										: ""}
								</text>
							</g>
						);
					})}
				</svg>
			</div>

			{/* Execution order legend */}
			{executionOrder.length > 0 && (
				<div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
					<span className="font-medium">
						{t("multiRepo:graph.executionOrder")}:
					</span>
					{executionOrder.map((repo, i) => (
						<span key={repo} className="flex items-center gap-1">
							<span className="inline-flex h-4 w-4 items-center justify-center rounded-full bg-primary/10 text-[10px] font-medium text-primary">
								{i + 1}
							</span>
							{repo.split("/").pop()}
							{i < executionOrder.length - 1 && (
								<span className="text-border ml-1">→</span>
							)}
						</span>
					))}
				</div>
			)}
		</div>
	);
}
