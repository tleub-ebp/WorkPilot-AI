import { useDroppable } from "@dnd-kit/core";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Star } from "lucide-react";
import type { CSSProperties, ReactNode } from "react";
import { cn } from "@/lib/utils";

// dnd-kit requires each sortable id to be stable AND unique within its DndContext.
// Because items and groups share the same DndContext (needed so an item can be dragged
// onto the favorites drop zone), we namespace ids — `item:kanban`, `group:agents`,
// `fav-item:kanban`. Parsing helpers below keep the rest of the codebase unaware of this.
export type SortableKind = "group" | "item" | "fav-item" | "fav-group";

export function encodeSortableId(kind: SortableKind, id: string): string {
	return `${kind}:${id}`;
}

export function decodeSortableId(
	sortableId: string,
): { kind: SortableKind; id: string } | null {
	const sep = sortableId.indexOf(":");
	if (sep === -1) return null;
	const kind = sortableId.slice(0, sep) as SortableKind;
	const id = sortableId.slice(sep + 1);
	if (
		kind !== "group" &&
		kind !== "item" &&
		kind !== "fav-item" &&
		kind !== "fav-group"
	) {
		return null;
	}
	return { kind, id };
}

interface SortableWrapperProps {
	sortableId: string;
	disabled?: boolean;
	children: (args: {
		dragHandle: ReactNode;
		isDragging: boolean;
		setNodeRef: (node: HTMLElement | null) => void;
		style: CSSProperties;
	}) => ReactNode;
}

// Generic sortable wrapper. The drag handle is rendered via render-prop so callers
// decide exactly where it sits in their own markup — we don't wrap their layout.
export function SortableWrapper({
	sortableId,
	disabled,
	children,
}: SortableWrapperProps) {
	const {
		attributes,
		listeners,
		setNodeRef,
		transform,
		transition,
		isDragging,
	} = useSortable({ id: sortableId, disabled });

	const style: CSSProperties = {
		transform: CSS.Transform.toString(transform),
		transition,
		opacity: isDragging ? 0.4 : 1,
		zIndex: isDragging ? 50 : undefined,
	};

	const dragHandle = (
		<button
			type="button"
			aria-label="Drag to reorder"
			className={cn(
				"opacity-40 hover:opacity-100 focus-visible:opacity-100",
				"transition-opacity duration-150",
				"flex items-center justify-center w-4 h-4 shrink-0",
				"text-muted-foreground hover:text-foreground cursor-grab active:cursor-grabbing",
			)}
			{...attributes}
			{...listeners}
		>
			<GripVertical className="h-3.5 w-3.5" />
		</button>
	);

	return <>{children({ dragHandle, isDragging, setNodeRef, style })}</>;
}

// Droppable wrapper for the favorites section. When the user drags any nav item or
// group, this zone lights up to signal "drop here to pin". We use a stable droppable
// id "__fav_drop__" so the Sidebar's drag-end handler can detect favorites drops
// even when the favorites group is empty (no sortable children to receive the drop).
interface FavoritesDropZoneProps {
	isDragging: boolean;
	active: boolean;
	children: ReactNode;
}

export function FavoritesDropZone({
	isDragging,
	active,
	children,
}: FavoritesDropZoneProps) {
	const { setNodeRef, isOver } = useDroppable({ id: "__fav_drop__" });
	return (
		<div
			ref={setNodeRef}
			className={cn(
				"relative transition-all duration-200 rounded-lg",
				isDragging && active && "ring-2 ring-amber-400/40",
				isOver && "ring-2 ring-amber-400 shadow-[0_0_24px_-4px_rgba(251,191,36,0.5)] scale-[1.01]",
			)}
		>
			{children}
		</div>
	);
}

// Shown when no favorites yet and the user starts dragging — gives them a visible
// target to drop onto. Otherwise there'd be no way to discover pinning via drag
// until they've already used the star button at least once.
interface FavoritesDropZoneEmptyProps {
	label: string;
}

export function FavoritesDropZoneEmpty({
	label,
}: FavoritesDropZoneEmptyProps) {
	const { setNodeRef, isOver } = useDroppable({ id: "__fav_drop__" });
	return (
		<div
			ref={setNodeRef}
			className={cn(
				"flex items-center justify-center gap-2 rounded-lg border-2 border-dashed px-3 py-4 text-xs transition-all duration-200",
				isOver
					? "border-amber-400 bg-amber-400/10 text-amber-400 shadow-[0_0_24px_-4px_rgba(251,191,36,0.5)]"
					: "border-amber-400/30 text-muted-foreground/70 bg-amber-400/5",
			)}
		>
			<Star
				className={cn(
					"h-3.5 w-3.5",
					isOver ? "fill-amber-400 text-amber-400" : "text-amber-400/60",
				)}
			/>
			<span>{label}</span>
		</div>
	);
}

interface PinStarProps {
	isPinned: boolean;
	onToggle: (e: React.MouseEvent) => void;
	label: string;
	alwaysVisible?: boolean;
}

// Pin toggle shown on the right of each nav item/group. Hidden until hover to keep
// the chrome minimal; stays visible once pinned so the user sees their own state.
export function PinStar({
	isPinned,
	onToggle,
	label,
	alwaysVisible,
}: PinStarProps) {
	return (
		<button
			type="button"
			onClick={onToggle}
			aria-label={label}
			aria-pressed={isPinned}
			className={cn(
				"flex items-center justify-center w-5 h-5 shrink-0 rounded",
				"transition-all duration-200",
				"hover:bg-accent/60 hover:scale-110",
				isPinned
					? "text-amber-400 opacity-100"
					: cn(
							"text-muted-foreground/60 hover:text-amber-400",
							alwaysVisible
								? "opacity-100"
								: "opacity-0 group-hover:opacity-100 focus-visible:opacity-100",
						),
			)}
		>
			<Star
				className={cn("h-3.5 w-3.5", isPinned && "fill-amber-400")}
			/>
		</button>
	);
}
