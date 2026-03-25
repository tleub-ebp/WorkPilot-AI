import { cn } from '../../lib/utils';
import { Skeleton, SkeletonCard } from './skeleton';

interface KanbanSkeletonProps {
  columns?: number;
  cardsPerColumn?: number[];
  className?: string;
  showRefreshText?: boolean;
}

/**
 * Skeleton screen for the KanbanBoard view.
 * Renders placeholder columns with animated card skeletons.
 */
export function KanbanSkeleton({
  columns = 5,
  cardsPerColumn = [3, 2, 4, 1, 2],
  className,
  showRefreshText = false,
}: KanbanSkeletonProps) {
  return (
    <div
      // biome-ignore lint/a11y/useSemanticElements: custom element maintains accessibility
      // biome-ignore lint/a11y/useSemanticElements: intentional
      role="status"
      aria-label={showRefreshText ? "Refreshing kanban board..." : "Loading kanban board..."}
      className={cn('flex gap-3 p-4 h-full overflow-hidden', className)}
    >
      {showRefreshText && (
        <div className="absolute top-4 right-4 flex items-center gap-2 text-sm text-muted-foreground">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary" />
          <span>Actualisation...</span>
        </div>
      )}
      {Array.from({ length: columns }).map((_, colIdx) => (
        <div
          // biome-ignore lint/suspicious/noArrayIndexKey: no stable key available
          key={colIdx}
          className="flex flex-col flex-1 min-w-[220px] max-w-[350px]"
        >
          {/* Column header skeleton */}
          <div className="flex items-center gap-2 mb-3 px-2">
            <Skeleton className="h-5 w-24" />
            <Skeleton className="h-5 w-6 rounded-full" />
          </div>

          {/* Column content skeleton */}
          <div className="flex-1 space-y-2 rounded-lg bg-muted/30 p-2">
            {Array.from({ length: cardsPerColumn[colIdx] ?? 2 }).map(
              (_, cardIdx) => (
                // biome-ignore lint/suspicious/noArrayIndexKey: no stable key available
                <KanbanCardSkeleton key={cardIdx} />
              )
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Single kanban card skeleton placeholder.
 */
function KanbanCardSkeleton() {
  return (
    <SkeletonCard className="space-y-2">
      {/* Title */}
      <Skeleton className="h-4 w-4/5" />
      {/* Description snippet */}
      <Skeleton className="h-3 w-3/5" />
      {/* Footer: status badge + avatar */}
      <div className="flex items-center justify-between pt-1">
        <Skeleton className="h-5 w-16 rounded-full" />
        <Skeleton className="h-5 w-5 rounded-full" />
      </div>
    </SkeletonCard>
  );
}
