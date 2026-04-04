/**
 * Pixel Office Canvas — The core rendering engine.
 *
 * Renders a pixel art office with animated characters representing
 * active agent terminals. Uses requestAnimationFrame for smooth 60fps.
 */

import { useCallback, useEffect, useRef } from "react";
import {
	type AgentActivity,
	type PixelAgent,
	usePixelOfficeStore,
} from "../../stores/pixel-office-store";
import {
	type ActivityIcon,
	CHAIR_H,
	DESK_H,
	drawSpeechBubble,
	getActivityIcon,
	getChairSprite,
	getCharacterSprite,
	getDeskSprite,
	getFloorTile,
	getWallTile,
	SPRITE_H,
	TILE_SIZE,
} from "./pixel-sprites";

// ── Layout constants ─────────────────────────────────────────

const OFFICE_COLS = 24;
const OFFICE_ROWS = 16;
const DESK_SPACING_X = 5;
const DESK_SPACING_Y = 5;
const DESK_START_X = 3;
const DESK_START_Y = 2;
const DESKS_PER_ROW = 4;
const MAX_DESK_ROWS = 3;

const CHAR_OFFSET_Y = (DESK_H + CHAIR_H) / TILE_SIZE;

// ── Activity config ───────────────────────────────────────────

const ACTIVITY_COLORS: Record<string, string> = {
	typing: "#4A90D9",
	running: "#1ABC9C",
	waiting: "#F39C12",
	reading: "#27AE60",
	exited: "#E74C3C",
	idle: "#6B7280",
};

interface AgentVisual {
	color: string;
	isActive: boolean;
	isWaiting: boolean;
	isIdle: boolean;
	bounceY: number;
}

function getAgentVisual(
	activity: AgentActivity,
	frame: number,
	z: number,
): AgentVisual {
	const color = ACTIVITY_COLORS[activity] ?? "#6B7280";
	const isActive =
		activity === "typing" || activity === "running" || activity === "reading";
	const isWaiting = activity === "waiting";
	const isIdle = activity === "idle" || activity === "exited";

	let bounceY = 0;
	if (activity === "typing") bounceY = Math.sin(frame * 0.35) * 1.2 * z;
	else if (activity === "running")
		bounceY = Math.abs(Math.sin(frame * 0.25)) * -1.5 * z;
	else if (isWaiting) bounceY = Math.sin(frame * 0.08) * 0.8 * z;

	return { color, isActive, isWaiting, isIdle, bounceY };
}

function activityToDirection(activity: AgentActivity): "down" | "up" {
	if (activity === "typing" || activity === "reading" || activity === "running")
		return "up";
	return "down";
}

function activityToIcon(activity: AgentActivity): ActivityIcon {
	switch (activity) {
		case "typing":
			return "typing";
		case "reading":
			return "reading";
		case "running":
			return "running";
		case "waiting":
			return "waiting";
		default:
			return "idle";
	}
}

function getDeskPosition(seatIndex: number): { x: number; y: number } {
	const col = seatIndex % DESKS_PER_ROW;
	const row = Math.floor(seatIndex / DESKS_PER_ROW) % MAX_DESK_ROWS;
	return {
		x: DESK_START_X + col * DESK_SPACING_X,
		y: DESK_START_Y + row * DESK_SPACING_Y,
	};
}

// ── Per-agent drawing helpers ─────────────────────────────────

function drawActivityGlow(
	ctx: CanvasRenderingContext2D,
	cx: number,
	cy: number,
	color: string,
	isWaiting: boolean,
	z: number,
	frame: number,
) {
	const pulse = isWaiting
		? 0.18 + Math.sin(frame * 0.07) * 0.1
		: 0.22 + Math.sin(frame * 0.18) * 0.08;
	ctx.save();
	ctx.globalAlpha = pulse;
	const grad = ctx.createRadialGradient(
		cx + 8 * z,
		cy + 20 * z,
		0,
		cx + 8 * z,
		cy + 20 * z,
		16 * z,
	);
	grad.addColorStop(0, color);
	grad.addColorStop(1, "transparent");
	ctx.fillStyle = grad;
	ctx.beginPath();
	ctx.ellipse(cx + 8 * z, cy + 22 * z, 14 * z, 6 * z, 0, 0, Math.PI * 2);
	ctx.fill();
	ctx.restore();
}

