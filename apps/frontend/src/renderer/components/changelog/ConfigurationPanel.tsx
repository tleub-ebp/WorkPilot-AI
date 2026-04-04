import {
	AlertCircle,
	ArrowLeft,
	ChevronDown,
	ChevronUp,
	FileText,
	GitCommit,
	RefreshCw,
	Sparkles,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import {
	CHANGELOG_AUDIENCE_DESCRIPTIONS,
	CHANGELOG_AUDIENCE_LABELS,
	CHANGELOG_EMOJI_LEVEL_DESCRIPTIONS,
	CHANGELOG_EMOJI_LEVEL_LABELS,
	CHANGELOG_FORMAT_DESCRIPTIONS,
	CHANGELOG_FORMAT_LABELS,
	CHANGELOG_STAGE_LABELS,
} from "../../../shared/constants";
import type {
	ChangelogAudience,
	ChangelogEmojiLevel,
	ChangelogFormat,
	ChangelogSourceMode,
} from "../../../shared/types";
import { Button } from "../ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import {
	Collapsible,
	CollapsibleContent,
	CollapsibleTrigger,
} from "../ui/collapsible";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Progress } from "../ui/progress";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../ui/select";
import { Textarea } from "../ui/textarea";
import { getVersionBumpDescription, type SummaryInfo } from "./utils";

interface ConfigurationPanelProps {
	readonly sourceMode: ChangelogSourceMode;
	readonly summaryInfo: SummaryInfo;
	readonly existingChangelog: { lastVersion?: string } | null;
	readonly version: string;
	readonly versionReason: string | null;
	readonly date: string;
	readonly format: ChangelogFormat;
	readonly audience: ChangelogAudience;
	readonly emojiLevel: ChangelogEmojiLevel;
	readonly customInstructions: string;
	readonly generationProgress: {
		stage: string;
		progress: number;
		message?: string;
		error?: string;
	} | null;
	readonly isGenerating: boolean;
	readonly error: string | null;
	readonly showAdvanced: boolean;
	readonly canGenerate: boolean;
	readonly onBack: () => void;
	readonly onVersionChange: (v: string) => void;
	readonly onDateChange: (d: string) => void;
	readonly onFormatChange: (f: ChangelogFormat) => void;
	readonly onAudienceChange: (a: ChangelogAudience) => void;
	readonly onEmojiLevelChange: (l: ChangelogEmojiLevel) => void;
	readonly onCustomInstructionsChange: (i: string) => void;
	readonly onShowAdvancedChange: (show: boolean) => void;
	readonly onGenerate: () => void;
}

