import { cn } from '../../lib/utils';

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Width of the skeleton element */
  width?: string | number;
  /** Height of the skeleton element */
  height?: string | number;
  /** Whether to render as a circle */
  circle?: boolean;
}

/**
 * Skeleton loading placeholder component.
 * Renders an animated pulse placeholder for content that is loading.
 */
export function Skeleton({
  className,
  width,
  height,
  circle,
  style,
  ...props
}: SkeletonProps) {
  return (
    <div
      role="status"
      aria-label="Loading..."
      className={cn(
        'animate-pulse bg-muted rounded-md',
        circle && 'rounded-full',
        className
      )}
      style={{
        width: width ?? undefined,
        height: height ?? undefined,
        ...style,
      }}
      {...props}
    />
  );
}

/**
 * A skeleton text line — useful for simulating paragraphs.
 */
export function SkeletonLine({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <Skeleton
      className={cn('h-4 w-full', className)}
      {...props}
    />
  );
}

/**
 * A skeleton card — useful for simulating card-based layouts.
 */
export function SkeletonCard({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      role="status"
      aria-label="Loading..."
      className={cn(
        'rounded-lg border border-border bg-card p-4 space-y-3',
        className
      )}
      {...props}
    >
      {children || (
        <>
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-3 w-1/2" />
          <Skeleton className="h-3 w-5/6" />
        </>
      )}
    </div>
  );
}
