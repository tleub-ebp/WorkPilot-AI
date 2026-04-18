import {
	ArrowDownUp,
	BarChart3,
	FlaskConical,
	Router,
	Zap,
} from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { SettingsSection } from "./SettingsSection";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type RoutingStrategy =
	| "best_performance"
	| "cheapest"
	| "lowest_latency"
	| "round_robin";

interface ProviderEntry {
	provider: string;
	model: string;
	capabilities: string[];
	priority: number;
	isLocal: boolean;
	enabled: boolean;
}

interface FallbackChain {
	taskType: string;
	chain: string[];
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function LlmRouterSettings() {
	const { t } = useTranslation("settings");
	const [strategy, setStrategy] = useState<RoutingStrategy>("best_performance");

	const [providers] = useState<ProviderEntry[]>([
		{
			provider: "Anthropic",
			model: "claude-opus-4-6",
			capabilities: ["coding", "planning", "review"],
			priority: 1,
			isLocal: false,
			enabled: true,
		},
		{
			provider: "OpenAI",
			model: "gpt-5.4",
			capabilities: ["coding", "review"],
			priority: 2,
			isLocal: false,
			enabled: true,
		},
		{
			provider: "Google",
			model: "gemini-3.1-pro",
			capabilities: ["coding", "planning"],
			priority: 3,
			isLocal: false,
			enabled: true,
		},
		{
			provider: "Mistral",
			model: "mistral-large-3",
			capabilities: ["coding", "planning"],
			priority: 4,
			isLocal: false,
			enabled: false,
		},
		{
			provider: "DeepSeek",
			model: "deepseek-v3.2",
			capabilities: ["coding", "review"],
			priority: 5,
			isLocal: false,
			enabled: true,
		},
		{
			provider: "GitHub Copilot",
			model: "gpt-5.4",
			capabilities: ["coding", "quick_feedback"],
			priority: 6,
			isLocal: false,
			enabled: true,
		},
		{
			provider: "Grok",
			model: "grok-2",
			capabilities: ["coding", "planning"],
			priority: 7,
			isLocal: false,
			enabled: false,
		},
		{
			provider: "Windsurf",
			model: "swe-1.5",
			capabilities: ["coding", "review"],
			priority: 8,
			isLocal: false,
			enabled: false,
		},
		{
			provider: "Ollama",
			model: "llama3.3",
			capabilities: ["quick_feedback", "coding"],
			priority: 9,
			isLocal: true,
			enabled: true,
		},
	]);

	const [fallbacks] = useState<FallbackChain[]>([
		{
			taskType: "coding",
			chain: [
				"Anthropic / claude-opus-4-6",
				"OpenAI / gpt-5.4",
				"DeepSeek / deepseek-v3.2",
				"GitHub Copilot / gpt-5.4",
				"Ollama / llama3.3",
			],
		},
		{
			taskType: "planning",
			chain: [
				"Anthropic / claude-opus-4-6",
				"Google / gemini-3.1-pro",
				"Grok / grok-2",
				"Mistral / mistral-large-3",
			],
		},
		{
			taskType: "review",
			chain: [
				"Anthropic / claude-opus-4-6",
				"OpenAI / gpt-5.4",
				"DeepSeek / deepseek-v3.2",
				"Windsurf / swe-1.5",
			],
		},
		{
			taskType: "quick_feedback",
			chain: [
				"GitHub Copilot / gpt-5.4",
				"Ollama / llama3.3",
				"DeepSeek / deepseek-v3.2",
			],
		},
	]);

	const strategies: {
		id: RoutingStrategy;
		label: string;
		desc: string;
		icon: React.ReactNode;
	}[] = [
		{
			id: "best_performance",
			label: t("llmRouter.routingStrategy.bestPerformance"),
			desc: t("llmRouter.routingStrategy.bestPerformanceDescription"),
			icon: <Zap className="h-4 w-4" />,
		},
		{
			id: "cheapest",
			label: t("llmRouter.routingStrategy.cheapest"),
			desc: t("llmRouter.routingStrategy.cheapestDescription"),
			icon: <ArrowDownUp className="h-4 w-4" />,
		},
		{
			id: "lowest_latency",
			label: t("llmRouter.routingStrategy.lowestLatency"),
			desc: t("llmRouter.routingStrategy.lowestLatencyDescription"),
			icon: <BarChart3 className="h-4 w-4" />,
		},
		{
			id: "round_robin",
			label: t("llmRouter.routingStrategy.roundRobin"),
			desc: t("llmRouter.routingStrategy.roundRobinDescription"),
			icon: <Router className="h-4 w-4" />,
		},
	];

	return (
		<SettingsSection
			title={t("llmRouter.title")}
			description={t("llmRouter.description")}
		>
			<div className="space-y-8">
				{/* Routing Strategy */}
				<div>
					<h4 className="text-sm font-semibold mb-1 flex items-center gap-2">
						<Router className="h-4 w-4 text-primary" />
						{t("llmRouter.routingStrategy.title")}
					</h4>
					<p className="text-xs text-muted-foreground mb-3">
						{t("llmRouter.routingStrategy.description")}
					</p>
					<div className="grid grid-cols-2 gap-3">
						{strategies.map((s) => (
							<button
								type="button"
								key={s.id}
								onClick={() => setStrategy(s.id)}
								className={cn(
									"flex items-start gap-3 rounded-lg border p-3 text-left transition-colors",
									strategy === s.id
										? "border-primary bg-primary/5 ring-1 ring-primary"
										: "border-border hover:bg-accent/50",
								)}
							>
								<span
									className={cn(
										"mt-0.5",
										strategy === s.id
											? "text-primary"
											: "text-muted-foreground",
									)}
								>
									{s.icon}
								</span>
								<div>
									<span className="text-sm font-medium">{s.label}</span>
									<p className="text-xs text-muted-foreground">{s.desc}</p>
								</div>
							</button>
						))}
					</div>
				</div>

				{/* Registered Providers */}
				<div>
					<h4 className="text-sm font-semibold mb-1 flex items-center gap-2">
						<Zap className="h-4 w-4 text-primary" />
						{t("llmRouter.registeredProviders.title")}
					</h4>
					<p className="text-xs text-muted-foreground mb-3">
						{t("llmRouter.registeredProviders.description")}
					</p>
					<div className="rounded-md border border-border overflow-hidden">
						<table className="w-full text-xs">
							<thead>
								<tr className="border-b border-border bg-muted/40">
									<th className="text-left px-3 py-2 font-medium text-muted-foreground">
										{t("llmRouter.registeredProviders.table.providerModel")}
									</th>
									<th className="text-left px-3 py-2 font-medium text-muted-foreground">
										{t("llmRouter.registeredProviders.table.capabilities")}
									</th>
									<th className="text-center px-3 py-2 font-medium text-muted-foreground">
										{t("llmRouter.registeredProviders.table.priority")}
									</th>
									<th className="text-center px-3 py-2 font-medium text-muted-foreground">
										{t("llmRouter.registeredProviders.table.status")}
									</th>
								</tr>
							</thead>
							<tbody>
								{providers.map((p) => (
									<tr
										key={`${p.provider}-${p.model}`}
										className="border-b border-border last:border-0"
									>
										<td className="px-3 py-2">
											<div className="flex items-center gap-2">
												<span className="font-medium">{p.provider}</span>
												<span className="text-muted-foreground">
													/ {p.model}
												</span>
												{p.isLocal && (
													<span className="rounded-full bg-green-500/15 text-green-600 px-1.5 py-0 text-[10px] font-medium">
														{t("llmRouter.registeredProviders.status.local")}
													</span>
												)}
											</div>
										</td>
										<td className="px-3 py-2">
											<div className="flex flex-wrap gap-1">
												{p.capabilities.map((c) => (
													<span
														key={c}
														className="rounded bg-accent px-1.5 py-0 text-[10px]"
													>
														{c}
													</span>
												))}
											</div>
										</td>
										<td className="px-3 py-2 text-center font-mono">
											{p.priority}
										</td>
										<td className="px-3 py-2 text-center">
											<span
												className={cn(
													"rounded-full px-2 py-0.5 text-[10px] font-medium",
													p.enabled
														? "bg-green-500/15 text-green-600"
														: "bg-muted text-muted-foreground",
												)}
											>
												{p.enabled
													? t("llmRouter.registeredProviders.status.active")
													: t("llmRouter.registeredProviders.status.disabled")}
											</span>
										</td>
									</tr>
								))}
							</tbody>
						</table>
					</div>
				</div>

				{/* Fallback Chains */}
				<div>
					<h4 className="text-sm font-semibold mb-1 flex items-center gap-2">
						<ArrowDownUp className="h-4 w-4 text-primary" />
						{t("llmRouter.fallbackChains.title")}
					</h4>
					<p className="text-xs text-muted-foreground mb-3">
						{t("llmRouter.fallbackChains.description")}
					</p>
					<div className="space-y-3">
						{fallbacks.map((fb) => (
							<div
								key={fb.taskType}
								className="rounded-md border border-border p-3"
							>
								<p className="text-xs font-semibold text-foreground mb-2 capitalize">
									{fb.taskType}
								</p>
								<div className="flex items-center gap-1.5 flex-wrap">
									{fb.chain.map((entry) => (
										<span
											key={`${fb.taskType}-${entry}`}
											className="flex items-center gap-1.5"
										>
											<span className="rounded bg-accent px-2 py-0.5 text-[10px] font-mono">
												{entry}
											</span>
											{fb.chain.indexOf(entry) < fb.chain.length - 1 && (
												<span className="text-muted-foreground text-xs">→</span>
											)}
										</span>
									))}
								</div>
							</div>
						))}
					</div>
				</div>

				{/* A/B Testing */}
				<div>
					<h4 className="text-sm font-semibold mb-1 flex items-center gap-2">
						<FlaskConical className="h-4 w-4 text-primary" />
						{t("llmRouter.abTesting.title")}
					</h4>
					<p className="text-xs text-muted-foreground mb-3">
						{t("llmRouter.abTesting.description")}
					</p>
					<div className="rounded-md border border-dashed border-border bg-muted/20 p-6 text-center">
						<FlaskConical className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
						<p className="text-sm text-muted-foreground">
							{t("llmRouter.abTesting.noActiveTests")}
						</p>
						<p className="text-xs text-muted-foreground mt-1">
							{t("llmRouter.abTesting.createTest")}
						</p>
					</div>
				</div>
			</div>
		</SettingsSection>
	);
}
