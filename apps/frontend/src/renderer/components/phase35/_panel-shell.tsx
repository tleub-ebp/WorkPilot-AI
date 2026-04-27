import type { ReactNode } from "react";
import { Card } from "../ui/card";

interface PanelShellProps {
	title: string;
	subtitle?: string;
	actions?: ReactNode;
	children: ReactNode;
	error?: string | null;
}

/**
 * Lightweight wrapper used by every Phase 3-5 panel.
 *
 * Keeps the layout consistent (title + optional subtitle + actions row +
 * body + inline error) without dragging in a heavy header component.
 */
export function PanelShell({ title, subtitle, actions, children, error }: PanelShellProps) {
	return (
		<Card className="p-4 space-y-4">
			<div className="flex items-start justify-between gap-4">
				<div>
					<h2 className="text-lg font-semibold">{title}</h2>
					{subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
				</div>
				{actions && <div className="flex items-center gap-2">{actions}</div>}
			</div>
			{error && (
				<div className="rounded border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm text-destructive">
					{error}
				</div>
			)}
			<div>{children}</div>
		</Card>
	);
}
