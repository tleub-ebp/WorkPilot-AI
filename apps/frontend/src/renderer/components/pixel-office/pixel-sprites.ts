/**
 * Pixel Art Sprite System for Pixel Office
 *
 * Generates pixel art characters and office furniture using canvas drawing.
 * No external assets needed — everything is procedurally generated.
 */

// ── Color Palettes for 6 diverse characters ──────────────────

export const CHARACTER_PALETTES = [
	{
		skin: "#F5D0A9",
		hair: "#3B2314",
		shirt: "#4A90D9",
		pants: "#2C3E50",
		shoes: "#1A1A2E",
	},
	{
		skin: "#8D5524",
		hair: "#1A1A1A",
		shirt: "#E74C3C",
		pants: "#34495E",
		shoes: "#2C2C3E",
	},
	{
		skin: "#FFDBB4",
		hair: "#D4A017",
		shirt: "#27AE60",
		pants: "#2C3E50",
		shoes: "#1A1A2E",
	},
	{
		skin: "#C68642",
		hair: "#2C1810",
		shirt: "#9B59B6",
		pants: "#2C3E50",
		shoes: "#1A1A2E",
	},
	{
		skin: "#F1C27D",
		hair: "#6B3A2A",
		shirt: "#F39C12",
		pants: "#34495E",
		shoes: "#2C2C3E",
	},
	{
		skin: "#FFDBAC",
		hair: "#8B4513",
		shirt: "#1ABC9C",
		pants: "#2C3E50",
		shoes: "#1A1A2E",
	},
];

export const TILE_SIZE = 16;
export const SPRITE_W = 16;
export const SPRITE_H = 24;
export const DESK_H = 14; // Desk sprite height (compact, no tall legs)
export const CHAIR_H = 6; // Chair sprite height

// ── Character sprite frames ──────────────────────────────────

type Direction = "down" | "up" | "left" | "right";

interface SpritePixel {
	x: number;
	y: number;
	color: string;
}

function getCharacterPixels(
	palette: (typeof CHARACTER_PALETTES)[0],
	direction: Direction,
	frame: number,
): SpritePixel[] {
	const pixels: SpritePixel[] = [];
	const { skin, hair, shirt, pants, shoes } = palette;

	// Head (rows 2-7)
	// Hair top
	for (let x = 5; x <= 10; x++) pixels.push({ x, y: 2, color: hair });
	for (let x = 4; x <= 11; x++) pixels.push({ x, y: 3, color: hair });

	// Face
	if (direction === "down" || direction === "left" || direction === "right") {
		for (let x = 4; x <= 11; x++) pixels.push({ x, y: 4, color: skin });
		for (let x = 4; x <= 11; x++) pixels.push({ x, y: 5, color: skin });
		// Eyes
		if (direction === "down") {
			pixels.push(
				{ x: 6, y: 5, color: "#1A1A2E" },
				{ x: 9, y: 5, color: "#1A1A2E" },
			);
		} else if (direction === "left") {
			pixels.push(
				{ x: 5, y: 5, color: "#1A1A2E" },
				{ x: 8, y: 5, color: "#1A1A2E" },
			);
		} else {
			pixels.push(
				{ x: 7, y: 5, color: "#1A1A2E" },
				{ x: 10, y: 5, color: "#1A1A2E" },
			);
		}
		for (let x = 5; x <= 10; x++) pixels.push({ x, y: 6, color: skin });
		for (let x = 6; x <= 9; x++) pixels.push({ x, y: 7, color: skin });
	} else {
		// Back of head
		for (let x = 4; x <= 11; x++) pixels.push({ x, y: 4, color: hair });
		for (let x = 4; x <= 11; x++) pixels.push({ x, y: 5, color: hair });
		for (let x = 5; x <= 10; x++) pixels.push({ x, y: 6, color: hair });
		for (let x = 6; x <= 9; x++) pixels.push({ x, y: 7, color: skin });
	}

	// Body / shirt (rows 8-13)
	for (let y = 8; y <= 13; y++) {
		const w = y <= 9 ? 3 : 4;
		for (let x = 8 - w; x <= 7 + w; x++) {
			pixels.push({ x, y, color: shirt });
		}
	}

	// Arms animation
	const armOffset = frame % 2 === 0 ? 0 : 1;
	pixels.push(
		{ x: 3, y: 9 + armOffset, color: skin },
		{ x: 12, y: 9 + (armOffset === 0 ? 1 : 0), color: skin },
	);

	// Pants (rows 14-17)
	for (let y = 14; y <= 17; y++) {
		for (let x = 5; x <= 10; x++) {
			pixels.push({ x, y, color: pants });
		}
	}

	// Walking leg animation
	const legSpread = frame % 2 === 0 ? 0 : 1;
	// Shoes (rows 18-19)
	for (let x = 5 - legSpread; x <= 7; x++)
		pixels.push({ x, y: 18, color: shoes });
	for (let x = 8; x <= 10 + legSpread; x++)
		pixels.push({ x, y: 18, color: shoes });

	return pixels;
}

