import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';

// Catégories et templates enrichis
const BLOCK_CATEGORIES = [
	{
		labelKey: 'categoryFrontend',
		blocks: [{ type: 'frontend', labelKey: 'frontend', icon: '🖥️' }],
	},
	{
		labelKey: 'categoryBackend',
		blocks: [
			{ type: 'backend', labelKey: 'backend', icon: '🗄️' },
			{ type: 'worker', labelKey: 'worker', icon: '⚙️' },
			{ type: 'microservice', labelKey: 'microservice', icon: '🔌' },
			{ type: 'gateway', labelKey: 'gateway', icon: '🛡️' },
		],
	},
	{
		labelKey: 'categoryData',
		blocks: [
			{ type: 'database', labelKey: 'database', icon: '🗃️' },
			{ type: 'cache', labelKey: 'cache', icon: '🧠' },
			{ type: 'search', labelKey: 'search', icon: '🔍' },
			{ type: 'queue', labelKey: 'queue', icon: '📬' },
			{ type: 'storage', labelKey: 'storage', icon: '💾' },
		],
	},
	{
		labelKey: 'categoryInfra',
		blocks: [
			{ type: 'messagebroker', labelKey: 'messageBroker', icon: '📨' },
			{ type: 'cdn', labelKey: 'cdn', icon: '🌐' },
			{ type: 'monitoring', labelKey: 'monitoring', icon: '📈' },
			{ type: 'analytics', labelKey: 'analytics', icon: '📊' },
		],
	},
	{
		labelKey: 'categorySecurity',
		blocks: [{ type: 'auth', labelKey: 'auth', icon: '🔒' }],
	},
	{
		labelKey: 'categoryIntegration',
		blocks: [
			{ type: 'thirdparty', labelKey: 'thirdPartyApi', icon: '🔗' },
			{ type: 'notification', labelKey: 'notification', icon: '🔔' },
		],
	},
	{
		labelKey: 'categoryCustom',
		blocks: [{ type: 'custom', labelKey: 'customBlock', icon: '✨' }],
	},
];

export const VisualProgrammingPalette: React.FC<{ compact?: boolean }> = ({ compact = false }) => {
	const { t } = useTranslation('visualProgramming');
	// Accordion state: ouvert/fermé par catégorie
	const [openGroups, setOpenGroups] = useState(() =>
		Object.fromEntries(BLOCK_CATEGORIES.map((cat) => [cat.labelKey, true])),
	);
	const toggleGroup = (key: string) =>
		setOpenGroups((prev) => ({ ...prev, [key]: !prev[key] }));

	// Drag start handler
	const handleDragStart = (e: React.DragEvent, type: string) => {
		e.dataTransfer.setData('application/block-type', type);
	};

	if (compact) {
		return (
			<div
				className="flex items-center justify-center w-14 h-14"
				style={{ opacity: 0.9, pointerEvents: 'auto', filter: 'none', background: 'transparent' }} // icône nette, pas de blur
				title={t('showPalette', 'Afficher la palette')}
			>
				<span style={{ fontSize: 28, color: 'var(--palette-fg, #f4f4f5)', filter: 'none', textShadow: '0 1px 4px rgba(0,0,0,0.10)' }}>🧩</span>
			</div>
		);
	}

	return (
		<div
			className="w-90 p-4 flex flex-col gap-2 border rounded shadow-lg max-h-[80vh] overflow-y-auto"
			style={{
				background: 'linear-gradient(135deg, var(--palette-bg-1, #18181b99) 0%, var(--palette-bg-2, #27272a99) 100%)',
				backdropFilter: 'blur(12px)',
				WebkitBackdropFilter: 'blur(12px)',
				border: '1.5px solid var(--palette-border, #27272a66)',
				boxShadow: '0 4px 24px 0 rgba(0,0,0,0.10)',
				color: 'var(--palette-fg, #f4f4f5)',
				transition: 'background 0.2s',
			}}
		>
			<div className="font-bold mb-2 text-lg">{t('palette')}</div>
			{BLOCK_CATEGORIES.map((cat) => (
				<div key={cat.labelKey} className="mb-2">
					<button
						className="flex items-center w-full text-xs font-semibold text-muted-foreground mb-1 hover:text-foreground transition-colors"
						style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
						onClick={() => toggleGroup(cat.labelKey)}
						aria-expanded={openGroups[cat.labelKey]}
					>
						<span style={{ marginRight: 6 }}>{openGroups[cat.labelKey] ? '▼' : '▶'}</span>
						{t(cat.labelKey)}
					</button>
					{openGroups[cat.labelKey] && (
						<div className="flex flex-wrap gap-2">
							{cat.blocks.map((tpl) => (
								<div
									key={tpl.type}
									className="flex items-center gap-2 p-2 rounded cursor-grab hover:bg-muted/60"
									draggable
									title={t(tpl.labelKey + 'Desc', '')}
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