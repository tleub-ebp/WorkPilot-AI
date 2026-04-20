import { AlertTriangle, Radar, Target } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useBlastRadiusStore } from "../../stores/blast-radius-store";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";

const SCORE_STYLES: Record<"low" | "medium" | "high", string> = {
	low: "bg-green-500/15 text-green-500 border-green-500/30",
	medium: "bg-yellow-500/15 text-yellow-500 border-yellow-500/30",
	high: "bg-red-500/15 text-red-500 border-red-500/30",
};

interface Props {
	readonly projectRoot?: string;
}

export function BlastRadiusView({ projectRoot }: Props) {
	const { t } = useTranslation(["blastRadius", "common"]);
	const { report, loading, error, analyze } = useBlastRadiusStore();
	const [rootInput, setRootInput] = useState(projectRoot ?? "");
	const [targetsInput, setTargetsInput] = useState("");

	const handleAnalyze = () => {
		const targets = targetsInput
			.split(/[\n,]/)
			.map((s) => s.trim())
			.filter(Boolean);
		if (!rootInput.trim() || targets.length === 0) return;
		void analyze(rootInput.trim(), targets);
	};

	return (
		<div className="flex flex-col gap-3 p-4">
			<div className="flex items-center gap-2">
				<Radar className="w-4 h-4" />
				<h3 className="text-base font-semibold">
					{t("blastRadius:title", "Blast Radius")}
				</h3>
			</div>

			<div className="grid grid-cols-1 gap-2">
				<div>
					<Label className="text-xs">
						{t("blastRadius:projectRoot", "Project root")}
					</Label>
					<Input
						value={rootInput}
						onChange={(e) => setRootInput(e.target.value)}
						placeholder="/path/to/repo"
					/>
				</div>
				<div>
					<Label className="text-xs">
						{t("blastRadius:targets", "Target files (comma or newline separated)")}
					</Label>
					<textarea
						className="w-full min-h-[70px] rounded-md border border-border bg-card px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
						value={targetsInput}
						onChange={(e) => setTargetsInput(e.target.value)}
						placeholder="src/core/client.ts,src/utils/hash.ts"
					/>
				</div>
				<Button
					size="sm"
					onClick={handleAnalyze}
					disabled={loading || !rootInput.trim() || !targetsInput.trim()}
				>
					<Target className="w-3 h-3 mr-1" />
					{loading
						? t("blastRadius:analyzing", "Analyzing…")
						: t("blastRadius:analyze", "Analyze")}
				</Button>
			</div>

			{error && <p className="text-sm text-destructive">{error}</p>}

			{report && (
				<section className="border rounded-md p-3 bg-card space-y-3">
					<div className="flex items-center justify-between">
						<div className="text-sm">
							<span className="font-medium">
								{t("blastRadius:score", "Score")}:{" "}
							</span>
							<span
								className={`inline-block px-2 py-0.5 rounded border text-xs font-medium ${SCORE_STYLES[report.score]}`}
							>
								{report.score.toUpperCase()}
							</span>
						</div>
						<div className="text-xs text-muted-foreground">
							{report.total_dependents}{" "}
							{t("blastRadius:dependents", "dependents")} ·{" "}
							{report.tests.length} {t("blastRadius:tests", "tests")}
						</div>
					</div>

					<ul className="text-xs text-muted-foreground list-disc pl-4 space-y-0.5">
						{report.explanation.map((line) => (
							<li key={line}>{line}</li>
						))}
					</ul>

					{report.flags.length > 0 && (
						<div className="text-xs">
							<div className="flex items-center gap-1 text-yellow-500 font-medium">
								<AlertTriangle className="w-3 h-3" />
								{t("blastRadius:flags", "Feature flags referenced")}
							</div>
							<div className="flex flex-wrap gap-1 mt-1">
								{report.flags.map((f) => (
									<code
										key={f}
										className="bg-muted px-1 py-0.5 rounded text-xs"
									>
										{f}
									</code>
								))}
							</div>
						</div>
					)}

					{report.dependents.length > 0 && (
						<div>
							<h4 className="text-sm font-medium mb-1">
								{t("blastRadius:dependentFiles", "Dependent files")}
							</h4>
							<div className="max-h-48 overflow-auto space-y-1">
								{report.dependents.map((d) => (
									<div
										key={`${d.source}→${d.target}`}
										className="text-xs font-mono flex items-center gap-1"
									>
										<code className="text-muted-foreground">{d.source}</code>
										<span className="text-muted-foreground">→</span>
										<code>{d.target}</code>
									</div>
								))}
							</div>
						</div>
					)}

					{report.tests.length > 0 && (
						<div>
							<h4 className="text-sm font-medium mb-1">
								{t("blastRadius:testFiles", "Tests in scope")}
							</h4>
							<div className="max-h-40 overflow-auto space-y-0.5">
								{report.tests.map((testFile) => (
									<code
										key={testFile}
										className="text-xs block font-mono text-muted-foreground"
									>
										{testFile}
									</code>
								))}
							</div>
						</div>
					)}
				</section>
			)}
		</div>
	);
}
