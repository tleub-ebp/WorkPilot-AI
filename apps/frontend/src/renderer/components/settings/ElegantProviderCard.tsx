import {
	ChevronDown,
	ChevronUp,
	Eye,
	EyeOff,
	Key,
	Settings2,
	Star,
	Zap,
} from "lucide-react";
import type React from "react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { Button } from "../ui/button";
import { TooltipProvider } from "../ui/tooltip";

interface ElegantProviderCardProps {
	provider: {
		id: string;
		name: string;
		category: string;
		description?: string;
		isConfigured: boolean;
		isWorking?: boolean;
		lastTested?: string;
		usageCount?: number;
		isPremium?: boolean;
		icon?: React.ElementType;
	};
	onConfigure: (providerId: string) => void;
	onTest: (providerId: string) => void;
	onToggle: (providerId: string, enabled: boolean) => void;
	onRemove?: (providerId: string) => void;
	className?: string;
}

// Icônes officielles des providers depuis ProviderSelector - respectent le thème avec currentColor
const providerIcons: Record<string, React.ReactNode> = {
	// Anthropic — logo officiel (lettre A stylisée)
	anthropic: (
		<svg
			width="20"
			height="20"
			viewBox="0 0 24 24"
			fill="none"
			xmlns="http://www.w3.org/2000/svg"
			role="img"
			aria-label="Anthropic"
		>
			<title>Anthropic</title>
			<path
				d="M13.827 3.52h3.603L24 20h-3.603l-6.57-16.48zm-7.258 0h3.767L16.906 20h-3.674l-1.343-3.461H5.017L3.674 20H0L6.57 3.52zm4.132 9.959L8.453 7.687 6.205 13.479h4.496z"
				fill="currentColor"
			/>
		</svg>
	),
	claude: (
		<svg
			width="20"
			height="20"
			viewBox="0 0 24 24"
			fill="none"
			xmlns="http://www.w3.org/2000/svg"
			role="img"
			aria-label="Claude"
		>
			<title>Claude</title>
			<path
				d="M13.827 3.52h3.603L24 20h-3.603l-6.57-16.48zm-7.258 0h3.767L16.906 20h-3.674l-1.343-3.461H5.017L3.674 20H0L6.57 3.52zm4.132 9.959L8.453 7.687 6.205 13.479h4.496z"
				fill="currentColor"
			/>
		</svg>
	),
	// OpenAI — logo officiel (fleur vectorielle) — currentColor pour s'adapter au thème clair/sombre
	openai: (
		<svg
			width="20"
			height="20"
			viewBox="0 0 24 24"
			fill="none"
			xmlns="http://www.w3.org/2000/svg"
			role="img"
			aria-label="OpenAI"
		>
			<title>OpenAI</title>
			<path
				d="M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073zM13.26 22.43a4.476 4.476 0 0 1-2.876-1.04l.141-.081 4.779-2.758a.795.795 0 0 0 .392-.681v-6.737l2.02 1.168a.071.071 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494zM3.6 18.304a4.47 4.47 0 0 1-.535-3.014l.142.085 4.783 2.759a.771.771 0 0 0 .78 0l5.843-3.369v2.332a.08.08 0 0 1-.033.062L9.74 19.95a4.5 4.5 0 0 1-6.14-1.646zM2.34 7.896a4.485 4.485 0 0 1 2.366-1.973V11.6a.766.766 0 0 0 .388.676l5.815 3.355-2.02 1.168a.076.076 0 0 1-.071 0L3.86 14.026a4.505 4.505 0 0 1-1.52-6.13zm16.597 3.855l-5.843-3.369 2.02-1.168a.076.076 0 0 1 .071 0l4.957 2.812a4.496 4.496 0 0 1-.692 8.115v-5.678a.795.795 0 0 0-.513-.712zm2.01-3.023l-.141-.085-4.774-2.782a.776.776 0 0 0-.785 0L9.409 9.23V6.897a.066.066 0 0 1 .028-.061l4.956-2.817a4.5 4.5 0 0 1 6.683 4.66zm-12.64 4.135l-2.02-1.164a.08.08 0 0 1-.038-.057V6.075a4.5 4.5 0 0 1 7.375-3.453l-.142.08-4.778 2.758a.795.795 0 0 0-.397.681zm1.097-2.365l2.602-1.5 2.607 1.5v2.999l-2.597 1.5-2.607-1.5z"
				fill="currentColor"
			/>
		</svg>
	),
	// Ollama — logo officiel (llama vectorisé simplifié) — currentColor pour s'adapter au thème
	ollama: (
		<svg
			width="20"
			height="20"
			viewBox="0 0 100 100"
			fill="none"
			xmlns="http://www.w3.org/2000/svg"
			role="img"
			aria-label="Ollama"
		>
			<title>Ollama</title>
			<circle cx="36" cy="32" r="10" fill="currentColor" />
			<circle cx="64" cy="32" r="10" fill="currentColor" />
			<ellipse cx="50" cy="62" rx="22" ry="18" fill="currentColor" />
			<rect x="29" y="74" width="10" height="18" rx="5" fill="currentColor" />
			<rect x="61" y="74" width="10" height="18" rx="5" fill="currentColor" />
			<circle cx="32" cy="28" r="3" fill="#00000033" />
			<circle cx="68" cy="28" r="3" fill="#00000033" />
		</svg>
	),
	// Google Gemini — logo officiel (étoile 4 branches dégradée)
	gemini: (
		<svg
			width="20"
			height="20"
			viewBox="0 0 24 24"
			fill="none"
			xmlns="http://www.w3.org/2000/svg"
			role="img"
			aria-label="Google Gemini"
		>
			<title>Google Gemini</title>
			<defs>
				<linearGradient id="gemini-grad" x1="0" y1="0" x2="1" y2="1">
					<stop offset="0%" stopColor="#4285F4" />
					<stop offset="50%" stopColor="#9B72CB" />
					<stop offset="100%" stopColor="#D96570" />
				</linearGradient>
			</defs>
			<path
				d="M12 2C12 2 13.5 8.5 18 12C13.5 15.5 12 22 12 22C12 22 10.5 15.5 6 12C10.5 8.5 12 2 12 2Z"
				fill="url(#gemini-grad)"
			/>
		</svg>
	),
	// Mistral AI — logo officiel (blocs géométriques empilés)
	mistral: (
		<svg
			width="20"
			height="20"
			viewBox="0 0 24 24"
			fill="none"
			xmlns="http://www.w3.org/2000/svg"
			role="img"
			aria-label="Mistral AI"
		>
			<title>Mistral AI</title>
			<rect x="2" y="2" width="6" height="6" fill="#F7521E" />
			<rect x="10" y="2" width="6" height="6" fill="#F7521E" />
			<rect x="18" y="2" width="4" height="6" fill="#F7521E" />
			<rect x="2" y="10" width="6" height="4" fill="#F7521E" />
			<rect x="10" y="10" width="6" height="4" fill="#F7521E" />
			<rect x="2" y="16" width="6" height="6" fill="#F7521E" />
			<rect x="10" y="16" width="6" height="6" fill="#F7521E" />
			<rect x="18" y="16" width="4" height="6" fill="#F7521E" />
		</svg>
	),
	// DeepSeek — logo officiel (œil stylisé bleu)
	deepseek: (
		<svg
			width="20"
			height="20"
			viewBox="0 0 24 24"
			fill="none"
			xmlns="http://www.w3.org/2000/svg"
			role="img"
			aria-label="DeepSeek"
		>
			<title>DeepSeek</title>
			<path
				d="M22.433 9.257c-.173-.08-.537.03-.686.08-.122.03-.275.08-.428.152a9.16 9.16 0 0 0-.62-.833c-.02-.021-.04-.05-.061-.07a9.993 9.993 0 0 0-2.16-1.87A9.675 9.675 0 0 0 12.047 5c-2.627 0-5.05.985-6.847 2.607A9.7 9.7 0 0 0 2.07 14.9a9.695 9.695 0 0 0 9.692 8.594c4.68 0 8.617-3.335 9.49-7.772.061-.304-.02-.487-.183-.567-.163-.08-.396.01-.52.304a8.476 8.476 0 0 1-8.237 5.53A8.467 8.467 0 0 1 3.82 13.5a8.463 8.463 0 0 1 8.463-8.463c2.16 0 4.14.812 5.63 2.14.366.325.701.68 1.006 1.058-.437.212-.843.507-1.168.893-.61.73-.864 1.703-.7 2.637.122.71.477 1.329.995 1.773.518.446 1.168.69 1.849.69.254 0 .508-.03.752-.09.752-.192 1.34-.71 1.614-1.401.213-.548.213-1.137.01-1.642-.193-.497-.57-.894-1.078-1.126l-.002-.002zM9.697 14.596c-.294.517-.874.833-1.493.833-.325 0-.64-.082-.924-.244-.822-.467-1.107-1.512-.64-2.333l.02-.04c.02-.04.04-.08.07-.112 0-.01.01-.021.02-.03.02-.04.051-.07.071-.111.02-.03.04-.07.061-.1.01-.02.03-.041.04-.061.03-.04.07-.08.102-.121.112-.132.244-.244.386-.336a1.74 1.74 0 0 1 .894-.244c.619 0 1.199.315 1.493.833.33.578.32 1.26-.1 1.867zm5.295-1.3c-.203.347-.56.558-.955.558a1.095 1.095 0 0 1-.549-.142c-.519-.294-.702-.965-.406-1.483.203-.345.558-.558.955-.558.193 0 .376.05.548.143.518.295.701.965.406 1.482z"
				fill="#4D6BFE"
			/>
			<path
				d="M9.697 14.596c-.294.517-.874.833-1.493.833-.325 0-.64-.082-.924-.244-.822-.467-1.107-1.512-.64-2.333l.02-.04c.02-.04.04-.08.07-.112 0-.01.01-.021.02-.03.02-.04.051-.07.071-.111.02-.03.04-.07.061-.1.01-.02.03-.041.04-.061.03-.04.07-.08.102-.121.112-.132.244-.244.386-.336a1.74 1.74 0 0 1 .894-.244c.619 0 1.199.315 1.493.833.33.578.32 1.26-.1 1.867zm5.295-1.3c-.203.347-.56.558-.955.558a1.095 1.095 0 0 1-.549-.142c-.519-.294-.702-.965-.406-1.483.203-.345.558-.558.955-.558.193 0 .376.05.548.143.518.295.701.965.406 1.482z"
				fill="#4D6BFE"
			/>
		</svg>
	),
	// Meta — logo officiel (ruban infini stylisé bleu/violet)
	meta: (
		<svg
			width="20"
			height="20"
			viewBox="0 0 24 24"
			fill="none"
			xmlns="http://www.w3.org/2000/svg"
			role="img"
			aria-label="Meta"
		>
			<title>Meta</title>
			<defs>
				<linearGradient id="meta-grad" x1="0" y1="0" x2="1" y2="0">
					<stop offset="0%" stopColor="#0082FB" />
					<stop offset="100%" stopColor="#A33BC2" />
				</linearGradient>
			</defs>
			<path
				d="M2.002 12.87c0 1.356.3 2.394.694 3.053.511.853 1.27 1.302 2.145 1.302 1.03 0 1.972-.254 3.794-2.73l1.698-2.326.005-.007 1.466-2.007c1.01-1.38 2.178-2.943 3.72-2.943 1.334 0 2.59.776 3.566 2.24.865 1.3 1.302 2.948 1.302 4.64 0 1.01-.2 1.77-.538 2.337-.328.548-.956 1.095-2.013 1.095v-2.17c.906 0 1.13-.832 1.13-1.308 0-1.283-.298-2.72-.959-3.718-.488-.74-1.121-1.17-1.787-1.17-.727 0-1.343.485-2.098 1.534l-1.505 2.059-.008.011-.44.602.019.025 1.364 1.875c.99 1.359 1.563 2.044 2.176 2.044.338 0 .685-.12.957-.367l.018-.016.946 1.784-.017.015c-.65.579-1.452.817-2.212.817-.936 0-1.747-.364-2.435-1.09a14.82 14.82 0 0 1-.605-.74l-.86-1.18-.009-.013-1.155 1.575C8.697 16.76 7.608 17.21 6.5 17.21c-1.32 0-2.396-.52-3.143-1.51-.693-.93-1.04-2.198-1.04-3.66l2.685-.17z"
				fill="url(#meta-grad)"
			/>
			<path
				d="M6.617 7.213c1.21 0 2.557.757 4.047 2.747.225.297.454.613.685.94l-.762 1.044-1.052-1.44C8.27 8.77 7.447 8.118 6.702 8.118c-.596 0-1.19.387-1.668 1.09-.572.845-.903 2.073-.903 3.474h-2.13c0-1.72.42-3.354 1.245-4.572.79-1.168 1.905-1.897 3.371-1.897z"
				fill="url(#meta-grad)"
			/>
		</svg>
	),
	// AWS — logo officiel (smile + flèche)
	aws: (
		<svg
			width="20"
			height="20"
			viewBox="0 0 24 24"
			fill="none"
			xmlns="http://www.w3.org/2000/svg"
			role="img"
			aria-label="AWS"
		>
			<title>AWS</title>
			<path
				d="M6.763 10.036c0 .296.032.535.088.71.064.176.144.368.256.576.04.063.056.127.056.183 0 .08-.048.16-.152.24l-.503.335a.383.383 0 0 1-.208.072c-.08 0-.16-.04-.239-.112a2.47 2.47 0 0 1-.287-.375 6.18 6.18 0 0 1-.248-.471c-.622.734-1.405 1.101-2.347 1.101-.67 0-1.205-.191-1.596-.574-.391-.383-.59-.894-.59-1.533 0-.678.239-1.23.726-1.644.487-.415 1.133-.623 1.955-.623.272 0 .551.024.846.064.296.04.6.104.918.176v-.583c0-.607-.127-1.030-.375-1.277-.255-.248-.686-.367-1.3-.367-.28 0-.568.031-.863.103-.295.072-.583.16-.862.272a2.287 2.287 0 0 1-.28.104.488.488 0 0 1-.127.023c-.112 0-.168-.08-.168-.247v-.391c0-.128.016-.224.056-.28a.597.597 0 0 1 .224-.167c.279-.144.614-.264 1.005-.36a4.84 4.84 0 0 1 1.246-.151c.95 0 1.644.216 2.091.647.439.43.662 1.085.662 1.963v2.586zm-3.24 1.214c.263 0 .534-.048.822-.144.287-.096.543-.271.758-.51.128-.152.224-.32.272-.512.047-.191.08-.423.08-.694v-.335a6.66 6.66 0 0 0-.735-.136 6.02 6.02 0 0 0-.75-.048c-.535 0-.926.104-1.19.32-.263.215-.39.518-.39.917 0 .375.095.655.295.846.191.2.47.296.838.296zm6.41.862c-.144 0-.24-.024-.304-.08-.063-.048-.12-.16-.168-.311L7.586 5.55a1.398 1.398 0 0 1-.072-.32c0-.128.064-.2.191-.2h.783c.151 0 .255.025.31.08.065.048.113.16.16.312l1.342 5.284 1.245-5.284c.04-.16.088-.264.151-.312a.549.549 0 0 1 .32-.08h.638c.152 0 .256.025.32.08.063.048.12.16.151.312l1.261 5.348 1.381-5.348c.048-.16.104-.264.16-.312a.52.52 0 0 1 .311-.08h.743c.127 0 .2.065.2.2 0 .04-.009.08-.017.128a1.137 1.137 0 0 1-.056.2l-1.923 6.17c-.048.16-.104.263-.168.311a.51.51 0 0 1-.303.08h-.687c-.151 0-.255-.024-.32-.08-.063-.056-.119-.16-.15-.32l-1.238-5.148-1.23 5.14c-.04.16-.087.264-.15.32-.065.056-.177.08-.32.08zm10.256.215c-.415 0-.83-.048-1.229-.143-.399-.096-.71-.2-.918-.32-.128-.071-.215-.151-.247-.223a.563.563 0 0 1-.048-.224v-.407c0-.167.064-.247.183-.247.048 0 .096.008.144.024.048.016.12.048.2.08.271.12.566.215.878.279.319.064.63.096.95.096.502 0 .894-.088 1.165-.264a.86.86 0 0 0 .415-.758.778.778 0 0 0-.215-.559c-.144-.15"
				fill="#FF9900"
			/>
		</svg>
	),
	// GitHub Copilot — logo officiel (octocat stylisé)
	copilot: (
		<svg
			width="20"
			height="20"
			viewBox="0 0 24 24"
			fill="none"
			xmlns="http://www.w3.org/2000/svg"
			role="img"
			aria-label="GitHub Copilot"
		>
			<title>GitHub Copilot</title>
			<path
				d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
				fill="#333333"
			/>
		</svg>
	),
	// Windsurf — logo Codeium (onde stylisée)
	windsurf: (
		<svg
			width="20"
			height="20"
			viewBox="0 0 24 24"
			fill="none"
			xmlns="http://www.w3.org/2000/svg"
			role="img"
			aria-label="Windsurf"
		>
			<title>Windsurf</title>
			<path
				d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5z"
				fill="#00D4AA"
			/>
			<path
				d="M12 2v20c5.16-1.26 9-6.45 9-12V7l-9-4.5z"
				fill="#00B894"
				opacity="0.8"
			/>
		</svg>
	),
	// Cursor — logo (flèche de curseur stylisée)
	cursor: (
		<svg
			width="20"
			height="20"
			viewBox="0 0 24 24"
			fill="none"
			xmlns="http://www.w3.org/2000/svg"
			role="img"
			aria-label="Cursor"
		>
			<title>Cursor</title>
			<path d="M3 3l7.07 16.97 2.51-7.39 7.39-2.51L3 3z" fill="#000000" />
			<path
				d="M3 3l7.07 16.97 2.51-7.39 7.39-2.51L3 3z"
				stroke="#000000"
				strokeWidth="2"
				strokeLinecap="round"
				strokeLinejoin="round"
			/>
		</svg>
	),
	// Grok (xAI) — logo stylisé
	grok: (
		<svg
			width="20"
			height="20"
			viewBox="0 0 24 24"
			fill="none"
			xmlns="http://www.w3.org/2000/svg"
			role="img"
			aria-label="Grok"
		>
			<title>Grok</title>
			<path
				d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5z"
				fill="#FF6B35"
			/>
			<path
				d="M12 2v20c5.16-1.26 9-6.45 9-12V7l-9-4.5z"
				fill="#E85D2D"
				opacity="0.8"
			/>
		</svg>
	),
	// Azure OpenAI — logo combiné
	"azure-openai": (
		<svg
			width="20"
			height="20"
			viewBox="0 0 24 24"
			fill="none"
			xmlns="http://www.w3.org/2000/svg"
			role="img"
			aria-label="Azure OpenAI"
		>
			<title>Azure OpenAI</title>
			<circle cx="8" cy="8" r="6" fill="#0078D4" />
			<path
				d="M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073zM13.26 22.43a4.476 4.476 0 0 1-2.876-1.04l.141-.081 4.779-2.758a.795.795 0 0 0 .392-.681v-6.737l2.02 1.168a.071.071 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494z"
				fill="#0078D4"
			/>
		</svg>
	),
};

