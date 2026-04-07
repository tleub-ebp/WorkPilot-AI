import type React from "react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

// CatÃ©gories et templates enrichis
const BLOCK_CATEGORIES = [
	{
		labelKey: "categoryFrontend",
		blocks: [{ type: "frontend", labelKey: "frontend", icon: "ðŸ–¥ï¸" }],
	},
	{
		labelKey: "categoryBackend",
		blocks: [
			{ type: "backend", labelKey: "backend", icon: "ðŸ—„ï¸" },
			{ type: "worker", labelKey: "worker", icon: "âš™ï¸" },
			{ type: "microservice", labelKey: "microservice", icon: "ðŸ”Œ" },
			{ type: "gateway", labelKey: "gateway", icon: "ðŸ›¡ï¸" },
		],
	},
	{
		labelKey: "categoryData",
		blocks: [
			{ type: "database", labelKey: "database", icon: "ðŸ—ƒï¸" },
			{ type: "cache", labelKey: "cache", icon: "ðŸ§ " },
			{ type: "search", labelKey: "search", icon: "ðŸ”" },
			{ type: "queue", labelKey: "queue", icon: "ðŸ“¬" },
			{ type: "storage", labelKey: "storage", icon: "ðŸ’¾" },
		],
	},
	{
		labelKey: "categoryInfra",
		blocks: [
			{ type: "messagebroker", labelKey: "messageBroker", icon: "ðŸ“¨" },
			{ type: "cdn", labelKey: "cdn", icon: "ðŸŒ" },
			{ type: "monitoring", labelKey: "monitoring", icon: "ðŸ“ˆ" },
			{ type: "analytics", labelKey: "analytics", icon: "ðŸ“Š" },
		],
	},
	{
		labelKey: "categorySecurity",
		blocks: [{ type: "auth", labelKey: "auth", icon: "ðŸ”’" }],
	},
	{
		labelKey: "categoryIntegration",
		blocks: [
			{ type: "thirdparty", labelKey: "thirdPartyApi", icon: "ðŸ”—" },
			{ type: "notification", labelKey: "notification", icon: "ðŸ””" },
		],
	},
	{
		labelKey: "categoryCustom",
		blocks: [{ type: "custom", labelKey: "customBlock", icon: "âœ¨" }],
	},
];

export const VisualProgrammingPalette: React.FC<{ compact?: boolean }> = ({
	compact = false,
}) => {
	const { t } = useTranslation("visualProgramming");
	// Accordion state: ouvert/fermÃ© par catÃ©gorie
	const [openGroups, setOpenGroups] = useState(() =>
		Object.fromEntries(BLOCK_CATEGORIES.map((cat) => [cat.labelKey, true])),
	);
	const toggleGroup = (key: string) =>
		setOpenGroups((prev) => ({ ...prev, [key]: !prev[key] }));

	// Drag start handler
	const handleDragStart = (e: React.DragEvent, type: string) => {
		e.dataTransfer.setData("application/block-type", type);
	};

	if (compact) {
		return (
			<div
				className="flex items-center justify-center w-14 h-14"
				style={{
					opacity: 0.9,
					pointerEvents: "auto",
					filter: "none",
					background: "transparent",
				}} // icÃ´ne nette, pas de blur
				title={t("showPalette", "Afficher la palette")}
			>
				<span
					style={{
						fontSize: 28,
						color: "var(--palette-fg, #f4f4f5)",
						filter: "none",
						textShadow: "0 1px 4px rgba(0,0,0,0.10)",
					}}
				>
					ðŸ§©
				</span>
			</div>
		);
	}

	return (
		<div
			className="w-90 p-4 flex flex-col gap-2 border rounded shadow-lg max-h-[80vh] overflow-y-auto"
			style={{
				background:
					"linear-gradient(135deg, var(--palette-bg-1, #18181b99) 0%, var(--palette-bg-2, #27272a99) 100%)",
				backdropFilter: "blur(12px)",
				WebkitBackdropFilter: "blur(12px)",
				border: "1.5px solid var(--palette-border, #27272a66)",
				boxShadow: "0 4px 24px 0 rgba(0,0,0,0.10)",
				color: "var(--palette-fg, #f4f4f5)",
				transition: "background 0.2s",
			}}
		>
			<div className="font-bold mb-2 text-lg">{t("palette")}</div>
			{BLOCK_CATEGORIES.map((cat) => (
				<div key={cat.labelKey} className="mb-2">
					<button
						type="button"
						className="flex items-center w-full text-xs font-semibold text-muted-foreground mb-1 hover:text-foreground transition-colors"
						style={{
							background: "none",
							border: "none",
							cursor: "pointer",
							padding: 0,
						}}
						onClick={() => toggleGroup(cat.labelKey)}
						aria-expanded={openGroups[cat.labelKey]}
					>
						<span style={{ marginRight: 6 }}>
							{openGroups[cat.labelKey] ? "â–¼" : "â–¶"}
						</span>
						{t(cat.labelKey)}
					</button>
					{openGroups[cat.labelKey] && (
						<div className="flex flex-wrap gap-2">
							{cat.blocks.map((tpl) => (
								// biome-ignore lint/a11y/noStaticElementInteractions: draggable palette block
								// biome-ignore lint/a11y/noNoninteractiveElementInteractions: draggable palette block
								<div
									key={tpl.type}
									className="flex items-center gap-2 p-2 rounded cursor-grab hover:bg-muted/60"
									draggable
									title={t(`${tpl.labelKey}Desc`, "")}
									onDragStart={(e) => handleDragStart(e, tpl.type)}
								>
									<span>{tpl.icon}</span>
									<span>{t(tpl.labelKey)}</span>
								</div>
							))}
						</div>
					)}
				</div>
			))}
		</div>
	);
};
