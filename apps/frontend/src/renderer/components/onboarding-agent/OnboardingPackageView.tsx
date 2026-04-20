import {
	BookOpen,
	ChevronLeft,
	ChevronRight,
	CircleCheck,
	CircleX,
	ListChecks,
	Map as MapIcon,
	MessageCircleQuestion,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
	setupOnboardingAgentListeners,
	useOnboardingAgentStore,
} from "../../stores/onboarding-agent-store";
import { Button } from "../ui/button";

type Tab = "tour" | "quiz" | "tasks" | "glossary";

interface OnboardingPackageViewProps {
	readonly projectPath?: string;
}

export function OnboardingPackageView({
	projectPath,
}: OnboardingPackageViewProps) {
	const { t } = useTranslation(["onboardingAgent", "common"]);
	const [tab, setTab] = useState<Tab>("tour");

	const pkg = useOnboardingAgentStore((s) => s.pkg);
	const phase = useOnboardingAgentStore((s) => s.phase);
	const status = useOnboardingAgentStore((s) => s.status);
	const error = useOnboardingAgentStore((s) => s.error);
	const startScan = useOnboardingAgentStore((s) => s.startScan);
	const reset = useOnboardingAgentStore((s) => s.reset);

	useEffect(() => {
		const cleanup = setupOnboardingAgentListeners();
		return cleanup;
	}, []);

	const isScanning = phase === "scanning";

	if (!pkg && phase !== "scanning" && phase !== "error") {
		return (
			<div className="p-6 space-y-3">
				<h2 className="text-lg font-semibold flex items-center gap-2">
					<BookOpen className="w-5 h-5" />
					{t("onboardingAgent:packageTitle", "Onboarding Tour")}
				</h2>
				<p className="text-sm text-muted-foreground">
					{t(
						"onboardingAgent:packageIntro",
						"Generate an interactive tour with quiz, first tasks, and glossary for this project.",
					)}
				</p>
				<Button
					onClick={() => projectPath && startScan(projectPath)}
					disabled={!projectPath}
				>
					{t("onboardingAgent:actions.runScan", "Generate onboarding")}
				</Button>
			</div>
		);
	}

	if (isScanning) {
		return (
			<div className="p-6">
				<p className="text-sm text-muted-foreground">
					{status || t("onboardingAgent:actions.scanning", "Scanning project…")}
				</p>
			</div>
		);
	}

	if (phase === "error") {
		return (
			<div className="p-6 space-y-3">
				<p className="text-sm text-destructive">{error}</p>
				<Button variant="outline" onClick={reset}>
					{t("common:retry", "Retry")}
				</Button>
			</div>
		);
	}

	if (!pkg) return null;

	return (
		<div className="flex flex-col h-full">
			<div className="flex items-center justify-between p-4 border-b">
				<h2 className="text-lg font-semibold flex items-center gap-2">
					<BookOpen className="w-5 h-5" />
					{pkg.guide.project_name}
				</h2>
				<Button variant="outline" size="sm" onClick={reset}>
					{t("common:reset", "Reset")}
				</Button>
			</div>

			<div className="flex border-b text-sm">
				<TabButton
					icon={<MapIcon className="w-4 h-4" />}
					label={t("onboardingAgent:tabs.tour", "Tour")}
					active={tab === "tour"}
					badge={pkg.tour.length}
					onClick={() => setTab("tour")}
				/>
				<TabButton
					icon={<MessageCircleQuestion className="w-4 h-4" />}
					label={t("onboardingAgent:tabs.quiz", "Quiz")}
					active={tab === "quiz"}
					badge={pkg.quiz.length}
					onClick={() => setTab("quiz")}
				/>
				<TabButton
					icon={<ListChecks className="w-4 h-4" />}
					label={t("onboardingAgent:tabs.firstTasks", "First tasks")}
					active={tab === "tasks"}
					badge={pkg.first_tasks.length}
					onClick={() => setTab("tasks")}
				/>
				<TabButton
					icon={<BookOpen className="w-4 h-4" />}
					label={t("onboardingAgent:tabs.glossary", "Glossary")}
					active={tab === "glossary"}
					badge={pkg.glossary.length}
					onClick={() => setTab("glossary")}
				/>
			</div>

			<div className="flex-1 overflow-auto p-4">
				{tab === "tour" && <TourPanel />}
				{tab === "quiz" && <QuizPanel />}
				{tab === "tasks" && <FirstTasksPanel />}
				{tab === "glossary" && <GlossaryPanel />}
			</div>
		</div>
	);
}

