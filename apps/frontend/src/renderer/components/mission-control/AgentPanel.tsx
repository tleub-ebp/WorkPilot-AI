/**
 * AgentPanel — Individual agent card in the Mission Control grid.
 *
 * Shows: status badge, provider/model, progress bar, live thinking,
 * last tool call, active files, token usage, and control buttons.
 */

import { useState } from 'react';
import {
  Play,
  Pause,
  Square,
  Trash2,
  MoreVertical,
  GitBranch,
  FileCode,
  Cpu,
  DollarSign,
  Clock,
  Brain,
  Wrench,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Card, CardContent } from '../ui/card';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { cn } from '../../lib/utils';
import type { AgentSlot } from '../../stores/mission-control-store';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../ui/dropdown-menu';

interface AgentPanelProps {
  readonly agent: AgentSlot;
  readonly isSelected: boolean;
  readonly onSelect: () => void;
  readonly onStart: (task: string) => void;
  readonly onPause: () => void;
  readonly onResume: () => void;
  readonly onStop: () => void;
  readonly onRemove: () => void;
  readonly onShowDecisionTree: () => void;
  readonly onUpdateConfig: (config: Partial<{ provider: string; model: string; model_label: string; name: string; role: string }>) => void;
}

const STATUS_COLORS: Record<string, string> = {
  idle: 'bg-gray-500/10 text-gray-500 border-gray-500/30',
  running: 'bg-green-500/10 text-green-500 border-green-500/30',
  paused: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/30',
  completed: 'bg-blue-500/10 text-blue-500 border-blue-500/30',
  error: 'bg-red-500/10 text-red-500 border-red-500/30',
  waiting: 'bg-purple-500/10 text-purple-500 border-purple-500/30',
};

const STATUS_DOT: Record<string, string> = {
  idle: 'bg-gray-500',
  running: 'bg-green-500 animate-pulse',
  paused: 'bg-yellow-500',
  completed: 'bg-blue-500',
  error: 'bg-red-500',
  waiting: 'bg-purple-500 animate-pulse',
};

const ROLE_LABELS: Record<string, string> = {
  architect: '🏗️ Architect',
  coder: '💻 Coder',
  tester: '🧪 Tester',
  reviewer: '👁️ Reviewer',
  documenter: '📝 Documenter',
  planner: '📋 Planner',
  debugger: '🐛 Debugger',
  custom: '⚙️ Custom',
};