// Fonction pour obtenir l'icône du provider avec le bon thème
const getProviderIcon = (
	providerId: string,
	_category: string,
	isConfigured: boolean,
) => {
	const icon = providerIcons[providerId];
	if (!icon) {
		// Fallback générique avec initiale
		return (
			<svg
				width="20"
				height="20"
				viewBox="0 0 20 20"
				fill="none"
				xmlns="http://www.w3.org/2000/svg"
				role="img"
				aria-label={providerId}
			>
				<title>{providerId}</title>
				<circle
					cx="10"
					cy="10"
					r="9"
					stroke={isConfigured ? "#4B5563" : "#BDBDBD"}
					strokeWidth="2"
					fill={isConfigured ? "#F5F5F5" : "#F5F5F5"}
				/>
				<text
					x="50%"
					y="55%"
					textAnchor="middle"
					fontSize="10"
					fill={isConfigured ? "#4B5563" : "#BDBDBD"}
					fontWeight="bold"
					dy=".3em"
				>
					{providerId.charAt(0).toUpperCase()}
				</text>
			</svg>
		);
	}
	return icon;
};

const categoryGradients: Record<string, string> = {
	openai: "from-emerald-500/20 to-teal-500/20 border-emerald-500/30",
	google: "from-blue-500/20 to-indigo-500/20 border-blue-500/30",
	meta: "from-purple-500/20 to-pink-500/20 border-purple-500/30",
	microsoft: "from-cyan-500/20 to-blue-500/20 border-cyan-500/30",
	independent: "from-orange-500/20 to-amber-500/20 border-orange-500/30",
};