function TabButton({
	icon,
	label,
	active,
	badge,
	onClick,
}: {
	icon: React.ReactNode;
	label: string;
	active: boolean;
	badge: number;
	onClick: () => void;
}) {
	return (
		<button
			type="button"
			onClick={onClick}
			className={`flex items-center gap-2 px-4 py-2 border-b-2 ${
				active
					? "border-primary text-primary"
					: "border-transparent text-muted-foreground hover:text-foreground"
			}`}
		>
			{icon}
			<span>{label}</span>
			<span className="text-xs bg-muted px-1.5 rounded">{badge}</span>
		</button>
	);
}

function TourPanel() {
	const { t } = useTranslation("onboardingAgent");
	const pkg = useOnboardingAgentStore((s) => s.pkg);
	const idx = useOnboardingAgentStore((s) => s.currentTourStep);
	const setIdx = useOnboardingAgentStore((s) => s.setCurrentTourStep);

	if (!pkg || pkg.tour.length === 0) {
		return (
			<p className="text-sm text-muted-foreground">
				{t("emptyTour", "No tour steps generated.")}
			</p>
		);
	}

	const step = pkg.tour[idx];

	return (
		<div className="space-y-4">
			<div className="flex items-center justify-between">
				<span className="text-sm text-muted-foreground">
					{t("stepOfTotal", {
						current: idx + 1,
						total: pkg.tour.length,
						defaultValue: "Step {{current}} of {{total}}",
					})}
				</span>
				<div className="flex gap-2">
					<Button
						size="icon"
						variant="outline"
						onClick={() => setIdx(Math.max(0, idx - 1))}
						disabled={idx === 0}
					>
						<ChevronLeft className="w-4 h-4" />
					</Button>
					<Button
						size="icon"
						variant="outline"
						onClick={() => setIdx(Math.min(pkg.tour.length - 1, idx + 1))}
						disabled={idx === pkg.tour.length - 1}
					>
						<ChevronRight className="w-4 h-4" />
					</Button>
				</div>
			</div>
			<div className="border rounded-md p-4 bg-card space-y-2">
				<h3 className="font-semibold">{step.title}</h3>
				<p className="text-sm font-mono text-muted-foreground">
					{step.file_path}
				</p>
				<p className="text-sm whitespace-pre-wrap">{step.reason}</p>
				{step.suggested_questions.length > 0 && (
					<div className="mt-3">
						<p className="text-xs font-medium text-muted-foreground mb-1">
							{t("suggestedQuestions", "Suggested questions")}
						</p>
						<ul className="list-disc pl-5 space-y-1 text-sm">
							{step.suggested_questions.map((q) => (
								<li key={q}>{q}</li>
							))}
						</ul>
					</div>
				)}
			</div>
		</div>
	);
}