// ── Sprite caching ───────────────────────────────────────────

const spriteCache = new Map<string, HTMLCanvasElement>();

export function getCharacterSprite(
	characterIndex: number,
	direction: Direction,
	frame: number,
): HTMLCanvasElement {
	const key = `char-${characterIndex}-${direction}-${frame}`;
	const cached = spriteCache.get(key);
	if (cached) return cached;

	const canvas = document.createElement("canvas");
	canvas.width = SPRITE_W;
	canvas.height = SPRITE_H;
	const ctx = canvas.getContext("2d");
	if (!ctx) throw new Error("Could not get 2D context");

	const palette =
		CHARACTER_PALETTES[characterIndex % CHARACTER_PALETTES.length];
	const pixels = getCharacterPixels(palette, direction, frame);

	for (const { x, y, color } of pixels) {
		ctx.fillStyle = color;
		ctx.fillRect(x, y, 1, 1);
	}

	spriteCache.set(key, canvas);
	return canvas;
}

// ── Desk sprite (compact top-view, no tall legs) ─────────────

export function getDeskSprite(): HTMLCanvasElement {
	const key = "desk-v2";
	const cached = spriteCache.get(key);
	if (cached) return cached;

	const canvas = document.createElement("canvas");
	canvas.width = 32;
	canvas.height = DESK_H; // 14px
	const ctx = canvas.getContext("2d");
	if (!ctx) throw new Error("Could not get 2D context");

	// Table top surface (seen from slight angle)
	ctx.fillStyle = "#C4922E"; // top highlight
	ctx.fillRect(0, 0, 32, 1);
	ctx.fillStyle = "#A07828"; // main surface
	ctx.fillRect(0, 1, 32, 5);
	// Front face of table (depth illusion)
	ctx.fillStyle = "#7A5A10";
	ctx.fillRect(0, 6, 32, 4);
	// Bottom shadow
	ctx.fillStyle = "#5A4208";
	ctx.fillRect(0, 10, 32, 2);
	// Short side supports (visible below table)
	ctx.fillStyle = "#6B5310";
	ctx.fillRect(2, 10, 2, 4);
	ctx.fillRect(28, 10, 2, 4);

	// Monitor body
	ctx.fillStyle = "#1E1E30";
	ctx.fillRect(11, 0, 10, 5);
	// Screen glow
	ctx.fillStyle = "#1A5FD4";
	ctx.fillRect(12, 0, 8, 4);
	// Screen content lines
	ctx.fillStyle = "#5DB8FF";
	ctx.fillRect(13, 1, 5, 1);
	ctx.fillStyle = "#4488CC";
	ctx.fillRect(13, 3, 3, 1);

	// Keyboard on surface
	ctx.fillStyle = "#484848";
	ctx.fillRect(5, 2, 9, 2);
	ctx.fillStyle = "#666";
	for (let i = 0; i < 4; i++) {
		ctx.fillRect(6 + i * 2, 2, 1, 1);
	}

	// Mouse
	ctx.fillStyle = "#888";
	ctx.fillRect(16, 2, 3, 2);
	ctx.fillStyle = "#AAA";
	ctx.fillRect(17, 2, 1, 1);

	spriteCache.set(key, canvas);
	return canvas;
}