export function ConfigurationPanel({
	sourceMode,
	summaryInfo,
	existingChangelog,
	version,
	versionReason,
	date,
	format,
	audience,
	emojiLevel,
	customInstructions,
	generationProgress,
	isGenerating,
	error,
	showAdvanced,
	canGenerate,
	onBack,
	onVersionChange,
	onDateChange,
	onFormatChange,
	onAudienceChange,
	onEmojiLevelChange,
	onCustomInstructionsChange,
	onShowAdvancedChange,
	onGenerate,
}: ConfigurationPanelProps) {
	const { t } = useTranslation(["changelog", "common"]);
	const versionBumpDescription = getVersionBumpDescription(versionReason);

	return (
		<div className="w-80 shrink-0 border-r border-border overflow-y-auto">
			<div className="p-6 space-y-6">
				{/* Back button and summary */}
				<div className="space-y-4">
					<Button variant="ghost" size="sm" onClick={onBack} className="-ml-2">
						<ArrowLeft className="mr-2 h-4 w-4" />
						{t("changelog:configuration.backToSelection")}
					</Button>
					<div className="rounded-lg bg-muted/50 p-3">
						<div className="flex items-center gap-2 text-sm font-medium">
							{sourceMode === "tasks" ? (
								<FileText className="h-4 w-4" />
							) : (
								<GitCommit className="h-4 w-4" />
							)}
							{t("changelog:configuration.including")} {summaryInfo.count}{" "}
							{summaryInfo.label}
							{summaryInfo.count === 1 ? "" : "s"}
						</div>
						<div className="text-xs text-muted-foreground mt-1 line-clamp-2">
							{summaryInfo.details}
						</div>
					</div>
				</div>

				{/* Version & Date */}
				<Card>
					<CardHeader className="pb-3">
						<CardTitle className="text-sm">
							{t("changelog:configuration.releaseInfo")}
						</CardTitle>
					</CardHeader>
					<CardContent className="space-y-4">
						<div className="space-y-2">
							<Label htmlFor="version">
								{t("changelog:configuration.versionLabel")}
							</Label>
							<Input
								id="version"
								value={version}
								onChange={(e) => onVersionChange(e.target.value)}
								placeholder={t("changelog:configuration.versionPlaceholder")}
							/>
						</div>
						<div className="space-y-2">
							<Label htmlFor="date">
								{t("changelog:configuration.dateLabel")}
							</Label>
							<Input
								id="date"
								type="date"
								value={date}
								onChange={(e) => onDateChange(e.target.value)}
							/>
						</div>
						{(existingChangelog?.lastVersion || versionBumpDescription) && (
							<div className="text-xs text-muted-foreground space-y-1">
								{existingChangelog?.lastVersion && (
									<p>
										{t("changelog:configuration.previous", {
											version: existingChangelog.lastVersion,
										})}
									</p>
								)}
								{versionBumpDescription && (
									<p className="text-primary/70">{versionBumpDescription}</p>
								)}
							</div>
						)}
					</CardContent>
				</Card>

				{/* Format & Audience */}
				<Card>
					<CardHeader className="pb-3">
						<CardTitle className="text-sm">
							{t("changelog:configuration.outputStyle")}
						</CardTitle>
					</CardHeader>
					<CardContent className="space-y-4">
						<div className="space-y-2">
							<Label>{t("changelog:configuration.formatLabel")}</Label>
							<Select
								value={format}
								onValueChange={(value) =>
									onFormatChange(value as ChangelogFormat)
								}
							>
								<SelectTrigger>
									<SelectValue />
								</SelectTrigger>
								<SelectContent>
									{Object.entries(CHANGELOG_FORMAT_LABELS).map(
										([value, label]) => (
											<SelectItem key={value} value={value}>
												<div>
													<div>{label}</div>
													<div className="text-xs text-muted-foreground">
														{CHANGELOG_FORMAT_DESCRIPTIONS[value]}
													</div>
												</div>
											</SelectItem>
										),
									)}
								</SelectContent>
							</Select>
						</div>

						<div className="space-y-2">
							<Label>{t("changelog:configuration.audienceLabel")}</Label>
							<Select
								value={audience}
								onValueChange={(value) =>
									onAudienceChange(value as ChangelogAudience)
								}
							>
								<SelectTrigger>
									<SelectValue />
								</SelectTrigger>
								<SelectContent>
									{Object.entries(CHANGELOG_AUDIENCE_LABELS).map(
										([value, label]) => (
											<SelectItem key={value} value={value}>
												<div>
													<div>{label}</div>
													<div className="text-xs text-muted-foreground">
														{CHANGELOG_AUDIENCE_DESCRIPTIONS[value]}
													</div>
												</div>
											</SelectItem>
										),
									)}
								</SelectContent>
							</Select>
						</div>

						<div className="space-y-2">
							<Label>{t("changelog:configuration.emojiLabel")}</Label>
							<Select
								value={emojiLevel}
								onValueChange={(value) =>
									onEmojiLevelChange(value as ChangelogEmojiLevel)
								}
							>
								<SelectTrigger>
									<SelectValue />
								</SelectTrigger>
								<SelectContent>
									{Object.entries(CHANGELOG_EMOJI_LEVEL_LABELS).map(
										([value, label]) => (
											<SelectItem key={value} value={value}>
												<div>
													<div>{label}</div>
													<div className="text-xs text-muted-foreground">
														{CHANGELOG_EMOJI_LEVEL_DESCRIPTIONS[value]}
													</div>
												</div>
											</SelectItem>
										),
									)}
								</SelectContent>
							</Select>
						</div>
					</CardContent>
				</Card>

				{/* Advanced Options */}
				<Collapsible open={showAdvanced} onOpenChange={onShowAdvancedChange}>
					<CollapsibleTrigger asChild>
						<Button variant="ghost" className="w-full justify-between">
							{t("changelog:configuration.advancedOptions")}
							{showAdvanced ? (
								<ChevronUp className="h-4 w-4" />
							) : (
								<ChevronDown className="h-4 w-4" />
							)}
						</Button>
					</CollapsibleTrigger>
					<CollapsibleContent className="pt-2">
						<Card>
							<CardContent className="pt-4">
								<div className="space-y-2">
									<Label htmlFor="instructions">
										{t("changelog:configuration.customInstructionsLabel")}
									</Label>
									<Textarea
										id="instructions"
										value={customInstructions}
										onChange={(e) => onCustomInstructionsChange(e.target.value)}
										placeholder={t(
											"changelog:configuration.customInstructionsPlaceholder",
										)}
										rows={3}
									/>
									<p className="text-xs text-muted-foreground">
										{t("changelog:configuration.customInstructionsHelp")}
									</p>
								</div>
							</CardContent>
						</Card>
					</CollapsibleContent>
				</Collapsible>

				{/* Generate Button */}
				<Button
					className="w-full"
					onClick={onGenerate}
					disabled={!canGenerate}
					size="lg"
				>
					{isGenerating ? (
						<>
							<RefreshCw className="mr-2 h-4 w-4 animate-spin" />
							{t("changelog:configuration.generating")}
						</>
					) : (
						<>
							<Sparkles className="mr-2 h-4 w-4" />
							{t("changelog:configuration.generateChangelog")}
						</>
					)}
				</Button>

				{/* Progress */}
				{generationProgress && isGenerating && (
					<div className="space-y-2">
						<div className="flex items-center justify-between text-sm">
							<span>{CHANGELOG_STAGE_LABELS[generationProgress.stage]}</span>
							<span>{generationProgress.progress}%</span>
						</div>
						<Progress value={generationProgress.progress} />
					</div>
				)}

				{/* Error */}
				{error && (
					<div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm">
						<div className="flex items-start gap-2">
							<AlertCircle className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
							<span className="text-destructive">{error}</span>
						</div>
					</div>
				)}
			</div>
		</div>
	);
}
