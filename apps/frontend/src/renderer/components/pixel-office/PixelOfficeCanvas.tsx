/**
 * Pixel Office Canvas — The core rendering engine.
 *
 * Renders a pixel art office with animated characters representing
 * active agent terminals. Uses requestAnimationFrame for smooth 60fps.
 */

import { useRef, useEffect, useCallback } from 'react';
import { usePixelOfficeStore, type AgentActivity } from '../../stores/pixel-office-store';
import {
  getCharacterSprite,
  getDeskSprite,
  getFloorTile,
  getWallTile,
  getActivityIcon,
  drawSpeechBubble,
  TILE_SIZE,
  SPRITE_H,
  type ActivityIcon,
} from './pixel-sprites';

// ── Layout constants ─────────────────────────────────────────

const OFFICE_COLS = 24;
const OFFICE_ROWS = 16;
const DESK_SPACING_X = 5;  // tiles between desk columns
const DESK_SPACING_Y = 4;  // tiles between desk rows
const DESK_START_X = 3;    // first desk column offset
const DESK_START_Y = 3;    // first desk row offset
const DESKS_PER_ROW = 4;
const MAX_DESK_ROWS = 3;

// ── Helpers ──────────────────────────────────────────────────

function getDeskPosition(seatIndex: number): { x: number; y: number } {
  const col = seatIndex % DESKS_PER_ROW;
  const row = Math.floor(seatIndex / DESKS_PER_ROW) % MAX_DESK_ROWS;
  return {
    x: DESK_START_X + col * DESK_SPACING_X,
    y: DESK_START_Y + row * DESK_SPACING_Y,
  };
}

function activityToDirection(activity: AgentActivity): 'down' | 'up' {
  if (activity === 'typing' || activity === 'reading' || activity === 'running') return 'up';
  return 'down';
}

function activityToIcon(activity: AgentActivity): ActivityIcon {
  switch (activity) {
    case 'typing': return 'typing';
    case 'reading': return 'reading';
    case 'running': return 'running';
    case 'waiting': return 'waiting';
    default: return 'idle';
  }
}

// ── Component ────────────────────────────────────────────────

interface PixelOfficeCanvasProps {
  readonly width: number;
  readonly height: number;
  readonly onAgentClick?: (agentId: string) => void;
}