function drawMonitorGlow(
	ctx: CanvasRenderingContext2D,
	dx: number,
	dy: number,
	color: string,
	z: number,
	frame: number,
) {
	ctx.save();
	ctx.globalAlpha = 0.25 + Math.sin(frame * 0.22) * 0.12;
	ctx.fillStyle = color;
	ctx.beginPath();
	ctx.roundRect(dx + 10 * z, dy, 12 * z, 5 * z, 2);
	ctx.fill();
	ctx.restore();
}

interface LabelOpts {
	ctx: CanvasRenderingContext2D;
	agent: PixelAgent;
	cx: number;
	cy: number;
	color: string;
	isIdle: boolean;
	isSelected: boolean;
	z: number;
}

/** Wrap text by measuring real pixel widths with ctx.measureText. */
function measureWrap(
	ctx: CanvasRenderingContext2D,
	text: string,
	maxW: number,
): string[] {
	const words = text.split(" ");
	const lines: string[] = [];
	let current = "";

	for (const word of words) {
		const candidate = current ? `${current} ${word}` : word;
		if (ctx.measureText(candidate).width <= maxW) {
			current = candidate;
		} else {
			if (current) lines.push(current);
			// If a single word is wider than maxW, hard-truncate it
			current =
				ctx.measureText(word).width <= maxW
					? word
					: word.slice(
							0,
							Math.max(
								3,
								Math.floor((word.length * maxW) / ctx.measureText(word).width),
							),
						);
		}
	}
	if (current) lines.push(current);
	return lines;
}

function drawAgentLabel({
	ctx,
	agent,
	cx,
	cy,
	color,
	isIdle,
	isSelected,
	z,
}: LabelOpts) {
	let labelColor: string;
	if (isSelected) labelColor = "#FFD700";
	else if (isIdle) labelColor = "#808080";
	else labelColor = color;

	const name = agent.fullName; // full untruncated name
	const fontSize = Math.max(4, 6 * z);
	ctx.fillStyle = labelColor;
	ctx.font = `bold ${fontSize}px Arial, sans-serif`;
	ctx.textAlign = "center";

	const cx8 = cx + 8 * z;
	const lineY = cy + (SPRITE_H + 4) * z;
	const lineH = fontSize + 2;
	const maxW = 36 * z; // slightly wider than desk (32px) for readability

	const lines = measureWrap(ctx, name, maxW).slice(0, 3);
	for (let i = 0; i < lines.length; i++) {
		ctx.fillText(lines[i], cx8, lineY + i * lineH);
	}

	ctx.textAlign = "start";
}

interface DrawAgentOpts {
	ctx: CanvasRenderingContext2D;
	agent: PixelAgent;
	dx: number;
	dy: number;
	z: number;
	selected: string | null;
	animFrame: number;
	frame: number;
}

function drawAgent({
	ctx,
	agent,
	dx,
	dy,
	z,
	selected,
	animFrame,
	frame,
}: DrawAgentOpts) {
	const visual = getAgentVisual(agent.activity, frame, z);
	const { color, isActive, isWaiting, isIdle, bounceY } = visual;

	const cx = dx + 8 * z;
	const cy = dy + CHAR_OFFSET_Y * TILE_SIZE * z + bounceY;
	const isSelected = agent.id === selected;

	if (isIdle) ctx.globalAlpha = 0.55;

	if (isActive || isWaiting)
		drawActivityGlow(ctx, cx, cy, color, isWaiting, z, frame);
	if (isActive) drawMonitorGlow(ctx, dx, dy, color, z, frame);

	// Selection ring
	if (isSelected) {
		ctx.save();
		ctx.globalAlpha = 1;
		const sprite = getCharacterSprite(
			agent.characterIndex,
			activityToDirection(agent.activity),
			animFrame,
		);
		ctx.strokeStyle = "#FFD700";
		ctx.lineWidth = 2;
		ctx.setLineDash([4, 2]);
		ctx.strokeRect(
			cx - 2 * z,
			cy - 2 * z,
			(sprite.width + 4) * z,
			(sprite.height + 4) * z,
		);
		ctx.setLineDash([]);
		ctx.restore();
	}

	// Character sprite
	const sprite = getCharacterSprite(
		agent.characterIndex,
		activityToDirection(agent.activity),
		animFrame,
	);
	ctx.drawImage(sprite, cx, cy, sprite.width * z, sprite.height * z);
	ctx.globalAlpha = 1;

	// Claude mode orange aura
	if (agent.isClaudeMode) {
		ctx.save();
		ctx.globalAlpha = 0.15 + Math.sin(frame * 0.1) * 0.1;
		ctx.fillStyle = "#D97706";
		ctx.beginPath();
		ctx.arc(cx + 8 * z, cy + 12 * z, 14 * z, 0, Math.PI * 2);
		ctx.fill();
		ctx.restore();
	}

	// Activity icon above head
	if (!isIdle) {
		const icon = getActivityIcon(activityToIcon(agent.activity), animFrame);
		ctx.drawImage(icon, cx + 2 * z, cy - 14 * z, 12 * z, 12 * z);
	}

	drawAgentLabel({ ctx, agent, cx, cy, color, isIdle, isSelected, z });

	// Speech bubble
	const bubbleText = agent.speechBubble ?? (isWaiting ? "💬 ..." : null);
	if (bubbleText) drawSpeechBubble(ctx, cx + 8 * z, cy - 16 * z, bubbleText, z);
}

