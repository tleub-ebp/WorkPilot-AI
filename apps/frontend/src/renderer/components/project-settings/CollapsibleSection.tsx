import { ChevronDown, ChevronUp } from "lucide-react";
import { type ReactNode, useId } from "react";

interface CollapsibleSectionProps {
	readonly title: string;
	readonly icon: ReactNode;
	readonly isExpanded: boolean;
	readonly onToggle: () => void;
	readonly badge?: ReactNode;
	readonly children: ReactNode;
}

export function CollapsibleSection({
	title,
	icon,
	isExpanded,
	onToggle,
	badge,
	children,
}: CollapsibleSectionProps) {
	const contentId = useId();

	return (
		<section className="space-y-3">
			<button
				type="button"
				onClick={onToggle}
				className="w-full flex items-center justify-between text-sm font-semibold text-foreground hover:text-foreground/80"
				aria-expanded={isExpanded}
				aria-controls={contentId}
			>
				<div className="flex items-center gap-2">
					{icon}
					{title}
					{badge}
				</div>
				{isExpanded ? (
					<ChevronUp className="h-4 w-4" aria-hidden="true" />
				) : (
					<ChevronDown className="h-4 w-4" aria-hidden="true" />
				)}
			</button>

			{isExpanded && (
				<div id={contentId} className="space-y-4 pl-6 pt-2">
					{children}
				</div>
			)}
		</section>
	);
}
