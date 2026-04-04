import { cn } from "../../lib/utils";

interface SkeletonProps extends React.OutputHTMLAttributes<HTMLOutputElement> {
	/** Width of the skeleton element */
	readonly width?: string | number;
	/** Height of the skeleton element */
	readonly height?: string | number;
	/** Whether to render as a circle */
	readonly circle?: boolean;
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
}: Readonly<SkeletonProps>) {
	return (
		<output
			aria-label="Loading..."
			className={cn(
				"animate-pulse bg-muted rounded-md border-0 p-0 m-0",
				circle && "rounded-full",
				className,
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
 * Props for SkeletonLine component.
 */
interface SkeletonLineProps
	extends Readonly<React.OutputHTMLAttributes<HTMLOutputElement>> {
	// No additional props currently, but interface for future extensibility
}

/**
 * A skeleton text line — useful for simulating paragraphs.
 */
export function SkeletonLine({
	className,
	...props
}: Readonly<SkeletonLineProps>) {
	return <Skeleton className={cn("h-4 w-full", className)} {...props} />;
}

/**
 * Props for SkeletonCard component.
 */
interface SkeletonCardProps
	extends React.OutputHTMLAttributes<HTMLOutputElement> {
	/** Content to render inside the card skeleton */
	readonly children?: React.ReactNode;
}

/**
 * A skeleton card — useful for simulating card-based layouts.
 */
export function SkeletonCard({
	className,
	children,
	...props
}: Readonly<SkeletonCardProps>) {
	return (
		<output
			aria-label="Loading..."
			className={cn(
				"rounded-lg border border-border bg-card p-4 space-y-3",
				className,
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
		</output>
	);
}