// ── Background drawing helpers ────────────────────────────────

function drawFloor(ctx: CanvasRenderingContext2D, z: number) {
	const tile = getFloorTile();
	for (let row = 0; row < OFFICE_ROWS; row++) {
		for (let col = 0; col < OFFICE_COLS; col++) {
			ctx.drawImage(
				tile,
				col * TILE_SIZE * z,
				row * TILE_SIZE * z,
				TILE_SIZE * z,
				TILE_SIZE * z,
			);
		}
	}
}

function drawWalls(ctx: CanvasRenderingContext2D, z: number) {
	const tile = getWallTile();
	for (let col = 0; col < OFFICE_COLS; col++) {
		ctx.drawImage(tile, col * TILE_SIZE * z, 0, TILE_SIZE * z, TILE_SIZE * z);
	}
	for (let row = 0; row < OFFICE_ROWS; row++) {
		ctx.drawImage(tile, 0, row * TILE_SIZE * z, TILE_SIZE * z, TILE_SIZE * z);
	}
}

function drawDecorations(ctx: CanvasRenderingContext2D, z: number) {
	// Water cooler
	const wcX = (OFFICE_COLS - 3) * TILE_SIZE * z;
	const wcY = (OFFICE_ROWS - 3) * TILE_SIZE * z;
	ctx.fillStyle = "#4A90D9";
	ctx.fillRect(wcX, wcY, 8 * z, 12 * z);
	ctx.fillStyle = "#87CEEB";
	ctx.fillRect(wcX + z, wcY + z, 6 * z, 4 * z);

	// Plant
	const plX = 2 * TILE_SIZE * z;
	const plY = (OFFICE_ROWS - 2) * TILE_SIZE * z;
	ctx.fillStyle = "#27AE60";
	ctx.fillRect(plX + 2 * z, plY - 4 * z, 4 * z, 4 * z);
	ctx.fillRect(plX + z, plY - 6 * z, 6 * z, 2 * z);
	ctx.fillStyle = "#8B4513";
	ctx.fillRect(plX + 2 * z, plY, 4 * z, 4 * z);
}

// ── Component ────────────────────────────────────────────────

interface PixelOfficeCanvasProps {
	readonly width: number;
	readonly height: number;
	readonly onAgentClick?: (
		agentId: string,
		screenX: number,
		screenY: number,
	) => void;
}

