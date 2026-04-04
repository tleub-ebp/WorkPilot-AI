import {
	AlertCircle,
	AlertTriangle,
	Box,
	Database,
	FileCode,
	Gauge,
	HardDrive,
	TrendingUp,
	Wifi,
	Wrench,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import {
	IDEATION_EFFORT_COLORS,
	IDEATION_IMPACT_COLORS,
	PERFORMANCE_CATEGORY_LABELS,
} from "../../../../shared/constants";
import type { PerformanceOptimizationIdea } from "../../../../shared/types";
import { Badge } from "../../ui/badge";
import { Card } from "../../ui/card";

interface PerformanceOptimizationDetailsProps {
	readonly idea: PerformanceOptimizationIdea;
}

// Get an icon for the performance category
function getCategoryIcon(category: string) {
	switch (category) {
		case "bundle_size":
			return <Box className="h-4 w-4" />;
		case "database":
			return <Database className="h-4 w-4" />;
		case "network":
			return <Wifi className="h-4 w-4" />;
		case "memory":
			return <HardDrive className="h-4 w-4" />;
		default:
			return <Gauge className="h-4 w-4" />;
	}
}

export function PerformanceOptimizationDetails({
	idea,
}: PerformanceOptimizationDetailsProps) {
	const { t } = useTranslation("ideation");

	return (
		<>
			{/* Metrics */}
			<div className="grid grid-cols-2 gap-2">
				<Card className="p-3 text-center">
					<div
						className={`text-lg font-semibold ${IDEATION_IMPACT_COLORS[idea.impact]}`}
					>
						{idea.impact}
					</div>
					<div className="text-xs text-muted-foreground">
						{t("performanceDetails.impact")}
					</div>
				</Card>
				<Card className="p-3 text-center">
					<div
						className={`text-lg font-semibold ${IDEATION_EFFORT_COLORS[idea.estimatedEffort]}`}
					>
						{idea.estimatedEffort}
					</div>
					<div className="text-xs text-muted-foreground">
						{t("performanceDetails.effort")}
					</div>
				</Card>
			</div>

			{/* Category */}
			<div>
				<h3 className="text-sm font-medium mb-2 flex items-center gap-2">
					{getCategoryIcon(idea.category)}
					{t("performanceDetails.category")}
				</h3>
				<Badge variant="outline">
					{PERFORMANCE_CATEGORY_LABELS[idea.category]}
				</Badge>
			</div>

			{/* Current Metric */}
			{idea.currentMetric && (
				<div>
					<h3 className="text-sm font-medium mb-2 flex items-center gap-2">
						<AlertCircle className="h-4 w-4" />
						{t("performanceDetails.currentState")}
					</h3>
					<p className="text-sm text-muted-foreground">{idea.currentMetric}</p>
				</div>
			)}

			{/* Expected Improvement */}
			<div>
				<h3 className="text-sm font-medium mb-2 flex items-center gap-2">
					<TrendingUp className="h-4 w-4 text-success" />
					{t("performanceDetails.expectedImprovement")}
				</h3>
				<p className="text-sm text-muted-foreground">
					{idea.expectedImprovement}
				</p>
			</div>

			{/* Implementation */}
			<div>
				<h3 className="text-sm font-medium mb-2 flex items-center gap-2">
					<Wrench className="h-4 w-4" />
					{t("performanceDetails.implementation")}
				</h3>
				<p className="text-sm text-muted-foreground whitespace-pre-line">
					{idea.implementation}
				</p>
			</div>

			{/* Affected Areas */}
			{idea.affectedAreas && idea.affectedAreas.length > 0 && (
				<div>
					<h3 className="text-sm font-medium mb-2 flex items-center gap-2">
						<FileCode className="h-4 w-4" />
						{t("performanceDetails.affectedAreas")}
					</h3>
					<ul className="space-y-1">
						{idea.affectedAreas.map((area) => (
							<li
								key={area}
								className="text-sm font-mono text-muted-foreground"
							>
								{area}
							</li>
						))}
					</ul>
				</div>
			)}

			{/* Tradeoffs */}
			{idea.tradeoffs && (
				<div>
					<h3 className="text-sm font-medium mb-2 flex items-center gap-2">
						<AlertTriangle className="h-4 w-4 text-warning" />
						{t("performanceDetails.tradeoffs")}
					</h3>
					<p className="text-sm text-muted-foreground">{idea.tradeoffs}</p>
				</div>
			)}
		</>
	);
}