// ── Chair sprite ──────────────────────────────────────────────

export function getChairSprite(): HTMLCanvasElement {
	const key = "chair";
	const cached = spriteCache.get(key);
	if (cached) return cached;

	const canvas = document.createElement("canvas");
	canvas.width = 32;
	canvas.height = CHAIR_H; // 6px
	const ctx = canvas.getContext("2d");
	if (!ctx) throw new Error("Could not get 2D context");

	// Chair seat
	ctx.fillStyle = "#2A2A4E";
	ctx.fillRect(7, 0, 18, 4);
	// Seat highlight
	ctx.fillStyle = "#3A3A6E";
	ctx.fillRect(7, 0, 18, 1);
	// Seat front edge
	ctx.fillStyle = "#1A1A3A";
	ctx.fillRect(7, 4, 18, 2);
	// Chair legs (tiny)
	ctx.fillStyle = "#555";
	ctx.fillRect(8, 4, 2, 2);
	ctx.fillRect(22, 4, 2, 2);

	spriteCache.set(key, canvas);
	return canvas;
}

// ── Floor tile sprite ────────────────────────────────────────

export function getFloorTile(): HTMLCanvasElement {
	const key = "floor";
	const cached = spriteCache.get(key);
	if (cached) return cached;

	const canvas = document.createElement("canvas");
	canvas.width = TILE_SIZE;
	canvas.height = TILE_SIZE;
	const ctx = canvas.getContext("2d");
	if (!ctx) throw new Error("Could not get 2D context");

	ctx.fillStyle = "#2A2A3A";
	ctx.fillRect(0, 0, TILE_SIZE, TILE_SIZE);

	// Subtle tile pattern
	ctx.fillStyle = "#252535";
	ctx.fillRect(0, 0, 8, 8);
	ctx.fillRect(8, 8, 8, 8);

	// Grid line
	ctx.strokeStyle = "rgba(255,255,255,0.04)";
	ctx.strokeRect(0.5, 0.5, TILE_SIZE - 1, TILE_SIZE - 1);

	spriteCache.set(key, canvas);
	return canvas;
}

// ── Wall tile sprite ─────────────────────────────────────────

export function getWallTile(): HTMLCanvasElement {
	const key = "wall";
	const cached = spriteCache.get(key);
	if (cached) return cached;

	const canvas = document.createElement("canvas");
	canvas.width = TILE_SIZE;
	canvas.height = TILE_SIZE;
	const ctx = canvas.getContext("2d");
	if (!ctx) throw new Error("Could not get 2D context");

	ctx.fillStyle = "#3D3D50";
	ctx.fillRect(0, 0, TILE_SIZE, TILE_SIZE);

	// Brick pattern
	ctx.strokeStyle = "#35354A";
	ctx.lineWidth = 1;
	ctx.strokeRect(0, 0, TILE_SIZE, 8);
	ctx.beginPath();
	ctx.moveTo(8, 0);
	ctx.lineTo(8, 8);
	ctx.stroke();
	ctx.strokeRect(0, 8, TILE_SIZE, 8);
	ctx.beginPath();
	ctx.moveTo(0, 8);
	ctx.lineTo(0, 16);
	ctx.moveTo(TILE_SIZE, 8);
	ctx.lineTo(TILE_SIZE, 16);
	ctx.stroke();

	spriteCache.set(key, canvas);
	return canvas;
}

// ── Activity indicator sprites ───────────────────────────────

export type ActivityIcon =
	| "typing"
	| "reading"
	| "running"
	| "waiting"
	| "idle";