function QuizPanel() {
	const { t } = useTranslation("onboardingAgent");
	const pkg = useOnboardingAgentStore((s) => s.pkg);
	const answers = useOnboardingAgentStore((s) => s.quizAnswers);
	const answer = useOnboardingAgentStore((s) => s.answerQuiz);

	if (!pkg || pkg.quiz.length === 0) {
		return (
			<p className="text-sm text-muted-foreground">
				{t("emptyQuiz", "No quiz questions generated.")}
			</p>
		);
	}

	const score = Object.entries(answers).filter(
		([qIdx, chosen]) => pkg.quiz[Number(qIdx)]?.correct_index === chosen,
	).length;
	const answered = Object.keys(answers).length;

	return (
		<div className="space-y-4">
			<p className="text-sm text-muted-foreground">
				{t("quizScore", {
					score,
					answered,
					total: pkg.quiz.length,
					defaultValue: "Score: {{score}}/{{answered}} (of {{total}})",
				})}
			</p>
			{pkg.quiz.map((q, qIdx) => {
				const chosen = answers[qIdx];
				const hasAnswered = chosen !== undefined;
				return (
					<div
						key={q.question}
						className="border rounded-md p-3 space-y-2 bg-card"
					>
						<p className="font-medium text-sm">
							{qIdx + 1}. {q.question}
						</p>
						<div className="space-y-1">
							{q.choices.map((choice, cIdx) => {
								const isCorrect = cIdx === q.correct_index;
								const isChosen = chosen === cIdx;
								return (
									<button
										type="button"
										key={choice}
										onClick={() => !hasAnswered && answer(qIdx, cIdx)}
										disabled={hasAnswered}
										className={`w-full text-left px-3 py-2 rounded-md border text-sm flex items-center gap-2 ${
											hasAnswered && isCorrect
												? "bg-green-500/10 border-green-500/50"
												: hasAnswered && isChosen && !isCorrect
													? "bg-red-500/10 border-red-500/50"
													: "hover:bg-accent"
										}`}
									>
										{hasAnswered && isCorrect && (
											<CircleCheck className="w-4 h-4 text-green-600" />
										)}
										{hasAnswered && isChosen && !isCorrect && (
											<CircleX className="w-4 h-4 text-red-600" />
										)}
										<span>{choice}</span>
									</button>
								);
							})}
						</div>
						{hasAnswered && q.rationale && (
							<p className="text-xs text-muted-foreground italic">
								{q.rationale}
							</p>
						)}
					</div>
				);
			})}
		</div>
	);
}

function FirstTasksPanel() {
	const { t } = useTranslation("onboardingAgent");
	const pkg = useOnboardingAgentStore((s) => s.pkg);

	if (!pkg || pkg.first_tasks.length === 0) {
		return (
			<p className="text-sm text-muted-foreground">
				{t("emptyFirstTasks", "No TODO/FIXME markers found.")}
			</p>
		);
	}

	return (
		<div className="space-y-2">
			{pkg.first_tasks.map((task) => (
				<div
					key={`${task.file_path}:${task.line}`}
					className="border rounded-md p-3 bg-card"
				>
					<p className="font-medium text-sm">{task.title}</p>
					<p className="text-xs font-mono text-muted-foreground mt-1">
						{task.file_path}:{task.line}
					</p>
					<p className="text-xs text-muted-foreground mt-1">
						{task.source_comment}
					</p>
				</div>
			))}
		</div>
	);
}

function GlossaryPanel() {
	const { t } = useTranslation("onboardingAgent");
	const pkg = useOnboardingAgentStore((s) => s.pkg);

	if (!pkg || pkg.glossary.length === 0) {
		return (
			<p className="text-sm text-muted-foreground">
				{t("emptyGlossary", "No glossary terms detected.")}
			</p>
		);
	}

	return (
		<div className="grid grid-cols-2 gap-2">
			{pkg.glossary.map((term) => (
				<div key={term.term} className="border rounded-md p-2 bg-card">
					<p className="font-mono text-sm">
						{term.term}{" "}
						<span className="text-xs text-muted-foreground">
							×{term.occurrences}
						</span>
					</p>
					{term.sources.length > 0 && (
						<p className="text-xs text-muted-foreground mt-1 truncate">
							{term.sources.slice(0, 3).join(", ")}
						</p>
					)}
				</div>
			))}
		</div>
	);
}
