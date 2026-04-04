import type {
	ChangelogAudience,
	ChangelogEmojiLevel,
	ChangelogFormat,
	ChangelogSourceMode,
	ChangelogTask,
	GitCommit as GitCommitType,
} from "../../../shared/types";
import { useProjectStore } from "../../stores/project-store";
import { ConfigurationPanel } from "./ConfigurationPanel";
import { useImageUpload } from "./hooks/useImageUpload";
import { PreviewPanel } from "./PreviewPanel";
import { Step3SuccessScreen } from "./Step3SuccessScreen";
import { getSummaryInfo } from "./utils";

interface Step2ConfigureGenerateProps {
	readonly sourceMode: ChangelogSourceMode;
	readonly selectedTaskIds: string[];
	readonly doneTasks: ChangelogTask[];
	readonly previewCommits: GitCommitType[];
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
	readonly generatedChangelog: string;
	readonly isGenerating: boolean;
	readonly error: string | null;
	readonly showAdvanced: boolean;
	readonly saveSuccess: boolean;
	readonly copySuccess: boolean;
	readonly canGenerate: boolean;
	readonly canSave: boolean;
	readonly onBack: () => void;
	readonly onVersionChange: (v: string) => void;
	readonly onDateChange: (d: string) => void;
	readonly onFormatChange: (f: ChangelogFormat) => void;
	readonly onAudienceChange: (a: ChangelogAudience) => void;
	readonly onEmojiLevelChange: (l: ChangelogEmojiLevel) => void;
	readonly onCustomInstructionsChange: (i: string) => void;
	readonly onShowAdvancedChange: (show: boolean) => void;
	readonly onGenerate: () => void;
	readonly onSave: () => void;
	readonly onCopy: () => void;
	readonly onChangelogEdit: (content: string) => void;
}

export function Step2ConfigureGenerate(props: Step2ConfigureGenerateProps) {
	const {
		sourceMode,
		selectedTaskIds,
		doneTasks,
		previewCommits,
		generatedChangelog,
		onChangelogEdit,
	} = props;

	const selectedProjectId = useProjectStore((state) => state.selectedProjectId);
	const projects = useProjectStore((state) => state.projects);
	const selectedProject = projects.find((p) => p.id === selectedProjectId);
	const selectedTasks = doneTasks.filter((t) => selectedTaskIds.includes(t.id));

	const summaryInfo = getSummaryInfo(
		sourceMode,
		selectedTaskIds,
		selectedTasks,
		previewCommits,
	);

	const imageUpload = useImageUpload({
		projectId: selectedProjectId,
		content: generatedChangelog,
		onContentChange: onChangelogEdit,
	});

	return (
		<div className="flex flex-1 overflow-hidden">
			<ConfigurationPanel
				sourceMode={sourceMode}
				summaryInfo={summaryInfo}
				existingChangelog={props.existingChangelog}
				version={props.version}
				versionReason={props.versionReason}
				date={props.date}
				format={props.format}
				audience={props.audience}
				emojiLevel={props.emojiLevel}
				customInstructions={props.customInstructions}
				generationProgress={props.generationProgress}
				isGenerating={props.isGenerating}
				error={props.error}
				showAdvanced={props.showAdvanced}
				canGenerate={props.canGenerate}
				onBack={props.onBack}
				onVersionChange={props.onVersionChange}
				onDateChange={props.onDateChange}
				onFormatChange={props.onFormatChange}
				onAudienceChange={props.onAudienceChange}
				onEmojiLevelChange={props.onEmojiLevelChange}
				onCustomInstructionsChange={props.onCustomInstructionsChange}
				onShowAdvancedChange={props.onShowAdvancedChange}
				onGenerate={props.onGenerate}
			/>

			<PreviewPanel
				generatedChangelog={generatedChangelog}
				saveSuccess={props.saveSuccess}
				copySuccess={props.copySuccess}
				canSave={props.canSave}
				isDragOver={imageUpload.isDragOver}
				imageError={imageUpload.imageError}
				textareaRef={imageUpload.textareaRef}
				projectPath={selectedProject?.path}
				onSave={props.onSave}
				onCopy={props.onCopy}
				onChangelogEdit={onChangelogEdit}
				onPaste={imageUpload.handlePaste}
				onDragOver={imageUpload.handleDragOver}
				onDragLeave={imageUpload.handleDragLeave}
				onDrop={imageUpload.handleDrop}
			/>
		</div>
	);
}

interface Step3ReleaseArchiveProps {
	readonly projectId: string;
	readonly version: string;
	readonly selectedTaskIds: string[];
	readonly doneTasks: ChangelogTask[];
	readonly generatedChangelog: string;
	readonly onDone: () => void;
}

export function Step3ReleaseArchive(props: Step3ReleaseArchiveProps) {
	return <Step3SuccessScreen {...props} />;
}
