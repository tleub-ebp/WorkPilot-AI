import type { PluginType } from "@shared/types/plugin-marketplace";
import { PackageOpen, Power, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import {
	togglePlugin,
	uninstallPlugin,
	usePluginMarketplaceStore,
} from "@/stores/plugin-marketplace-store";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Switch } from "../ui/switch";

const TYPE_COLORS: Record<PluginType, string> = {
	agent: "bg-purple-500/10 text-purple-500",
	integration: "bg-blue-500/10 text-blue-500",
	"spec-template": "bg-green-500/10 text-green-500",
	theme: "bg-orange-500/10 text-orange-500",
	"custom-prompt": "bg-pink-500/10 text-pink-500",
};

export function InstalledPluginsView() {
	const { t } = useTranslation(["common"]);
	const { installed, isInstalledLoading } = usePluginMarketplaceStore();

	const typeLabel: Record<PluginType, string> = {
		agent: t("common:pluginMarketplace.types.agent"),
		integration: t("common:pluginMarketplace.types.integration"),
		"spec-template": t("common:pluginMarketplace.types.specTemplate"),
		theme: t("common:pluginMarketplace.types.theme"),
		"custom-prompt": t("common:pluginMarketplace.types.customPrompt"),
	};

	if (isInstalledLoading) {
		return (
			<div className="flex items-center justify-center h-full">
				<div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" />
			</div>
		);
	}

	if (installed.length === 0) {
		return (
			<div className="flex flex-col items-center justify-center h-full gap-3 text-muted-foreground">
				<PackageOpen className="h-10 w-10 opacity-40" />
				<p className="text-sm font-medium">
					{t("common:pluginMarketplace.noInstalledPlugins")}
				</p>
				<p className="text-xs">
					{t("common:pluginMarketplace.browseToInstall")}
				</p>
			</div>
		);
	}

	return (
		<div className="flex flex-col h-full overflow-y-auto px-6 py-4">
			<p className="text-xs text-muted-foreground mb-4">
				{t("common:pluginMarketplace.installedCount", {
					count: installed.length,
				})}
			</p>
			<div className="space-y-3">
				{installed.map((plugin) => (
					<div
						key={plugin.pluginId}
						className={cn(
							"flex items-center justify-between rounded-xl border border-border bg-card p-4",
							"transition-opacity duration-200",
							!plugin.enabled && "opacity-60",
						)}
					>
						<div className="min-w-0 flex-1">
							<div className="flex items-center gap-2">
								<span className="font-medium text-sm">{plugin.name}</span>
								<Badge variant="secondary" className="text-[10px]">
									v{plugin.version}
								</Badge>
								<span
									className={cn(
										"rounded-full px-2 py-0.5 text-[10px] font-medium",
										TYPE_COLORS[plugin.type],
									)}
								>
									{typeLabel[plugin.type]}
								</span>
							</div>
							<p className="text-xs text-muted-foreground mt-0.5">
								{t("common:pluginMarketplace.installedOn", {
									date: new Date(plugin.installedAt).toLocaleDateString(),
								})}
							</p>
						</div>

						<div className="flex items-center gap-3 shrink-0">
							<div className="flex items-center gap-2">
								<Power className="h-3.5 w-3.5 text-muted-foreground" />
								<Switch
									checked={plugin.enabled}
									onCheckedChange={(checked) =>
										togglePlugin(plugin.pluginId, checked)
									}
									aria-label={
										plugin.enabled
											? t("common:pluginMarketplace.actions.disable")
											: t("common:pluginMarketplace.actions.enable")
									}
								/>
							</div>
							<Button
								variant="ghost"
								size="icon"
								className="h-7 w-7 text-muted-foreground hover:text-destructive"
								onClick={() => uninstallPlugin(plugin.pluginId)}
							>
								<Trash2 className="h-3.5 w-3.5" />
							</Button>
						</div>
					</div>
				))}
			</div>
		</div>
	);
}