export function PixelOfficeCanvas({ width, height, onAgentClick }: PixelOfficeCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const frameRef = useRef(0);
  const animFrameRef = useRef<number>(0);
  const lastTimeRef = useRef(0);

  const agents = usePixelOfficeStore((s) => s.agents);
  const selectedAgentId = usePixelOfficeStore((s) => s.selectedAgentId);
  const zoom = usePixelOfficeStore((s) => s.settings.zoom);

  // Keep agents in a ref for the render loop to avoid stale closures
  const agentsRef = useRef(agents);
  agentsRef.current = agents;
  const selectedRef = useRef(selectedAgentId);
  selectedRef.current = selectedAgentId;
  const zoomRef = useRef(zoom);
  zoomRef.current = zoom;

  // ── Render function ──────────────────────────────────────

  const render = useCallback((timestamp: number) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Frame timing
    const delta = timestamp - lastTimeRef.current;
    if (delta < 1000 / 30) {
      // Cap at ~30fps for pixel art aesthetic
      animFrameRef.current = requestAnimationFrame(render);
      return;
    }
    lastTimeRef.current = timestamp;
    frameRef.current++;

    const z = zoomRef.current;
    const currentAgents = agentsRef.current;
    const selected = selectedRef.current;

    // Clear
    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Calculate viewport offset to center the office
    const officePixelW = OFFICE_COLS * TILE_SIZE * z;
    const officePixelH = OFFICE_ROWS * TILE_SIZE * z;
    const offsetX = Math.max(0, (canvas.width - officePixelW) / 2);
    const offsetY = Math.max(0, (canvas.height - officePixelH) / 2);

    ctx.save();
    ctx.translate(offsetX, offsetY);

    // ── Draw floor ───────────────────────────────────────
    const floorTile = getFloorTile();
    for (let row = 0; row < OFFICE_ROWS; row++) {
      for (let col = 0; col < OFFICE_COLS; col++) {
        ctx.drawImage(
          floorTile,
          col * TILE_SIZE * z,
          row * TILE_SIZE * z,
          TILE_SIZE * z,
          TILE_SIZE * z
        );
      }
    }

    // ── Draw walls (top + left) ──────────────────────────
    const wallTile = getWallTile();
    for (let col = 0; col < OFFICE_COLS; col++) {
      ctx.drawImage(wallTile, col * TILE_SIZE * z, 0, TILE_SIZE * z, TILE_SIZE * z);
    }
    for (let row = 0; row < OFFICE_ROWS; row++) {
      ctx.drawImage(wallTile, 0, row * TILE_SIZE * z, TILE_SIZE * z, TILE_SIZE * z);
    }

    // ── Draw desks ───────────────────────────────────────
    const deskSprite = getDeskSprite();
    const totalSeats = Math.max(currentAgents.length, 4); // Always show at least 4 desks
    for (let i = 0; i < totalSeats; i++) {
      const pos = getDeskPosition(i);
      const dx = pos.x * TILE_SIZE * z;
      const dy = pos.y * TILE_SIZE * z;
      ctx.drawImage(deskSprite, dx, dy, 32 * z, 24 * z);

      // Empty desk label if no agent
      const occupant = currentAgents.find(a => a.seatIndex === i);
      if (!occupant) {
        ctx.fillStyle = 'rgba(255,255,255,0.15)';
        ctx.font = `${Math.max(8, 9 * z)}px "Courier New", monospace`;
        ctx.textAlign = 'center';
        ctx.fillText('empty', dx + 16 * z, dy + 30 * z);
        ctx.textAlign = 'start';
      }
    }

    // ── Draw agents ──────────────────────────────────────
    const animFrame = Math.floor(frameRef.current / 15) % 2; // Toggle every ~0.5s

    for (const agent of currentAgents) {
      const pos = getDeskPosition(agent.seatIndex);
      // Character sits below desk
      const cx = pos.x * TILE_SIZE * z + 8 * z;
      const cy = (pos.y + 1.5) * TILE_SIZE * z;

      const direction = activityToDirection(agent.activity);
      const sprite = getCharacterSprite(agent.characterIndex, direction, animFrame);

      // Selection highlight
      if (agent.id === selected) {
        ctx.strokeStyle = '#FFD700';
        ctx.lineWidth = 2;
        ctx.setLineDash([4, 2]);
        ctx.strokeRect(
          cx - 2 * z,
          cy - 2 * z,
          (sprite.width + 4) * z,
          (sprite.height + 4) * z
        );
        ctx.setLineDash([]);
      }

      // Draw character sprite
      ctx.drawImage(
        sprite,
        cx,
        cy,
        sprite.width * z,
        sprite.height * z
      );

      // Activity icon above head
      if (agent.activity !== 'idle' && agent.activity !== 'exited') {
        const iconSprite = getActivityIcon(activityToIcon(agent.activity), animFrame);
        ctx.drawImage(
          iconSprite,
          cx + 2 * z,
          cy - 14 * z,
          12 * z,
          12 * z
        );
      }

      // Claude mode glow
      if (agent.isClaudeMode) {
        ctx.save();
        ctx.globalAlpha = 0.15 + Math.sin(frameRef.current * 0.1) * 0.1;
        ctx.fillStyle = '#D97706';
        ctx.beginPath();
        ctx.arc(
          cx + 8 * z,
          cy + 12 * z,
          14 * z,
          0,
          Math.PI * 2
        );
        ctx.fill();
        ctx.restore();
      }

      // Name label
      ctx.fillStyle = agent.id === selected ? '#FFD700' : '#E0E0E0';
      ctx.font = `bold ${Math.max(8, 9 * z)}px "Courier New", monospace`;
      ctx.textAlign = 'center';
      const nameY = cy + (SPRITE_H + 4) * z;
      const displayName = agent.name.length > 12
        ? agent.name.slice(0, 11) + '…'
        : agent.name;
      ctx.fillText(displayName, cx + 8 * z, nameY);
      ctx.textAlign = 'start';

      // Speech bubble
      if (agent.speechBubble) {
        drawSpeechBubble(ctx, cx + 8 * z, cy - 16 * z, agent.speechBubble, z);
      }

      // "Waiting for input" bubble when agent is waiting
      if (agent.activity === 'waiting' && !agent.speechBubble) {
        drawSpeechBubble(ctx, cx + 8 * z, cy - 16 * z, '💬 Waiting...', z);
      }
    }

    // ── Decorative elements ──────────────────────────────

    // Water cooler area
    ctx.fillStyle = '#4A90D9';
    const wcX = (OFFICE_COLS - 3) * TILE_SIZE * z;
    const wcY = (OFFICE_ROWS - 3) * TILE_SIZE * z;
    ctx.fillRect(wcX, wcY, 8 * z, 12 * z);
    ctx.fillStyle = '#87CEEB';
    ctx.fillRect(wcX + 1 * z, wcY + 1 * z, 6 * z, 4 * z);

    // Plant
    ctx.fillStyle = '#27AE60';
    const plX = 2 * TILE_SIZE * z;
    const plY = (OFFICE_ROWS - 2) * TILE_SIZE * z;
    ctx.fillRect(plX + 2 * z, plY - 4 * z, 4 * z, 4 * z);
    ctx.fillRect(plX + 1 * z, plY - 6 * z, 6 * z, 2 * z);
    ctx.fillStyle = '#8B4513';
    ctx.fillRect(plX + 2 * z, plY, 4 * z, 4 * z);

    ctx.restore();

    animFrameRef.current = requestAnimationFrame(render);
  }, []);

  // ── Start/stop render loop ─────────────────────────────

  useEffect(() => {
    animFrameRef.current = requestAnimationFrame(render);
    return () => {
      cancelAnimationFrame(animFrameRef.current);
    };
  }, [render]);

  // ── Handle canvas resize ───────────────────────────────

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.scale(dpr, dpr);
    }
  }, [width, height]);

  // ── Click handling ─────────────────────────────────────

  const handleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const z = zoomRef.current;
    const officePixelW = OFFICE_COLS * TILE_SIZE * z;
    const officePixelH = OFFICE_ROWS * TILE_SIZE * z;
    const offsetX = Math.max(0, (rect.width - officePixelW) / 2);
    const offsetY = Math.max(0, (rect.height - officePixelH) / 2);

    const clickX = e.clientX - rect.left - offsetX;
    const clickY = e.clientY - rect.top - offsetY;

    // Check which agent was clicked
    for (const agent of agentsRef.current) {
      const pos = getDeskPosition(agent.seatIndex);
      const ax = pos.x * TILE_SIZE * z;
      const ay = (pos.y + 1.5) * TILE_SIZE * z;
      const aw = 16 * z;
      const ah = SPRITE_H * z;

      if (clickX >= ax && clickX <= ax + aw && clickY >= ay && clickY <= ay + ah) {
        onAgentClick?.(agent.id);
        return;
      }
    }

    // Clicked empty area — deselect
    onAgentClick?.('');
  }, [onAgentClick]);

  return (
    <canvas
      ref={canvasRef}
      onClick={handleClick}
      className="cursor-pointer"
      style={{
        imageRendering: 'pixelated',
        width: `${width}px`,
        height: `${height}px`,
      }}
    />
  );
}
