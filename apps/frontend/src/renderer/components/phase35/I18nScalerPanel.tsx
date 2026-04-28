/**
 * #3.12 i18n Auto-Scaling panel.
 *
 * Point at a `locales/` directory, pick a source locale, see coverage and
 * missing/obsolete keys per target locale.
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useI18nScalerStore } from "../../stores/phase35-stores";
import { Button } from "../ui/button";
import { PanelShell } from "./_panel-shell";

export function I18nScalerPanel() {
	const { t } = useTranslation("phase35");
	const { phase, error, report, runReport } = useI18nScalerStore();
	const [dir, setDir] = useState("");
	const [source, setSource] = useState("en");

	const isRunning = phase === "running";

	return (
		<PanelShell
			title={t("i18nScaler.title")}
			subtitle={t("i18nScaler.subtitle")}
			error={error}
			actions={
				<Button
					size="sm"
					onClick={() => runReport(dir, source)}
					disabled={isRunning || !dir}
				>
					{isRunning ? t("common.running") : t("i18nScaler.runReport")}
				</Button>
			}
		>
			<div className="space-y-3 text-sm">
				<div className="grid grid-cols-2 gap-3">
					<div>
						<label htmlFor="locales-dir-input" className="block font-medium mb-1">
							{t("i18nScaler.localesDir")}
						</label>
						<input
							id="locales-dir-input"
							value={dir}
							onChange={(e) => setDir(e.target.value)}
							className="w-full rounded border bg-background p-2 font-mono text-xs"
							placeholder="apps/frontend/src/shared/i18n/locales"
						/>
					</div>
					<div>
						<label htmlFor="source-locale-input" className="block font-medium mb-1">
							{t("i18nScaler.sourceLocale")}
						</label>
						<input
							id="source-locale-input"
							value={source}
							onChange={(e) => setSource(e.target.value)}
							className="w-full rounded border bg-background p-2 text-sm"
						/>
					</div>
				</div>

				{report && (
					<div className="space-y-3">
						<div>
							<div className="font-medium mb-1">{t("i18nScaler.coverage")}</div>
							<table className="w-full text-sm border">
								<thead>
									<tr className="border-b bg-muted/40">
										<th className="text-left p-2">locale</th>
										<th className="text-right p-2">translated</th>
										<th className="text-right p-2">placeholder</th>
										<th className="text-right p-2">total</th>
										<th className="text-right p-2">coverage</th>
									</tr>
								</thead>
								<tbody>
									{report.coverage.map((c) => (
										<tr key={c.locale} className="border-b">
											<td className="p-2 font-mono">{c.locale}</td>
											<td className="p-2 text-right">{c.translated_keys}</td>
											<td className="p-2 text-right">{c.placeholder_keys}</td>
											<td className="p-2 text-right">{c.total_keys}</td>
											<td className="p-2 text-right">
												{(c.coverage_ratio * 100).toFixed(1)}%
											</td>
										</tr>
									))}
								</tbody>
							</table>
						</div>

						{report.diffs.map((d) => (
							<details key={d.target_locale} className="rounded border p-2">
								<summary className="font-medium cursor-pointer">
									{d.target_locale} ({d.totals.missing} missing,{" "}
									{d.totals.obsolete} obsolete,{" "}
									{d.totals.placeholder_mismatches} mismatches)
								</summary>
								<div className="mt-2 grid grid-cols-3 gap-3 text-xs">
									<div>
										<div className="font-medium">
											{t("i18nScaler.missingKeys")}
										</div>
										<ul className="font-mono max-h-32 overflow-auto">
											{d.missing_keys.map((k) => (
												<li key={k}>{k}</li>
											))}
										</ul>
									</div>
									<div>
										<div className="font-medium">
											{t("i18nScaler.obsoleteKeys")}
										</div>
										<ul className="font-mono max-h-32 overflow-auto">
											{d.obsolete_keys.map((k) => (
												<li key={k}>{k}</li>
											))}
										</ul>
									</div>
									<div>
										<div className="font-medium">
											{t("i18nScaler.placeholderMismatches")}
										</div>
										<ul className="font-mono max-h-32 overflow-auto">
											{d.placeholder_mismatches.map((k) => (
												<li key={k}>{k}</li>
											))}
										</ul>
									</div>
								</div>
							</details>
						))}
					</div>
				)}
			</div>
		</PanelShell>
	);
}
