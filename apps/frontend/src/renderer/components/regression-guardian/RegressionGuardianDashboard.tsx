import type React from "react";
import type {
	Incident,
	RegressionGuardianResult,
} from "../../../shared/types/regression-guardian";

const SEVERITY_COLORS: Record<string, string> = {
	critical: "text-red-400 bg-red-500/10 border-red-500/20",
	error: "text-orange-400 bg-orange-500/10 border-orange-500/20",
	warning: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
	info: "text-blue-400 bg-blue-500/10 border-blue-500/20",
};

interface RegressionGuardianDashboardProps {
	readonly results: RegressionGuardianResult[];
	readonly onViewTest?: (result: RegressionGuardianResult) => void;
}

export function RegressionGuardianDashboard({
	results,
	onViewTest,
}: RegressionGuardianDashboardProps): React.ReactElement {
	if (!results) {
		return (
			<div className="flex items-center justify-center h-full text-(--text-secondary)">
				<p>No regression guardian data available</p>
			</div>
		);
	}

	const generated = results.filter((r) => r.generatedTest && !r.isDuplicate);
	const duplicates = results.filter((r) => r.isDuplicate);

	return (
		<div className="flex flex-col gap-4 p-6 bg-(--bg-primary) text-(--text-primary)">
			<div>
				<h2 className="text-lg font-semibold">Regression Guardian</h2>
				<p className="text-sm text-(--text-secondary)">
					{results.length} incidents detected
				</p>
			</div>

			{/* Stats */}
			<div className="grid grid-cols-3 gap-3">
				<StatCard
					label="Incidents"
					value={results.length}
					color="text-blue-400"
				/>
				<StatCard
					label="Tests Generated"
					value={generated.length}
					color="text-green-400"
				/>
				<StatCard
					label="Duplicates Skipped"
					value={duplicates.length}
					color="text-yellow-400"
				/>
			</div>

			{/* Results list */}
			<div className="space-y-2">
				{results.map((result) => (
					<IncidentRow
						key={result.incident.id}
						incident={result.incident}
						hasTest={!!result.generatedTest}
						isDuplicate={result.isDuplicate}
						onView={() => onViewTest?.(result)}
					/>
				))}
			</div>
		</div>
	);
}

function StatCard({
	label,
	value,
	color,
}: {
	readonly label: string;
	readonly value: number;
	readonly color: string;
}): React.ReactElement {
	return (
		<div className="p-3 rounded-lg bg-(--bg-secondary) border border-(--border-color)">
			<p className="text-xs text-(--text-secondary)">{label}</p>
			<p className={`text-2xl font-bold ${color}`}>{value}</p>
		</div>
	);
}

function IncidentRow({
	incident,
	hasTest,
	isDuplicate,
	onView,
}: {
	readonly incident: Incident;
	readonly hasTest: boolean;
	readonly isDuplicate: boolean;
	readonly onView: () => void;
}): React.ReactElement {
	let actionContent: React.ReactNode;
	if (isDuplicate) {
		actionContent = <span className="text-xs text-yellow-400">Duplicate</span>;
	} else if (hasTest) {
		actionContent = (
			<button
				type="button"
				onClick={onView}
				className="px-3 py-1 text-xs rounded bg-green-500/20 text-green-400 hover:bg-green-500/30 transition-colors"
			>
				View Test
			</button>
		);
	} else {
		actionContent = (
			<span className="text-xs text-(--text-secondary)">
				No test
			</span>
		);
	}

	return (
		<div className="flex items-center gap-3 px-4 py-3 rounded-lg border border-(--border-color) hover:bg-(--bg-secondary) transition-colors">
			<span
				className={`px-2 py-0.5 rounded text-xs font-medium border ${SEVERITY_COLORS[incident.severity] ?? ""}`}
			>
				{incident.severity}
			</span>
			<div className="flex-1 min-w-0">
				<p className="text-sm font-medium truncate">{incident.title}</p>
				<p className="text-xs text-(--text-secondary)">
					{incident.source} · {incident.exceptionType || "unknown"}
				</p>
			</div>
			{actionContent}
		</div>
	);
}
