/**
 * Pixel Office — Main component wrapping the canvas + toolbar.
 *
 * Each agent terminal AND active Kanban task appears as a pixel art character.
 * Characters reflect real-time activity (typing, reading, waiting, idle).
 */

import {
	Grid3X3,
	LayoutDashboard,
	Users,
	Volume2,
	VolumeX,
	ZoomIn,
	ZoomOut,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
	type PixelAgent,
	usePixelOfficeStore,
} from "../../stores/pixel-office-store";
import { useTaskStore } from "../../stores/task-store";
import { useTerminalStore } from "../../stores/terminal-store";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "../ui/tooltip";
import { AddAgentButton, AgentBubble } from "./AgentBubble";
import { PixelOfficeCanvas } from "./PixelOfficeCanvas";
import { getCharacterSprite } from "./pixel-sprites";

// ── Mini pixel character (for the waiting queue) ─────────────

function MiniPixelChar({
	characterIndex,
}: {
	readonly characterIndex: number;
}) {
	const canvasRef = useRef<HTMLCanvasElement>(null);
	const frameRef = useRef(0);

	useEffect(() => {
		let animId = 0;
		let lastTime = 0;

		const render = (time: number) => {
			if (time - lastTime > 700) {
				frameRef.current = (frameRef.current + 1) % 2;
				lastTime = time;
				const canvas = canvasRef.current;
				if (canvas) {
					const ctx = canvas.getContext("2d");
					if (ctx) {
						ctx.imageSmoothingEnabled = false;
						ctx.clearRect(0, 0, canvas.width, canvas.height);
						const sprite = getCharacterSprite(
							characterIndex,
							"down",
							frameRef.current,
						);
						ctx.drawImage(sprite, 0, 0, canvas.width, canvas.height);
					}
				}
			}
			animId = requestAnimationFrame(render);
		};

		// Initial draw
		const canvas = canvasRef.current;
		if (canvas) {
			const ctx = canvas.getContext("2d");
			if (ctx) {
				ctx.imageSmoothingEnabled = false;
				const sprite = getCharacterSprite(characterIndex, "down", 0);
				ctx.drawImage(sprite, 0, 0, canvas.width, canvas.height);
			}
		}

		animId = requestAnimationFrame(render);
		return () => cancelAnimationFrame(animId);
	}, [characterIndex]);

	return (
		<canvas
			ref={canvasRef}
			width={16}
			height={24}
			style={{ imageRendering: "pixelated", width: 32, height: 48 }}
		/>
	);
}

// ── Waiting queue strip ───────────────────────────────────────

interface WaitingQueueProps {
	readonly agents: PixelAgent[];
	readonly onAgentClick: (agentId: string, x: number, y: number) => void;
}

