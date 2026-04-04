import type { ClaudeProfile } from "@shared/types";
import type React from "react";
import { useTranslation } from "react-i18next";

interface ProfileRendererProps {
	readonly account: ClaudeProfile;
	readonly isActive: boolean;
	readonly onClick: (e: React.MouseEvent) => void;
}

export function ProfileRenderer({
	account,
	isActive,
	onClick,
}: ProfileRendererProps) {
	const { t } = useTranslation(["common"]);

	return (
		<button
			type="button"
			onClick={onClick}
			className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-md transition-all duration-200 text-left ${
				isActive
					? "bg-primary text-primary-foreground shadow-sm"
					: "hover:bg-muted/50 text-foreground"
			}`}
		>
			<div className="flex items-center gap-2 flex-1 min-w-0">
				<div className="w-6 h-6 rounded-full bg-linear-to-br from-blue-400 to-blue-600 flex items-center justify-center text-white text-xs font-medium shadow-sm">
					{account.name.charAt(0).toUpperCase()}
				</div>
				<div className="flex-1 min-w-0">
					<div className="flex items-center gap-1.5">
						<span className="text-sm font-medium truncate">{account.name}</span>
						{isActive && (
							<span className="text-xs bg-primary-foreground/20 px-1.5 py-0.5 rounded-full">
								{t("common:usage.active")}
							</span>
						)}
					</div>
					<div className="text-xs opacity-70 truncate">{account.email}</div>
				</div>
			</div>
			{!isActive && (
				<span className="text-xs px-2 py-1 rounded-md bg-primary/10 text-primary pointer-events-none">
					{t("common:usage.setActive")}
				</span>
			)}
		</button>
	);
}