export function getActivityIcon(
	activity: ActivityIcon,
	frame: number,
): HTMLCanvasElement {
	const key = `activity-${activity}-${frame % 2}`;
	const cached = spriteCache.get(key);
	if (cached) return cached;

	const canvas = document.createElement("canvas");
	canvas.width = 12;
	canvas.height = 12;
	const ctx = canvas.getContext("2d");
	if (!ctx) throw new Error("Could not get 2D context");

	switch (activity) {
		case "typing": {
			// Keyboard icon with blinking cursor
			ctx.fillStyle = "#4A90D9";
			ctx.fillRect(1, 4, 10, 6);
			ctx.fillStyle = "#FFF";
			for (let i = 0; i < 3; i++) {
				for (let j = 0; j < 4; j++) {
					ctx.fillRect(2 + j * 2, 5 + i * 2, 1, 1);
				}
			}
			if (frame % 2 === 0) {
				ctx.fillStyle = "#FFD700";
				ctx.fillRect(9, 2, 2, 2);
			}
			break;
		}
		case "reading": {
			// Book icon
			ctx.fillStyle = "#27AE60";
			ctx.fillRect(2, 2, 8, 8);
			ctx.fillStyle = "#FFF";
			ctx.fillRect(3, 3, 6, 1);
			ctx.fillRect(3, 5, 4, 1);
			ctx.fillRect(3, 7, 5, 1);
			break;
		}
		case "running": {
			// Terminal/command icon
			ctx.fillStyle = "#1ABC9C";
			ctx.fillRect(1, 2, 10, 8);
			ctx.fillStyle = "#0D0D1A";
			ctx.fillRect(2, 3, 8, 6);
			ctx.fillStyle = "#27AE60";
			ctx.fillRect(3, 4, 1, 1);
			ctx.fillRect(4, 5, 3 + (frame % 2), 1);
			break;
		}
		case "waiting": {
			// Hourglass / thinking dots
			ctx.fillStyle = "#F39C12";
			const dotOffset = frame % 2;
			ctx.fillRect(3, 5 + dotOffset, 2, 2);
			ctx.fillRect(6, 5 - dotOffset, 2, 2);
			ctx.fillRect(9, 5 + dotOffset, 2, 2);
			break;
		}
		default: {
			// Zzz for idle
			ctx.fillStyle = "rgba(255,255,255,0.5)";
			ctx.font = "8px monospace";
			ctx.fillText("z", 3, 8);
			if (frame % 2 === 0) {
				ctx.fillText("z", 7, 5);
			}
			break;
		}
	}

	spriteCache.set(key, canvas);
	return canvas;
}

// ── Speech bubble drawing ────────────────────────────────────

export function drawSpeechBubble(
	ctx: CanvasRenderingContext2D,
	x: number,
	y: number,
	text: string,
	zoom: number,
) {
	const fontSize = Math.max(8, Math.round(10 / zoom));
	ctx.font = `${fontSize}px "Courier New", monospace`;
	const metrics = ctx.measureText(text);
	const padding = 4;
	const w = metrics.width + padding * 2;
	const h = fontSize + padding * 2;
	const bx = x - w / 2;
	const by = y - h - 6;

	// Bubble background
	ctx.fillStyle = "rgba(255, 255, 255, 0.95)";
	ctx.beginPath();
	ctx.roundRect(bx, by, w, h, 3);
	ctx.fill();

	// Bubble border
	ctx.strokeStyle = "rgba(0, 0, 0, 0.2)";
	ctx.lineWidth = 1;
	ctx.stroke();

	// Pointer triangle
	ctx.fillStyle = "rgba(255, 255, 255, 0.95)";
	ctx.beginPath();
	ctx.moveTo(x - 3, by + h);
	ctx.lineTo(x, by + h + 4);
	ctx.lineTo(x + 3, by + h);
	ctx.fill();

	// Text
	ctx.fillStyle = "#1A1A2E";
	ctx.textAlign = "center";
	ctx.textBaseline = "middle";
	ctx.fillText(text, x, by + h / 2);
	ctx.textAlign = "start";
	ctx.textBaseline = "alphabetic";
}