function WaitingQueue({ agents, onAgentClick }: WaitingQueueProps) {
	if (agents.length === 0) return null;

	return (
		<div
			className="absolute bottom-0 left-0 right-0 pointer-events-none"
			style={{ zIndex: 20 }}
		>
			<div
				className="mx-4 mb-3 rounded-2xl pointer-events-auto overflow-hidden"
				style={{
					background:
						"linear-gradient(to top, rgba(10,8,30,0.97) 0%, rgba(20,14,50,0.92) 100%)",
					border: "1px solid rgba(139,92,246,0.35)",
					boxShadow: "0 -4px 24px rgba(139,92,246,0.12)",
				}}
			>
				{/* Sign / header */}
				<div className="flex items-center gap-2.5 px-4 pt-3 pb-2">
					<div
						className="w-2 h-2 rounded-full shrink-0"
						style={{
							background: "#8B5CF6",
							boxShadow: "0 0 6px #8B5CF6",
							animation: "pulse 2s ease-in-out infinite",
						}}
					/>
					<span
						className="text-xs font-mono font-bold"
						style={{ color: "#C4B5FD" }}
					>
						⏳ En attente de lancement
					</span>
					<span
						className="text-[10px] font-mono ml-auto"
						style={{ color: "rgba(167,139,250,0.5)" }}
					>
						{agents.length} tâche{agents.length > 1 ? "s" : ""} en file
					</span>
				</div>

				{/* Bench line */}
				<div
					className="mx-4 mb-2 h-px"
					style={{ background: "rgba(139,92,246,0.2)" }}
				/>

				{/* Agents queue */}
				<div
					className="flex gap-3 px-4 pb-3 overflow-x-auto"
					style={{ scrollbarWidth: "none" }}
				>
					{agents.map((agent) => (
						<button
							key={agent.id}
							type="button"
							className="flex flex-col items-center gap-1 group transition-opacity hover:opacity-100"
							style={{ opacity: 0.75, minWidth: 48 }}
							onClick={(e) => {
								const rect = e.currentTarget.getBoundingClientRect();
								const parentRect = e.currentTarget
									.closest(".relative")
									?.getBoundingClientRect();
								if (!parentRect) return;
								onAgentClick(
									agent.id,
									rect.left - parentRect.left + rect.width / 2,
									0, // bubble from top
								);
							}}
							title={agent.fullName}
						>
							{/* Slow-bob wrapper */}
							<div
								style={{
									animation: "waitBob 2.5s ease-in-out infinite",
									animationDelay: `${(agent.waitingIndex ?? 0) * 0.4}s`,
								}}
							>
								<MiniPixelChar characterIndex={agent.characterIndex} />
							</div>
							{/* Violet glow dot */}
							<div
								className="w-1.5 h-1.5 rounded-full"
								style={{ background: "#8B5CF6", opacity: 0.7 }}
							/>
							{/* Name */}
							<span
								className="text-[9px] font-mono text-center leading-tight max-w-[52px] truncate"
								style={{ color: "rgba(196,181,253,0.65)" }}
								title={agent.fullName}
							>
								{agent.name}
							</span>
						</button>
					))}
				</div>

				{/* Bench plank at the bottom */}
				<div
					className="mx-4 mb-3 rounded-lg h-2"
					style={{
						background: "linear-gradient(to bottom, #3D2A6E, #2A1A50)",
						border: "1px solid rgba(139,92,246,0.3)",
					}}
				/>
			</div>

			{/* Keyframe for bob animation injected once */}
			<style>{`
        @keyframes waitBob {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-4px); }
        }
      `}</style>
		</div>
	);
}

// ─────────────────────────────────────────────────────────────

interface PixelOfficeProps {
	/** File-system path of the project — used to match terminal sessions */
	readonly projectPath: string;
	/** Project ID (UUID) — used to match Kanban tasks */
	readonly projectId: string;
	readonly onNavigateToTerminals?: () => void;
	readonly onNavigateToKanban?: () => void;
}

