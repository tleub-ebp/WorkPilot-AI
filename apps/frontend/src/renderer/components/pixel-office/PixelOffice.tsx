/**
 * Pixel Office — Main component wrapping the canvas + toolbar.
 *
 * Each agent terminal AND active Kanban task appears as a pixel art character.
 * Characters reflect real-time activity (typing, reading, waiting, idle).
 */

import { useEffect, useCallback, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ZoomIn,
  ZoomOut,
  Users,
  Volume2,
  VolumeX,
  Grid3X3,
  LayoutDashboard,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Tooltip, TooltipTrigger, TooltipContent } from '../ui/tooltip';
import { useTerminalStore } from '../../stores/terminal-store';
import { useTaskStore } from '../../stores/task-store';
import { usePixelOfficeStore } from '../../stores/pixel-office-store';
import { PixelOfficeCanvas } from './PixelOfficeCanvas';
import { AgentBubble, AddAgentButton } from './AgentBubble';

interface PixelOfficeProps {
  /** File-system path of the project — used to match terminal sessions */
  readonly projectPath: string;
  /** Project ID (UUID) — used to match Kanban tasks */
  readonly projectId: string;
  readonly onNavigateToTerminals?: () => void;
  readonly onNavigateToKanban?: () => void;
}

export function PixelOffice({ projectPath, projectId, onNavigateToTerminals, onNavigateToKanban }: PixelOfficeProps) {
  useTranslation(['pixelOffice', 'common']);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 });
  const [bubblePos, setBubblePos] = useState<{ x: number; y: number } | null>(null);

  // ── Stores ──────────────────────────────────────────────────

  const terminals      = useTerminalStore((s) => s.terminals);
  const setActiveTerminal = useTerminalStore((s) => s.setActiveTerminal);
  const addTerminal    = useTerminalStore((s) => s.addTerminal);
  const removeTerminal = useTerminalStore((s) => s.removeTerminal);
  const canAddTerminal = useTerminalStore((s) => s.canAddTerminal);

  const tasks     = useTaskStore((s) => s.tasks);
  const selectTask = useTaskStore((s) => s.selectTask);

  const agents          = usePixelOfficeStore((s) => s.agents);
  const selectedAgentId = usePixelOfficeStore((s) => s.selectedAgentId);
  const settings        = usePixelOfficeStore((s) => s.settings);
  const syncAll         = usePixelOfficeStore((s) => s.syncAll);
  const selectAgent     = usePixelOfficeStore((s) => s.selectAgent);
  const updateSettings  = usePixelOfficeStore((s) => s.updateSettings);

  // ── Sync terminals + tasks → pixel agents ───────────────────

  useEffect(() => {
    const projectTerminals = terminals.filter(
      (t) => t.projectPath === projectPath || !t.projectPath
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
        setDimensions({ width: Math.floor(width), height: Math.floor(height) - 52 });
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // ── Bubble handlers ─────────────────────────────────────────

  const handleAgentClick = useCallback(
    (agentId: string, screenX: number, screenY: number) => {
      if (!agentId) { selectAgent(null); setBubblePos(null); return; }
      selectAgent(agentId);
      setBubblePos({ x: screenX, y: screenY });
    },
    [selectAgent]
  );

  const closeBubble = useCallback(() => {
    selectAgent(null);
    setBubblePos(null);
  }, [selectAgent]);

  // ── Terminal agent actions ───────────────────────────────────

  const handleGoToTerminal = useCallback(() => {
    const agent = agents.find(a => a.id === selectedAgentId);
    if (agent?.type !== 'terminal') return;
    setActiveTerminal(selectedAgentId);
    onNavigateToTerminals?.();
    closeBubble();
  }, [agents, selectedAgentId, setActiveTerminal, onNavigateToTerminals, closeBubble]);

  const handleKill = useCallback(async () => {
    if (!selectedAgentId) return;
    closeBubble();
    await globalThis.electronAPI.destroyTerminal(selectedAgentId);
    removeTerminal(selectedAgentId);
  }, [selectedAgentId, removeTerminal, closeBubble]);

  const handleInterrupt = useCallback(() => {
    if (!selectedAgentId) return;
    globalThis.electronAPI.sendTerminalInput(selectedAgentId, '\x03');
  }, [selectedAgentId]);

  const handleResumeClaude = useCallback(() => {
    if (!selectedAgentId) return;
    globalThis.electronAPI.invokeClaudeInTerminal(selectedAgentId);
  }, [selectedAgentId]);

  const handleSendCommand = useCallback((cmd: string) => {
    if (!selectedAgentId) return;
    globalThis.electronAPI.sendTerminalInput(selectedAgentId, cmd + '\n');
  }, [selectedAgentId]);

  // ── Task agent actions ───────────────────────────────────────

  const handleGoToTask = useCallback(() => {
    const agent = agents.find(a => a.id === selectedAgentId);
    if (!agent?.taskId) return;
    selectTask(agent.taskId);
    onNavigateToKanban?.();
    closeBubble();
  }, [agents, selectedAgentId, selectTask, onNavigateToKanban, closeBubble]);

  const handleStopTask = useCallback(() => {
    const agent = agents.find(a => a.id === selectedAgentId);
    if (!agent?.taskId) return;
    globalThis.electronAPI.stopTask(agent.taskId);
    closeBubble();
  }, [agents, selectedAgentId, closeBubble]);

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

  const handleZoomIn  = () => updateSettings({ zoom: Math.min(settings.zoom + 1, 6) });
  const handleZoomOut = () => updateSettings({ zoom: Math.max(settings.zoom - 1, 1) });
  const toggleSound   = () => updateSettings({ soundEnabled: !settings.soundEnabled });
  const toggleGrid    = () => updateSettings({ showGrid: !settings.showGrid });

  // ── Derived state ────────────────────────────────────────────

  const selectedAgent   = agents.find(a => a.id === selectedAgentId);
  const selectedTerminal = selectedAgent?.type === 'terminal'
    ? terminals.find(t => t.id === selectedAgentId)
    : undefined;

  const terminalCount = agents.filter(a => a.type === 'terminal').length;
  const taskCount     = agents.filter(a => a.type === 'task').length;
  const activeCount   = agents.filter(a => a.activity !== 'idle' && a.activity !== 'exited').length;

  return (
    <div ref={containerRef} className="flex flex-col h-full overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-background/80 backdrop-blur-sm shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-base font-bold tracking-tight font-mono">🏢 Pixel Office</span>

          {terminalCount > 0 && (
            <Badge variant="secondary" className="font-mono text-xs gap-1">
              <Users className="h-3 w-3" />
              {terminalCount} terminal{terminalCount > 1 ? 'x' : ''}
            </Badge>
          )}
          {taskCount > 0 && (
            <Badge variant="secondary" className="font-mono text-xs gap-1 border-orange-500/40 text-orange-400">
              <LayoutDashboard className="h-3 w-3" />
              {taskCount} tâche{taskCount > 1 ? 's' : ''}
            </Badge>
          )}
          {activeCount > 0 && (
            <Badge variant="default" className="font-mono text-xs bg-emerald-600">
              {activeCount} actif{activeCount > 1 ? 's' : ''}
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-1">
          <AddAgentButton onClick={handleAddAgent} disabled={!canAddTerminal(projectPath)} />
          <div className="w-px h-5 bg-border mx-1" />

          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleZoomOut}>
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
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleZoomIn}>
                <ZoomIn className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Zoom In</TooltipContent>
          </Tooltip>

          <div className="w-px h-5 bg-border mx-1" />

          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={toggleGrid}>
                <Grid3X3 className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Toggle Grid</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={toggleSound}>
                {settings.soundEnabled ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
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
            <h2 className="text-xl font-bold text-white/80 font-mono">Votre bureau est vide</h2>
            <p className="text-sm text-white/50 max-w-md">
              Démarrez une tâche dans le Kanban ou ouvrez des terminaux pour voir vos agents IA
              apparaître à leurs bureaux avec un suivi d'activité en direct.
            </p>
            <AddAgentButton onClick={handleAddAgent} disabled={!canAddTerminal(projectPath)} />
          </div>
        ) : (
          <>
            <PixelOfficeCanvas
              width={dimensions.width}
              height={dimensions.height}
              onAgentClick={handleAgentClick}
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
