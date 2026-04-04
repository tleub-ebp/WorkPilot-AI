import {
	BookOpen,
	Code,
	Package,
	Puzzle,
	Sparkles,
	Terminal,
} from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { PluginCreatorWizard } from "./PluginCreatorWizard";

const SDK_SECTIONS = [
	{
		icon: Puzzle,
		titleKey: "common:pluginMarketplace.sdk.gettingStarted",
		color: "#8b5cf6",
		descKey: "common:pluginMarketplace.sdk.gettingStartedDesc",
		codeSnippet: `# Install the WorkPilot Plugin SDK
npm install @workpilot/plugin-sdk

# Scaffold a new plugin
npx @workpilot/plugin-sdk create my-plugin --type agent`,
	},
	{
		icon: Code,
		titleKey: "common:pluginMarketplace.sdk.pluginStructure",
		color: "#10b981",
		descKey: "common:pluginMarketplace.sdk.pluginStructureDesc",
		codeSnippet: `// plugin.config.ts
export default {
  id: 'my-awesome-agent',
  name: 'My Awesome Agent',
  type: 'agent',
  version: '1.0.0',
  description: 'Does awesome things',
  systemPrompt: 'You are an expert at...',
  triggers: ['do awesome', 'run awesome'],
};`,
	},
	{
		icon: Package,
		titleKey: "common:pluginMarketplace.sdk.publishing",
		color: "#f59e0b",
		descKey: "common:pluginMarketplace.sdk.publishingDesc",
		codeSnippet: `# Validate your plugin
npx @workpilot/plugin-sdk validate

# Build and publish
npx @workpilot/plugin-sdk publish --registry https://plugins.workpilot.ai`,
	},
	{
		icon: Terminal,
		titleKey: "common:pluginMarketplace.sdk.testingLocally",
		color: "#06b6d4",
		descKey: "common:pluginMarketplace.sdk.testingLocallyDesc",
		codeSnippet: `# Load a local plugin in dev mode
# Add to your .workpilot/plugins/local.json:
{
  "localPlugins": [
    { "path": "/path/to/my-plugin", "enabled": true }
  ]
}`,
	},
];

const PLUGIN_TYPES = [
	{
		type: "agent",
		color: "#8b5cf6",
		descKey: "common:pluginMarketplace.sdk.typeDesc.agent",
	},
	{
		type: "integration",
		color: "#3b82f6",
		descKey: "common:pluginMarketplace.sdk.typeDesc.integration",
	},
	{
		type: "spec-template",
		color: "#10b981",
		descKey: "common:pluginMarketplace.sdk.typeDesc.specTemplate",
	},
	{
		type: "theme",
		color: "#f97316",
		descKey: "common:pluginMarketplace.sdk.typeDesc.theme",
	},
	{
		type: "custom-prompt",
		color: "#ec4899",
		descKey: "common:pluginMarketplace.sdk.typeDesc.customPrompt",
	},
];

export function PluginSDKView() {
	const { t } = useTranslation(["common"]);
	const [showCreator, setShowCreator] = useState(false);

	if (showCreator) {
		return <PluginCreatorWizard onClose={() => setShowCreator(false)} />;
	}

	return (
		<div className="flex flex-col h-full overflow-y-auto">
			{/* Hero section */}
			<div className="shrink-0 border-b border-border bg-gradient-to-b from-primary/5 to-transparent px-6 py-8">
				<div className="max-w-2xl">
					<div className="flex items-center gap-3 mb-3">
						<div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
							<BookOpen className="h-5 w-5 text-primary" />
						</div>
						<h2 className="text-xl font-bold">
							{t("common:pluginMarketplace.sdk.title")}
						</h2>
					</div>
					<p className="text-sm text-muted-foreground leading-relaxed">
						{t("common:pluginMarketplace.sdk.description")}
					</p>
					<div className="flex gap-3 mt-4">
						<button
							type="button"
							onClick={() => setShowCreator(true)}
							className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
						>
							<Sparkles className="h-3.5 w-3.5" />
							{t("common:pluginMarketplace.creator.createPlugin")}
						</button>
					</div>
				</div>
			</div>

			{/* SDK sections */}
			<div className="px-6 py-6 space-y-6">
				{SDK_SECTIONS.map(
					({ icon: Icon, titleKey, color, descKey, codeSnippet }) => (
						<div
							key={titleKey}
							className="rounded-xl border border-border bg-card overflow-hidden"
						>
							<div className="flex items-center gap-3 p-4 border-b border-border/50">
								<div
									className="flex h-8 w-8 items-center justify-center rounded-lg"
									style={{ backgroundColor: `${color}20` }}
								>
									<Icon className="h-4 w-4" style={{ color }} />
								</div>
								<h3 className="font-semibold text-sm">{t(titleKey)}</h3>
							</div>
							<div className="p-4 space-y-3">
								<p className="text-xs text-muted-foreground leading-relaxed">
									{t(descKey)}
								</p>
								<pre
									className={cn(
										"rounded-lg bg-muted/60 p-3 text-xs font-mono overflow-x-auto",
										"border border-border/50 text-foreground/80 leading-relaxed",
									)}
								>
									{codeSnippet}
								</pre>
							</div>
						</div>
					),
				)}

				{/* Plugin types reference */}
				<div className="rounded-xl border border-border bg-card p-4">
					<h3 className="font-semibold text-sm mb-3">
						{t("common:pluginMarketplace.sdk.pluginTypes")}
					</h3>
					<div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
						{PLUGIN_TYPES.map(({ type, color, descKey }) => (
							<div
								key={type}
								className="flex items-start gap-2.5 p-2.5 rounded-lg bg-muted/40"
							>
								<div
									className="w-2 h-2 rounded-full mt-1.5 shrink-0"
									style={{ backgroundColor: color }}
								/>
								<div>
									<p className="text-xs font-medium font-mono">{type}</p>
									<p className="text-[10px] text-muted-foreground mt-0.5">
										{t(descKey)}
									</p>
								</div>
							</div>
						))}
					</div>
				</div>
			</div>
		</div>
	);
}
