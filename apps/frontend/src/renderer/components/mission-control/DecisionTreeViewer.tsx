/**
 * DecisionTreeViewer — Renders the decision tree for a selected agent.
 *
 * Shows the hierarchical reasoning path: thinking → tool calls → decisions → results.
 * Each node is color-coded by type and status.
 */

import {
  Brain,
  Wrench,
  GitBranch,
  CheckCircle2,
  XCircle,
  Circle,
  ChevronRight,
  ChevronDown,
  Minus,
} from 'lucide-react';
import { useState } from 'react';
import { ScrollArea } from '../ui/scroll-area';
import { cn } from '../../lib/utils';
import type { DecisionTree, DecisionNode } from '../../stores/mission-control-store';

interface DecisionTreeViewerProps {
  readonly tree: DecisionTree;
}

const NODE_ICONS: Record<string, React.ElementType> = {
  root: GitBranch,
  thinking: Brain,
  tool_call: Wrench,
  decision: GitBranch,
  result: CheckCircle2,
  error: XCircle,
  branch: GitBranch,
};

const NODE_COLORS: Record<string, string> = {
  root: 'text-primary border-primary/30 bg-primary/5',
  thinking: 'text-purple-500 border-purple-500/30 bg-purple-500/5',
  tool_call: 'text-blue-500 border-blue-500/30 bg-blue-500/5',
  decision: 'text-amber-500 border-amber-500/30 bg-amber-500/5',
  result: 'text-green-500 border-green-500/30 bg-green-500/5',
  error: 'text-red-500 border-red-500/30 bg-red-500/5',
  branch: 'text-cyan-500 border-cyan-500/30 bg-cyan-500/5',
};

const STATUS_INDICATORS: Record<string, { icon: React.ElementType; color: string }> = {
  active: { icon: Circle, color: 'text-blue-500 animate-pulse' },
  completed: { icon: CheckCircle2, color: 'text-green-500' },
  failed: { icon: XCircle, color: 'text-red-500' },
  skipped: { icon: Minus, color: 'text-gray-400' },
};

export function DecisionTreeViewer({ tree }: DecisionTreeViewerProps) {
  if (!tree.root_id || tree.node_count === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-sm text-muted-foreground">
        No decisions recorded yet
      </div>
    );
  }

  return (
    <ScrollArea className="h-64">
      <div className="space-y-0.5 pr-2">
        <TreeNode
          node={tree.nodes[tree.root_id]}
          allNodes={tree.nodes}
          currentNodeId={tree.current_node_id}
          depth={0}
        />
      </div>
    </ScrollArea>
  );
}

interface TreeNodeProps {
  readonly node: DecisionNode;
  readonly allNodes: Record<string, DecisionNode>;
  readonly currentNodeId: string | null;
  readonly depth: number;
}

function TreeNode({ node, allNodes, currentNodeId, depth }: TreeNodeProps) {
  const [expanded, setExpanded] = useState(true);
  const Icon = NODE_ICONS[node.node_type] ?? Circle;
  const colorClass = NODE_COLORS[node.node_type] ?? NODE_COLORS.root;
  const statusInfo = STATUS_INDICATORS[node.status] ?? STATUS_INDICATORS.active;
  const StatusIcon = statusInfo.icon;
  const isCurrent = node.id === currentNodeId;
  const hasChildren = node.children.length > 0;
  
  // Determine which icon to show for expand/collapse toggle
  const toggleIcon = () => {
    if (!hasChildren) {
      return <span className="h-1 w-1 rounded-full bg-border" />;
    }
    
    if (expanded) {
      return <ChevronDown className="h-3 w-3 text-muted-foreground" />;
    }
    
    return <ChevronRight className="h-3 w-3 text-muted-foreground" />;
  };

  return (
    <div className="select-none">
      {/* Node row */}
      <div
        className={cn(
          'flex items-start gap-1.5 py-1 px-1.5 rounded-md text-xs transition-colors cursor-pointer hover:bg-muted/50',
          isCurrent && 'bg-primary/5 ring-1 ring-primary/20',
        )}
        style={{ paddingLeft: `${depth * 16 + 4}px` }}
        onClick={() => hasChildren && setExpanded(!expanded)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { hasChildren && setExpanded(!expanded); } }}
      >
        {/* Expand/collapse toggle */}
        <span className="w-3.5 h-3.5 shrink-0 flex items-center justify-center mt-0.5">
          {toggleIcon()}
        </span>

        {/* Node icon */}
        <div className={cn('p-0.5 rounded border shrink-0', colorClass)}>
          <Icon className="h-3 w-3" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0 space-y-0.5">
          <div className="flex items-center gap-1.5">
            <span className="font-medium truncate">{node.label}</span>
            <StatusIcon className={cn('h-3 w-3 shrink-0', statusInfo.color)} />
            {node.duration_ms > 0 && (
              <span className="text-[10px] text-muted-foreground shrink-0">
                {node.duration_ms.toFixed(0)}ms
              </span>
            )}
          </div>

          {/* Description */}
          {node.description && (
            <p className="text-muted-foreground line-clamp-1">{node.description}</p>
          )}

          {/* Tool info */}
          {node.node_type === 'tool_call' && node.tool_name && (
            <div className="flex items-center gap-1 text-muted-foreground">
              <Wrench className="h-2.5 w-2.5" />
              <span className="font-mono">{node.tool_name}</span>
              {node.tool_input && (
                <span className="truncate opacity-70">{node.tool_input}</span>
              )}
            </div>
          )}

          {/* Decision info */}
          {node.node_type === 'decision' && node.chosen_option && (
            <div className="text-muted-foreground">
              <span className="font-medium text-foreground/70">→ {node.chosen_option}</span>
              {node.reasoning && <span className="ml-1 opacity-70">({node.reasoning})</span>}
            </div>
          )}
        </div>
      </div>

      {/* Children */}
      {expanded && hasChildren && (
        <div>
          {node.children.map((childId) => {
            const childNode = allNodes[childId];
            if (!childNode) return null;
            return (
              <TreeNode
                key={childId}
                node={childNode}
                allNodes={allNodes}
                currentNodeId={currentNodeId}
                depth={depth + 1}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