export function PixelOfficeCanvas({
	width,
	height,
	onAgentClick,
}: PixelOfficeCanvasProps) {
	const canvasRef = useRef<HTMLCanvasElement>(null);
	const frameRef = useRef(0);
	const animFrameRef = useRef<number>(0);
	const lastTimeRef = useRef(0);

	const agents = usePixelOfficeStore((s) => s.agents);
	const selectedAgentId = usePixelOfficeStore((s) => s.selectedAgentId);
	const zoom = usePixelOfficeStore((s) => s.settings.zoom);

	const agentsRef = useRef(agents);
	agentsRef.current = agents;
	const selectedRef = useRef(selectedAgentId);
	selectedRef.current = selectedAgentId;
	const zoomRef = useRef(zoom);
	zoomRef.current = zoom;

	// ── Render loop ────────────────────────────────────────

	const render = useCallback((timestamp: number) => {
		const canvas = canvasRef.current;
		if (!canvas) return;
		const ctx = canvas.getContext("2d");
		if (!ctx) return;

		const delta = timestamp - lastTimeRef.current;
		if (delta < 1000 / 30) {
			animFrameRef.current = requestAnimationFrame(render);
			return;
		}
		lastTimeRef.current = timestamp;
		frameRef.current++;

		const z = zoomRef.current;
		const agents = agentsRef.current;
		const selected = selectedRef.current;
		const frame = frameRef.current;

		ctx.imageSmoothingEnabled = false;
		ctx.clearRect(0, 0, canvas.width, canvas.height);

		const officePixelW = OFFICE_COLS * TILE_SIZE * z;
		const officePixelH = OFFICE_ROWS * TILE_SIZE * z;
		const offsetX = Math.max(0, (canvas.width - officePixelW) / 2);
		const offsetY = Math.max(0, (canvas.height - officePixelH) / 2);

		ctx.save();
		ctx.translate(offsetX, offsetY);

		drawFloor(ctx, z);
		drawWalls(ctx, z);

		const deskSprite = getDeskSprite();
		const chairSprite = getChairSprite();
		const deskAgents = agents.filter((a) => a.seatIndex >= 0);
		const totalSeats = Math.max(deskAgents.length, 4);
		const animFrame = Math.floor(frame / 15) % 2;

		for (let i = 0; i < totalSeats; i++) {
			const pos = getDeskPosition(i);
			const dx = pos.x * TILE_SIZE * z;
			const dy = pos.y * TILE_SIZE * z;

			ctx.drawImage(deskSprite, dx, dy, 32 * z, DESK_H * z);
			ctx.drawImage(chairSprite, dx, dy + DESK_H * z, 32 * z, CHAIR_H * z);

			const occupant = agents.find((a) => a.seatIndex === i);
			if (!occupant) {
				ctx.fillStyle = "rgba(255,255,255,0.15)";
				ctx.font = `${Math.max(7, 8 * z)}px "Courier New", monospace`;
				ctx.textAlign = "center";
				ctx.fillText("empty", dx + 16 * z, dy + (DESK_H + 14) * z);
				ctx.textAlign = "start";
				continue;
			}

			drawAgent({
				ctx,
				agent: occupant,
				dx,
				dy,
				z,
				selected,
				animFrame,
				frame,
			});
		}

		drawDecorations(ctx, z);
		ctx.restore();

		animFrameRef.current = requestAnimationFrame(render);
	}, []);

	useEffect(() => {
		animFrameRef.current = requestAnimationFrame(render);
		return () => {
			cancelAnimationFrame(animFrameRef.current);
		};
	}, [render]);

	useEffect(() => {
		const canvas = canvasRef.current;
		if (!canvas) return;
		const dpr = window.devicePixelRatio || 1;
		canvas.width = width * dpr;
		canvas.height = height * dpr;
		canvas.style.width = `${width}px`;
		canvas.style.height = `${height}px`;
		canvas.getContext("2d")?.scale(dpr, dpr);
	}, [width, height]);

	// ── Click handling ─────────────────────────────────────

	const handleClick = useCallback(
		(e: React.MouseEvent<HTMLCanvasElement>) => {
			const canvas = canvasRef.current;
			if (!canvas) return;

			const rect = canvas.getBoundingClientRect();
			const z = zoomRef.current;
			const offsetX = Math.max(
				0,
				(rect.width - OFFICE_COLS * TILE_SIZE * z) / 2,
			);
			const offsetY = Math.max(
				0,
				(rect.height - OFFICE_ROWS * TILE_SIZE * z) / 2,
			);
			const clickX = e.clientX - rect.left - offsetX;
			const clickY = e.clientY - rect.top - offsetY;

			for (const agent of agentsRef.current) {
				const pos = getDeskPosition(agent.seatIndex);
				const deskX = pos.x * TILE_SIZE * z;
				const deskY = pos.y * TILE_SIZE * z;
				const charY = deskY + CHAR_OFFSET_Y * TILE_SIZE * z;
				const hitH = (DESK_H + CHAIR_H) * z + SPRITE_H * z;

				if (
					clickX >= deskX &&
					clickX <= deskX + 32 * z &&
					clickY >= deskY &&
					clickY <= deskY + hitH
				) {
					onAgentClick?.(agent.id, e.clientX - rect.left, charY + offsetY);
					return;
				}
			}
			onAgentClick?.("", 0, 0);
		},
		[onAgentClick],
	);

	return (
		<canvas
			ref={canvasRef}
			onClick={handleClick}
			className="cursor-pointer"
			style={{
				imageRendering: "pixelated",
				width: `${width}px`,
				height: `${height}px`,
			}}
		/>
	);
}