export function PixelOffice({
	projectPath,
	projectId,
	onNavigateToTerminals,
	onNavigateToKanban,
}: PixelOfficeProps) {
	useTranslation(["pixelOffice", "common"]);
	const containerRef = useRef<HTMLDivElement>(null);
	const [dimensions, setDimensions] = useState({ width: 800, height: 500 });
	const [bubblePos, setBubblePos] = useState<{ x: number; y: number } | null>(
		null,
	);

	// ── Stores ──────────────────────────────────────────────────

	const terminals = useTerminalStore((s) => s.terminals);
	const jumpToTerminal = useTerminalStore((s) => s.jumpToTerminal);
	const addTerminal = useTerminalStore((s) => s.addTerminal);
	const removeTerminal = useTerminalStore((s) => s.removeTerminal);
	const canAddTerminal = useTerminalStore((s) => s.canAddTerminal);

	const tasks = useTaskStore((s) => s.tasks);
	const selectTask = useTaskStore((s) => s.selectTask);
	const jumpToTask = useTaskStore((s) => s.jumpToTask);

	const agents = usePixelOfficeStore((s) => s.agents);
	const selectedAgentId = usePixelOfficeStore((s) => s.selectedAgentId);
	const settings = usePixelOfficeStore((s) => s.settings);
	const syncAll = usePixelOfficeStore((s) => s.syncAll);
	const selectAgent = usePixelOfficeStore((s) => s.selectAgent);
	const updateSettings = usePixelOfficeStore((s) => s.updateSettings);

	// ── Sync terminals + tasks → pixel agents ───────────────────

	useEffect(() => {
		const projectTerminals = terminals.filter(
			(t) => t.projectPath === projectPath || !t.projectPath,
		);
		const projectTasks = tasks.filter((t) => t.projectId === projectId);
		syncAll(projectTerminals, projectTasks);
	}, [terminals, tasks, projectPath, projectId, syncAll]);

	// ── Container resize ────────────────────────────────────────

	useEffect(() => {
		const el = containerRef.current;
		if (!el) return;
		const ro = new ResizeObserver((entries) => {
			for (const entry of entries) {
				const { width, height } = entry.contentRect;
				setDimensions({
					width: Math.floor(width),
					height: Math.floor(height) - 52,
				});
			}
		});
		ro.observe(el);
		return () => ro.disconnect();
	}, []);

	// ── Bubble handlers ─────────────────────────────────────────

	const handleAgentClick = useCallback(
		(agentId: string, screenX: number, screenY: number) => {
			if (!agentId) {
				selectAgent(null);
				setBubblePos(null);
				return;
			}
			selectAgent(agentId);
			setBubblePos({ x: screenX, y: screenY });
		},
		[selectAgent],
	);

	const closeBubble = useCallback(() => {
		selectAgent(null);
		setBubblePos(null);
	}, [selectAgent]);

	// ── Terminal agent actions ───────────────────────────────────

	const handleGoToTerminal = useCallback(() => {
		const agent = agents.find((a) => a.id === selectedAgentId);
		if (agent?.type !== "terminal" || !selectedAgentId) return;
		jumpToTerminal(selectedAgentId);
		onNavigateToTerminals?.();
		closeBubble();
	}, [
		agents,
		selectedAgentId,
		jumpToTerminal,
		onNavigateToTerminals,
		closeBubble,
	]);

	const handleKill = useCallback(async () => {
		if (!selectedAgentId) return;
		closeBubble();
		await globalThis.electronAPI.destroyTerminal(selectedAgentId);
		removeTerminal(selectedAgentId);
	}, [selectedAgentId, removeTerminal, closeBubble]);

	const handleInterrupt = useCallback(() => {
		if (!selectedAgentId) return;
		globalThis.electronAPI.sendTerminalInput(selectedAgentId, "\x03");
	}, [selectedAgentId]);

	const handleResumeClaude = useCallback(() => {
		if (!selectedAgentId) return;
		globalThis.electronAPI.invokeClaudeInTerminal(selectedAgentId);
	}, [selectedAgentId]);

	const handleSendCommand = useCallback(
		(cmd: string) => {
			if (!selectedAgentId) return;
			globalThis.electronAPI.sendTerminalInput(selectedAgentId, `${cmd}\n`);
		},
		[selectedAgentId],
	);

	// ── Task agent actions ───────────────────────────────────────

	const handleGoToTask = useCallback(() => {
		const agent = agents.find((a) => a.id === selectedAgentId);
		if (!agent?.taskId) return;
		selectTask(agent.taskId);
		jumpToTask(agent.taskId); // triggers scroll + spotlight in TaskCard
		onNavigateToKanban?.();
		closeBubble();
	}, [
		agents,
		selectedAgentId,
		selectTask,
		jumpToTask,
		onNavigateToKanban,
		closeBubble,
	]);

	const handleStopTask = useCallback(() => {
		const agent = agents.find((a) => a.id === selectedAgentId);
		if (!agent?.taskId) return;
		globalThis.electronAPI.stopTask(agent.taskId);
		closeBubble();
	}, [agents, selectedAgentId, closeBubble]);

	// ── Pending agent click (from WaitingQueue strip) ────────────

	const handlePendingAgentClick = useCallback(
		(agentId: string, x: number, _y: number) => {
			selectAgent(agentId);
			setBubblePos({ x, y: 0 }); // bubble fills from top so it appears above the queue
		},
		[selectAgent],
	);

	// ── New terminal ─────────────────────────────────────────────

	const handleAddAgent = useCallback(async () => {
		const cwd = terminals.find((t) => t.projectPath === projectPath)?.cwd;
		const newTerminal = addTerminal(cwd, projectPath);
		if (!newTerminal) return;
		await globalThis.electronAPI.createTerminal({
			id: newTerminal.id,
			cwd: newTerminal.cwd,
			projectPath: projectPath,
		});
	}, [terminals, projectPath, addTerminal]);

	// ── Zoom / grid / sound ──────────────────────────────────────

	const handleZoomIn = () =>
		updateSettings({ zoom: Math.min(settings.zoom + 1, 6) });
	const handleZoomOut = () =>
		updateSettings({ zoom: Math.max(settings.zoom - 1, 1) });
	const toggleSound = () =>
		updateSettings({ soundEnabled: !settings.soundEnabled });
	const toggleGrid = () => updateSettings({ showGrid: !settings.showGrid });

	// ── Derived state ────────────────────────────────────────────

	const selectedAgent = agents.find((a) => a.id === selectedAgentId);
	const selectedTerminal =
		selectedAgent?.type === "terminal"
			? terminals.find((t) => t.id === selectedAgentId)
			: undefined;

	const pendingAgents = agents.filter((a) => a.activity === "pending");
	const activeAgents = agents.filter((a) => a.activity !== "pending");

	const terminalCount = activeAgents.filter(
		(a) => a.type === "terminal",
	).length;
	const taskCount = activeAgents.filter((a) => a.type === "task").length;
	const activeCount = activeAgents.filter(
		(a) => a.activity !== "idle" && a.activity !== "exited",
	).length;

	return (
		<div ref={containerRef} className="flex flex-col h-full overflow-hidden">
			{/* Toolbar */}
			<div className="flex items-center justify-between px-4 py-2 border-b border-border bg-background/80 backdrop-blur-sm shrink-0">
				<div className="flex items-center gap-2">
					<span className="text-base font-bold tracking-tight font-mono">
						🏢 Pixel Office
					</span>

					{terminalCount > 0 && (
						<Badge variant="secondary" className="font-mono text-xs gap-1">
							<Users className="h-3 w-3" />
							{terminalCount} terminal{terminalCount > 1 ? "x" : ""}
						</Badge>
					)}
					{taskCount > 0 && (
						<Badge
							variant="secondary"
							className="font-mono text-xs gap-1 border-orange-500/40 text-orange-400"
						>
							<LayoutDashboard className="h-3 w-3" />
							{taskCount} tâche{taskCount > 1 ? "s" : ""}
						</Badge>
					)}
					{activeCount > 0 && (
						<Badge
							variant="default"
							className="font-mono text-xs bg-emerald-600"
						>
							{activeCount} actif{activeCount > 1 ? "s" : ""}
						</Badge>
					)}
					{pendingAgents.length > 0 && (
						<Badge
							variant="secondary"
							className="font-mono text-xs gap-1"
							style={{ borderColor: "rgba(139,92,246,0.4)", color: "#A78BFA" }}
						>
							⏳ {pendingAgents.length} en attente
						</Badge>
					)}
				</div>

				<div className="flex items-center gap-1">
					<AddAgentButton
						onClick={handleAddAgent}
						disabled={!canAddTerminal(projectPath)}
					/>
					<div className="w-px h-5 bg-border mx-1" />

					<Tooltip>
						<TooltipTrigger asChild>
							<Button
								variant="ghost"
								size="icon"
								className="h-8 w-8"
								onClick={handleZoomOut}
							>
								<ZoomOut className="h-4 w-4" />
							</Button>
						</TooltipTrigger>
						<TooltipContent>Zoom Out</TooltipContent>
					</Tooltip>

					<span className="text-xs font-mono text-muted-foreground w-8 text-center">
						{settings.zoom}x
					</span>

					<Tooltip>
						<TooltipTrigger asChild>
							<Button
								variant="ghost"
								size="icon"
								className="h-8 w-8"
								onClick={handleZoomIn}
							>
								<ZoomIn className="h-4 w-4" />
							</Button>
						</TooltipTrigger>
						<TooltipContent>Zoom In</TooltipContent>
					</Tooltip>

					<div className="w-px h-5 bg-border mx-1" />

					<Tooltip>
						<TooltipTrigger asChild>
							<Button
								variant="ghost"
								size="icon"
								className="h-8 w-8"
								onClick={toggleGrid}
							>
								<Grid3X3 className="h-4 w-4" />
							</Button>
						</TooltipTrigger>
						<TooltipContent>Toggle Grid</TooltipContent>
					</Tooltip>

					<Tooltip>
						<TooltipTrigger asChild>
							<Button
								variant="ghost"
								size="icon"
								className="h-8 w-8"
								onClick={toggleSound}
							>
								{settings.soundEnabled ? (
									<Volume2 className="h-4 w-4" />
								) : (
									<VolumeX className="h-4 w-4" />
								)}
							</Button>
						</TooltipTrigger>
						<TooltipContent>Toggle Sound</TooltipContent>
					</Tooltip>
				</div>
			</div>

			{/* Canvas area */}
			<div className="flex-1 bg-[#1A1A2E] overflow-hidden relative">
				{agents.length === 0 ? (
					<div className="flex flex-col items-center justify-center h-full text-center gap-4 px-8">
						<div className="text-6xl">🏢</div>
						<h2 className="text-xl font-bold text-white/80 font-mono">
							Votre bureau est vide
						</h2>
						<p className="text-sm text-white/50 max-w-md">
							Démarrez une tâche dans le Kanban ou ouvrez des terminaux pour
							voir vos agents IA apparaître à leurs bureaux avec un suivi
							d'activité en direct.
						</p>
						<AddAgentButton
							onClick={handleAddAgent}
							disabled={!canAddTerminal(projectPath)}
						/>
					</div>
				) : (
					<>
						{activeAgents.length > 0 && (
							<PixelOfficeCanvas
								width={dimensions.width}
								height={dimensions.height}
								onAgentClick={handleAgentClick}
							/>
						)}

						{/* Pending-only placeholder when no desk agents yet */}
						{activeAgents.length === 0 && (
							<div className="flex flex-col items-center justify-center h-full pb-40 gap-3 text-center px-8">
								<div className="text-5xl">🏢</div>
								<p className="text-sm text-white/40 font-mono">
									Les agents démarreront dès le lancement des tâches
								</p>
							</div>
						)}

						{/* Waiting queue strip — always visible when pending agents exist */}
						<WaitingQueue
							agents={pendingAgents}
							onAgentClick={handlePendingAgentClick}
						/>

						{/* Backdrop */}
						{selectedAgent && bubblePos && (
							<button
								type="button"
								aria-label="Fermer la bulle"
								className="absolute inset-0 cursor-default bg-transparent border-0 p-0"
								style={{ zIndex: 40 }}
								onClick={closeBubble}
							/>
						)}

						{/* Speech bubble overlay */}
						{selectedAgent && bubblePos && (
							<AgentBubble
								agent={selectedAgent}
								terminal={selectedTerminal}
								anchorX={bubblePos.x}
								anchorY={bubblePos.y}
								onClose={closeBubble}
								onGoToTerminal={handleGoToTerminal}
								onGoToTask={handleGoToTask}
								onKill={handleKill}
								onInterrupt={handleInterrupt}
								onResumeClaude={handleResumeClaude}
								onSendCommand={handleSendCommand}
								onStopTask={handleStopTask}
							/>
						)}
					</>
				)}
			</div>
		</div>
	);
}