export function ElegantProviderCard({
	provider,
	onConfigure,
	onTest,
	onToggle,
	// biome-ignore lint/correctness/noUnusedFunctionParameters: parameter kept for API compatibility
	onRemove,
	className,
}: ElegantProviderCardProps) {
	// biome-ignore lint/correctness/noUnusedVariables: variable kept for clarity
	const { t } = useTranslation("settings");
	const [isExpanded, setIsExpanded] = useState(false);
	const [isHovered, setIsHovered] = useState(false);
	const [showApiKey, setShowApiKey] = useState(false);

	// Récupérer l'icône du provider avec le bon thème
	const ProviderIcon = getProviderIcon(
		provider.id,
		provider.category,
		provider.isConfigured,
	);
	const categoryGradient =
		categoryGradients[provider.category] || categoryGradients.independent;

	const getStatusIndicator = () => {
		if (!provider.isConfigured) {
			return (
				<div className="flex items-center gap-2 px-3 py-1.5 bg-gray-100/50 rounded-full">
					<div className="w-2 h-2 bg-gray-400 rounded-full" />
					<span className="text-xs font-medium text-gray-600">
						Non configuré
					</span>
				</div>
			);
		}

		if (provider.isWorking === false) {
			return (
				<div className="flex items-center gap-2 px-3 py-1.5 bg-red-50/50 rounded-full">
					<div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
					<span className="text-xs font-medium text-red-600">Erreur</span>
				</div>
			);
		}

		return (
			<div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-50/50 rounded-full">
				<div className="w-2 h-2 bg-emerald-500 rounded-full" />
				<span className="text-xs font-medium text-emerald-600">Actif</span>
			</div>
		);
	};

	return (
		<TooltipProvider>
			{/* biome-ignore lint/a11y/noNoninteractiveElementInteractions: hover-tracking card */}
			{/* biome-ignore lint/a11y/noStaticElementInteractions: hover-tracking card */}
			<div
				className={cn(
					"group relative overflow-hidden rounded-2xl border transition-all duration-500 ease-out",
					"bg-white/80 backdrop-blur-sm",
					!provider.isConfigured && "border-gray-200/50 bg-gray-50/50",
					provider.isWorking === false && "border-red-200/50 bg-red-50/30",
					isHovered && "shadow-xl shadow-black/5 scale-[1.02]",
					categoryGradient,
					className,
				)}
				onMouseEnter={() => setIsHovered(true)}
				onMouseLeave={() => setIsHovered(false)}
			>
				{/* Subtle gradient overlay */}
				<div
					className={cn(
						"absolute inset-0 bg-linear-to-br opacity-0 transition-opacity duration-500",
						categoryGradient,
						isHovered && "opacity-100",
					)}
				/>

				{/* Content */}
				<div className="relative p-6 space-y-4">
					{/* Header */}
					<div className="flex items-start justify-between">
						<div className="flex items-center gap-4">
							{/* Icon with sophisticated background */}
							<div
								className={cn(
									"relative w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300",
									provider.isConfigured
										? "bg-linear-to-r from-white to-gray-50 shadow-lg"
										: "bg-gray-100/50",
									isHovered && "scale-110 shadow-xl",
								)}
							>
								{ProviderIcon}
								{provider.isPremium && (
									<div className="absolute -top-1 -right-1 w-4 h-4 bg-linear-to-r from-yellow-400 to-amber-500 rounded-full flex items-center justify-center">
										<Star className="w-2.5 h-2.5 text-white fill-current" />
									</div>
								)}
							</div>

							<div className="space-y-2">
								<h3 className="font-semibold text-lg text-gray-900 tracking-tight">
									{provider.name}
								</h3>
								{provider.description && (
									<p className="text-sm text-gray-600 leading-relaxed max-w-xs">
										{provider.description}
									</p>
								)}
							</div>
						</div>

						{/* Status indicator */}
						<div className="flex flex-col items-end gap-2">
							{getStatusIndicator()}

							{/* Toggle switch for configured providers */}
							{provider.isConfigured && (
								<button
									type="button"
									onClick={() =>
										onToggle(provider.id, provider.isWorking !== false)
									}
									className={cn(
										"relative w-11 h-6 rounded-full transition-colors duration-200",
										provider.isWorking === false
											? "bg-gray-200"
											: "bg-emerald-500",
									)}
								>
									<div
										className={cn(
											"absolute top-0.5 w-5 h-5 bg-white rounded-full shadow-md transition-transform duration-200",
											provider.isWorking === false
												? "translate-x-0.5"
												: "translate-x-5",
										)}
									/>
								</button>
							)}
						</div>
					</div>

					{/* Actions */}
					<div className="flex items-center justify-between">
						<div className="flex gap-2">
							{!provider.isConfigured ? (
								<Button
									onClick={() => onConfigure(provider.id)}
									className={cn(
										"px-4 py-2 text-sm font-medium rounded-xl transition-all duration-200",
										"bg-gray-900 text-white hover:bg-gray-800 hover:shadow-lg hover:scale-105",
										"active:scale-95",
									)}
								>
									<Key className="w-4 h-4 mr-2" />
									Configurer
								</Button>
							) : (
								<>
									<Button
										onClick={() => onTest(provider.id)}
										variant="ghost"
										className={cn(
											"px-3 py-2 text-sm font-medium rounded-xl transition-all duration-200",
											"hover:bg-gray-100 hover:shadow-md hover:scale-105",
											"active:scale-95",
										)}
									>
										<Zap className="w-4 h-4 mr-2" />
										Tester
									</Button>
									<Button
										onClick={() => onConfigure(provider.id)}
										variant="ghost"
										className={cn(
											"px-3 py-2 text-sm font-medium rounded-xl transition-all duration-200",
											"hover:bg-gray-100 hover:shadow-md hover:scale-105",
											"active:scale-95",
										)}
									>
										<Settings2 className="w-4 h-4 mr-2" />
										Modifier
									</Button>
								</>
							)}
						</div>

						{/* Expand button */}
						<Button
							variant="ghost"
							size="sm"
							onClick={() => setIsExpanded(!isExpanded)}
							className={cn(
								"w-8 h-8 rounded-lg transition-all duration-200",
								"hover:bg-gray-100 hover:scale-110",
								"active:scale-95",
							)}
						>
							{isExpanded ? (
								<ChevronUp className="w-4 h-4 text-gray-600" />
							) : (
								<ChevronDown className="w-4 h-4 text-gray-600" />
							)}
						</Button>
					</div>

					{/* Expanded details */}
					{isExpanded && provider.isConfigured && (
						<div className="pt-4 border-t border-gray-200/50 space-y-3 animate-in slide-in-from-top-2 duration-300">
							<div className="flex items-center justify-between">
								<span className="text-sm font-medium text-gray-700">
									Clé API
								</span>
								<div className="flex items-center gap-2">
									<div className="px-3 py-1.5 bg-gray-100/50 rounded-lg font-mono text-xs text-gray-600">
										{showApiKey
											? "sk-..."
											: "sk-...••••••••••••••••••••••••••••••••"}
									</div>
									<Button
										variant="ghost"
										size="sm"
										onClick={() => setShowApiKey(!showApiKey)}
										className="w-6 h-6 rounded hover:bg-gray-100"
									>
										{showApiKey ? (
											<EyeOff className="w-3.5 h-3.5 text-gray-500" />
										) : (
											<Eye className="w-3.5 h-3.5 text-gray-500" />
										)}
									</Button>
								</div>
							</div>

							{provider.lastTested && (
								<div className="flex items-center justify-between text-xs text-gray-500">
									<span>Dernier test</span>
									<span>
										{new Date(provider.lastTested).toLocaleDateString()}
									</span>
								</div>
							)}

							{provider.usageCount && (
								<div className="flex items-center justify-between text-xs text-gray-500">
									<span>Utilisations ce mois</span>
									<span className="font-medium text-gray-700">
										{provider.usageCount}
									</span>
								</div>
							)}
						</div>
					)}
				</div>

				{/* Subtle shimmer effect on hover */}
				{isHovered && (
					<div className="absolute inset-0 bg-linear-to-r from-transparent via-white/10 to-transparent -translate-x-full animate-pulse" />
				)}
			</div>
		</TooltipProvider>
	);
}
