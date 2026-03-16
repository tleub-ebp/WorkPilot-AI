/**
 * Pixel Office — Main component wrapping the canvas + toolbar.
 *
 * Inspired by pixel-agents (https://github.com/pablodelucca/pixel-agents).
 * Each agent terminal becomes a pixel art character in an animated office.
 * Characters reflect real-time agent activity (typing, reading, waiting, idle).
 */

import { useEffect, useCallback, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ZoomIn,
  ZoomOut,
  Users,
  Volume2,
  VolumeX,
  Maximize2,
  Grid3X3,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Tooltip, TooltipTrigger, TooltipContent } from '../ui/tooltip';
import { useTerminalStore } from '../../stores/terminal-store';
import { usePixelOfficeStore } from '../../stores/pixel-office-store';
import { PixelOfficeCanvas } from './PixelOfficeCanvas';

function getActivityColor(activity: string): string {
  const colors: Record<string, string> = {
    typing: '#4A90D9',
    running: '#1ABC9C',
    waiting: '#F39C12',
    reading: '#27AE60',
    exited: '#E74C3C',
  };
  return colors[activity] || '#6B7280';
}

interface PixelOfficeProps {
  readonly projectId: string;
}

export function PixelOffice({ projectId }: PixelOfficeProps) {
  useTranslation(['pixelOffice', 'common']);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 });

  // Terminal store — source of truth for agents
  const terminals = useTerminalStore((s) => s.terminals);
  const setActiveTerminal = useTerminalStore((s) => s.setActiveTerminal);

  // Pixel office store
  const agents = usePixelOfficeStore((s) => s.agents);
  const selectedAgentId = usePixelOfficeStore((s) => s.selectedAgentId);
  const settings = usePixelOfficeStore((s) => s.settings);
  const syncFromTerminals = usePixelOfficeStore((s) => s.syncFromTerminals);
  const selectAgent = usePixelOfficeStore((s) => s.selectAgent);
  const updateSettings = usePixelOfficeStore((s) => s.updateSettings);

  // Sync terminals → pixel agents
  useEffect(() => {
    const projectTerminals = terminals.filter(
      (t) => t.projectPath === projectId || !t.projectPath
    );
    syncFromTerminals(projectTerminals);
  }, [terminals, projectId, syncFromTerminals]);

  // Measure container
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        setDimensions({ width: Math.floor(width), height: Math.floor(height) - 60 });
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Handle agent click → select + switch terminal
  const handleAgentClick = useCallback(
    (agentId: string) => {
      if (!agentId) {
        selectAgent(null);
        return;
      }
      selectAgent(agentId);
    },
    [selectAgent]
  );

  // Double-click to jump to terminal
  const handleGoToTerminal = useCallback(() => {
    if (selectedAgentId) {
      setActiveTerminal(selectedAgentId);
    }
  }, [selectedAgentId, setActiveTerminal]);

  const handleZoomIn = () => updateSettings({ zoom: Math.min(settings.zoom + 1, 6) });
  const handleZoomOut = () => updateSettings({ zoom: Math.max(settings.zoom - 1, 1) });
  const toggleSound = () => updateSettings({ soundEnabled: !settings.soundEnabled });
  const toggleGrid = () => updateSettings({ showGrid: !settings.showGrid });

  const selectedAgent = agents.find((a) => a.id === selectedAgentId);
  const activeCount = agents.filter((a) => a.activity !== 'idle' && a.activity !== 'exited').length;

  return (
    <div ref={containerRef} className="flex flex-col h-full overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-background/80 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold tracking-tight" style={{ fontFamily: '"Courier New", monospace' }}>
              🏢 Pixel Office
            </span>
            <Badge variant="secondary" className="font-mono text-xs">
              <Users className="h-3 w-3 mr-1" />
              {agents.length} {agents.length === 1 ? 'agent' : 'agents'}
            </Badge>
            {activeCount > 0 && (
              <Badge variant="default" className="font-mono text-xs bg-emerald-600">
                {activeCount} active
              </Badge>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1">
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
            <h2 className="text-xl font-bold text-white/80" style={{ fontFamily: '"Courier New", monospace' }}>
              Your office is empty
            </h2>
            <p className="text-sm text-white/50 max-w-md">
              Open agent terminals to see your AI workers appear at their desks.
              Each terminal becomes a character with live activity tracking.
            </p>
          </div>
        ) : (
          <PixelOfficeCanvas
            width={dimensions.width}
            height={dimensions.height}
            onAgentClick={handleAgentClick}
          />
        )}
      </div>

      {/* Agent detail panel (bottom strip) */}
      {selectedAgent && (
        <div className="border-t border-border bg-background/95 backdrop-blur-sm px-4 py-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: getActivityColor(selectedAgent.activity) }}
                />
                <span className="font-mono font-bold text-sm">{selectedAgent.name}</span>
              </div>
              <Badge variant="outline" className="font-mono text-xs capitalize">
                {selectedAgent.activity}
              </Badge>
              {selectedAgent.isClaudeMode && (
                <Badge variant="secondary" className="font-mono text-xs">
                  Claude Mode
                </Badge>
              )}
              {selectedAgent.taskName && (
                <Badge variant="outline" className="font-mono text-xs">
                  📋 {selectedAgent.taskName}
                </Badge>
              )}
            </div>
            <Button variant="outline" size="sm" onClick={handleGoToTerminal}>
              <Maximize2 className="h-3.5 w-3.5 mr-1.5" />
              Go to Terminal
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