export function AgentPanel({
  agent,
  isSelected,
  onSelect,
  onStart,
  onPause,
  onResume,
  onStop,
  onRemove,
  onShowDecisionTree,
  // biome-ignore lint/correctness/noUnusedFunctionParameters: parameter kept for API compatibility
  onUpdateConfig,
}: AgentPanelProps) {
  const [taskInput, setTaskInput] = useState('');

  const statusColor = STATUS_COLORS[agent.status] ?? STATUS_COLORS.idle;
  const statusDot = STATUS_DOT[agent.status] ?? STATUS_DOT.idle;

  return (
    <Card
      className={cn(
        'border transition-all duration-200 cursor-pointer hover:shadow-md',
        isSelected
          ? 'border-primary/50 shadow-lg shadow-primary/5 ring-1 ring-primary/20'
          : 'border-border/50 hover:border-border',
      )}
      onClick={onSelect}
    >
      <CardContent className="p-3 space-y-3">
        {/* Header: Name + Status + Menu */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className={cn('h-2 w-2 rounded-full shrink-0', statusDot)} />
            <span className="font-semibold text-sm truncate">{agent.name}</span>
            <Badge variant="outline" className={cn('text-[10px] px-1.5 py-0', statusColor)}>
              {agent.status}
            </Badge>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-6 w-6 shrink-0" onClick={(e) => e.stopPropagation()}>
                <MoreVertical className="h-3.5 w-3.5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-44">
              <DropdownMenuItem onClick={onShowDecisionTree}>
                <GitBranch className="h-3.5 w-3.5 mr-2" />
                Decision Tree
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={onRemove} className="text-destructive">
                <Trash2 className="h-3.5 w-3.5 mr-2" />
                Remove
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {/* Role + Provider/Model */}
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>{ROLE_LABELS[agent.role] ?? agent.role}</span>
          <span className="text-border">•</span>
          <span className="truncate">
            {agent.provider ? `${agent.provider}:` : ''}
            {agent.model_label || agent.model || 'No model'}
          </span>
        </div>

        {/* Progress */}
        {agent.status === 'running' && (
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground truncate">{agent.current_step || agent.current_task || 'Working...'}</span>
              <span className="text-muted-foreground shrink-0">{Math.round(agent.progress * 100)}%</span>
            </div>
            <Progress value={agent.progress * 100} className="h-1.5" />
          </div>
        )}

        {/* Live Thinking */}
        {agent.current_thinking && agent.status === 'running' && (
          <div className="bg-muted/30 rounded-md p-2 text-xs text-muted-foreground">
            <div className="flex items-center gap-1.5 mb-1 font-medium text-foreground/70">
              <Brain className="h-3 w-3" />
              Thinking
            </div>
            <p className="line-clamp-2 italic">{agent.current_thinking}</p>
          </div>
        )}

        {/* Last Tool Call */}
        {agent.last_tool_call && agent.status === 'running' && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Wrench className="h-3 w-3 shrink-0" />
            <span className="font-medium">{agent.last_tool_call}</span>
            {agent.last_tool_input && (
              <span className="truncate opacity-70">{agent.last_tool_input}</span>
            )}
          </div>
        )}

        {/* Active Files */}
        {agent.active_files.length > 0 && (
          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-medium">
              <FileCode className="h-3 w-3" />
              Files ({agent.active_files.length})
            </div>
            <div className="flex flex-wrap gap-1">
              {agent.active_files.slice(-3).map((f) => (
                <Badge key={f} variant="secondary" className="text-[10px] font-mono px-1.5">
                  {f.split('/').pop()}
                </Badge>
              ))}
              {agent.active_files.length > 3 && (
                <Badge variant="secondary" className="text-[10px] px-1.5">
                  +{agent.active_files.length - 3}
                </Badge>
              )}
            </div>
          </div>
        )}

        {/* Stats Row */}
        <div className="flex items-center gap-3 text-xs text-muted-foreground pt-1 border-t border-border/30">
          <div className="flex items-center gap-1" title="Tokens">
            <Cpu className="h-3 w-3" />
            {agent.tokens.total_tokens.toLocaleString()}
          </div>
          <div className="flex items-center gap-1" title="Cost">
            <DollarSign className="h-3 w-3" />
            ${agent.tokens.estimated_cost_usd.toFixed(4)}
          </div>
          <div className="flex items-center gap-1" title="Elapsed">
            <Clock className="h-3 w-3" />
            {formatElapsed(agent.elapsed_seconds)}
          </div>
        </div>

        {/* Controls */}
{/* biome-ignore lint/a11y/noNoninteractiveElementInteractions lint/a11y/noStaticElementInteractions lint/a11y/useKeyWithClickEvents: interactive handler is intentional */}
        <div className="flex items-center gap-1.5 pt-1" onClick={(e) => e.stopPropagation()}>
          {agent.status === 'idle' && (
            <>
              <input
                type="text"
                placeholder="Task description..."
                value={taskInput}
                onChange={(e) => setTaskInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && taskInput.trim()) {
                    onStart(taskInput);
                    setTaskInput('');
                  }
                }}
                className="flex-1 text-xs bg-muted/50 border border-border/50 rounded px-2 py-1 placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/30"
              />
              <Button
                variant="default"
                size="icon"
                className="h-6 w-6"
                onClick={() => {
                  if (taskInput.trim()) {
                    onStart(taskInput);
                    setTaskInput('');
                  }
                }}
              >
                <Play className="h-3 w-3" />
              </Button>
            </>
          )}
          {agent.status === 'running' && (
            <>
              <Button variant="outline" size="icon" className="h-6 w-6" onClick={onPause}>
                <Pause className="h-3 w-3" />
              </Button>
              <Button variant="destructive" size="icon" className="h-6 w-6" onClick={onStop}>
                <Square className="h-3 w-3" />
              </Button>
            </>
          )}
          {agent.status === 'paused' && (
            <>
              <Button variant="default" size="icon" className="h-6 w-6" onClick={onResume}>
                <Play className="h-3 w-3" />
              </Button>
              <Button variant="destructive" size="icon" className="h-6 w-6" onClick={onStop}>
                <Square className="h-3 w-3" />
              </Button>
            </>
          )}
          {(agent.status === 'completed' || agent.status === 'error') && (
            <Button
              variant="outline"
              size="sm"
              className="h-6 text-xs"
              onClick={() => onStart('')}
            >
              <Play className="h-3 w-3 mr-1" />
              Restart
            </Button>
          )}
        </div>

        {/* Error message */}
        {agent.error_message && (
          <div className="text-xs text-destructive bg-destructive/10 rounded px-2 py-1 truncate">
            {agent.error_message}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${Math.floor(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  return `${Math.floor(seconds / 3600)}h${Math.floor((seconds % 3600) / 60)}m`;
}


