import { cn } from '../../lib/utils';
import { Skeleton } from './skeleton';

interface TerminalGridSkeletonProps {
  readonly panels?: number;
  readonly className?: string;
}

/**
 * Skeleton screen for the TerminalGrid view.
 * Renders placeholder terminal panels with animated content.
 */
export function TerminalGridSkeleton({
  panels = 4,
  className,
}: TerminalGridSkeletonProps) {
  return (
    <output 
      aria-label="Loading terminals..."
      className={cn('grid grid-cols-2 gap-2 p-4 h-full', className)}
    >
      {Array.from({ length: panels }).map(() => (
        <TerminalPanelSkeleton key={crypto.randomUUID()} />
      ))}
    </output>
  );
}

/**
 * Single terminal panel skeleton placeholder.
 */
function TerminalPanelSkeleton() {
  return (
    <div className="flex flex-col rounded-lg border border-border bg-card overflow-hidden">
      {/* Terminal header bar */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-border bg-muted/30">
        <Skeleton className="h-3 w-3 rounded-full" />
        <Skeleton className="h-3 w-3 rounded-full" />
        <Skeleton className="h-3 w-3 rounded-full" />
        <Skeleton className="h-3 w-32 ml-2" />
      </div>

      {/* Terminal content area */}
      <div className="flex-1 p-3 space-y-2 bg-black/5 dark:bg-black/20 min-h-[120px]">
        <Skeleton className="h-3 w-4/5 bg-muted/50" />
        <Skeleton className="h-3 w-3/5 bg-muted/50" />
        <Skeleton className="h-3 w-2/3 bg-muted/50" />
        <Skeleton className="h-3 w-1/2 bg-muted/50" />
        <Skeleton className="h-3 w-3/4 bg-muted/50" />
      </div>
    </div>
  );
}
