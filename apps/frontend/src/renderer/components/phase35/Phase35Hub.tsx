/**
 * Tabbed page that aggregates the 12 Phase 3-5 panels.
 *
 * Used as a single entry point in the sidebar so users can discover all
 * the new features without us having to thread 12 separate routes.
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../ui/button";
import { AgentHealthPanel } from "./AgentHealthPanel";
import { ArchDriftPanel } from "./ArchDriftPanel";
import { AuditTrailPanel } from "./AuditTrailPanel";
import { CicdAnomalyPanel } from "./CicdAnomalyPanel";
import { CogContextPanel } from "./CogContextPanel";
import { DomainAgentsPanel } from "./DomainAgentsPanel";
import { GenTestsPanel } from "./GenTestsPanel";
import { I18nScalerPanel } from "./I18nScalerPanel";
import { LicensePanel } from "./LicensePanel";
import { LongevityPanel } from "./LongevityPanel";
import { ModelRouterPanel } from "./ModelRouterPanel";
import { PairProgrammingPanel } from "./PairProgrammingPanel";

interface Phase35HubProps {
	projectPath?: string;
}

type TabId =
	| "longevity"
	| "agentHealth"
	| "modelRouter"
	| "domainAgents"
	| "cicdAnomaly"
	| "license"
	| "archDrift"
	| "genTests"
	| "i18nScaler"
	| "cogContext"
	| "audit"
	| "pair";

export function Phase35Hub({ projectPath = "" }: Phase35HubProps) {
	const { t } = useTranslation("phase35");
	const [tab, setTab] = useState<TabId>("longevity");

	const tabs: { id: TabId; titleKey: string }[] = [
		{ id: "longevity", titleKey: "longevity.title" },
		{ id: "agentHealth", titleKey: "agentHealth.title" },
		{ id: "modelRouter", titleKey: "modelRouter.title" },
		{ id: "domainAgents", titleKey: "domainAgents.title" },
		{ id: "cicdAnomaly", titleKey: "cicdAnomaly.title" },
		{ id: "license", titleKey: "license.title" },
		{ id: "archDrift", titleKey: "archDrift.title" },
		{ id: "genTests", titleKey: "genTests.title" },
		{ id: "i18nScaler", titleKey: "i18nScaler.title" },
		{ id: "cogContext", titleKey: "cogContext.title" },
		{ id: "audit", titleKey: "audit.title" },
		{ id: "pair", titleKey: "pair.title" },
	];

	return (
		<div className="flex h-full">
			<aside className="w-56 border-r bg-muted/20 p-2 overflow-y-auto">
				<nav className="space-y-1">
					{tabs.map((tabItem) => (
						<Button
							key={tabItem.id}
							variant={tab === tabItem.id ? "secondary" : "ghost"}
							size="sm"
							className="w-full justify-start text-left"
							onClick={() => setTab(tabItem.id)}
						>
							{t(tabItem.titleKey as never)}
						</Button>
					))}
				</nav>
			</aside>

			<main className="flex-1 p-4 overflow-y-auto">
				{tab === "longevity" && <LongevityPanel projectPath={projectPath} />}
				{tab === "agentHealth" && <AgentHealthPanel />}
				{tab === "modelRouter" && <ModelRouterPanel />}
				{tab === "domainAgents" && <DomainAgentsPanel />}
				{tab === "cicdAnomaly" && <CicdAnomalyPanel />}
				{tab === "license" && <LicensePanel projectPath={projectPath} />}
				{tab === "archDrift" && <ArchDriftPanel projectPath={projectPath} />}
				{tab === "genTests" && <GenTestsPanel projectPath={projectPath} />}
				{tab === "i18nScaler" && <I18nScalerPanel />}
				{tab === "cogContext" && <CogContextPanel />}
				{tab === "audit" && <AuditTrailPanel />}
				{tab === "pair" && <PairProgrammingPanel />}
			</main>
		</div>
	);
}
